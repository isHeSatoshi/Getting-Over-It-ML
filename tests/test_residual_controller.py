from copy import deepcopy
from types import SimpleNamespace
import unittest

import numpy as np

from research.residual_controller import (ACTOR_DIMENSION, HORIZON, ResidualController,
                                          contract, validate_normalizer)
from research.stroke_controller import StrokeController


def fixture():
    observations = np.zeros((600, 217), np.float32)
    observations[:, 0] = np.arange(600, dtype=np.float32)/5500
    observations[:, 1] = 21/16000
    actions = np.column_stack((np.arange(600)/1000, np.full(600, -.5))).astype(np.float32)
    return observations, actions


class ResidualControllerTests(unittest.TestCase):
    def setUp(self):
        self.observations, self.actions = fixture()
        self.raw = self.observations[0].copy()
        self.controller = ResidualController(self.observations, self.actions)
        self.controller.reset(self.raw)
        self.zero = np.zeros(2, np.float32)

    def test_contract_explicit_context_new_rms_and_no_learning_claim(self):
        record = contract()
        self.assertEqual(record["actor_dimension"], 222)
        self.assertEqual(record["residual_scale"], 2)
        self.assertEqual(record["base"]["maximum_phase"], 599)
        self.assertEqual(record["base"]["contact_proxy_travel_threshold_pixels"], 3)
        self.assertEqual(record["frame_skip"], 1)
        self.assertIn("never learned progress", record["limit"])
        self.assertFalse(record["privileged_counter_input"])
        self.assertEqual(record["learning_updates"], 0)

    def test_zero_residual_exact_600_row_baseline_with_causal_context(self):
        base = StrokeController(self.observations, self.actions, "contact_timed_feedback")
        previous = self.zero
        for tick, pre in enumerate(self.observations):
            context = self.controller.prepare(pre)
            proposal = base.action(pre)
            self.assertEqual(context.shape, (ACTOR_DIMENSION,))
            self.assertEqual(context.dtype, np.float32)
            np.testing.assert_array_equal(context[:217], pre)
            self.assertEqual(context[217], np.float32(tick/599))
            np.testing.assert_array_equal(context[218:220], proposal)
            np.testing.assert_array_equal(context[220:222], previous)
            action = self.controller.action(self.zero)
            np.testing.assert_array_equal(action, proposal)
            self.assertEqual(self.controller.base_summary(), base.last)
            post = self.observations[min(tick+1, 599)]
            self.controller.observe(post, action)
            previous = action

    def test_preparation_cached_without_double_source_advance(self):
        first = self.controller.prepare(self.raw)
        first[:] = 99
        second = self.controller.prepare(self.raw)
        self.assertEqual(self.controller.summary()["base_calls"], 1)
        np.testing.assert_array_equal(second[:217], self.raw)
        wrong = self.raw.copy()
        wrong[0] += .1
        with self.assertRaisesRegex(ValueError, "Pre-input"):
            self.controller.prepare(wrong)
        self.assertEqual(self.controller.summary()["base_calls"], 1)

    def test_signed_residual_scale_and_final_clipping_separate_fields(self):
        context = self.controller.prepare(self.raw)
        residual = np.asarray([1, -1], np.float32)
        final = self.controller.action(residual)
        np.testing.assert_array_equal(final, [1, -1])
        record = self.controller.observe(self.raw, final)["last_transition"]
        np.testing.assert_array_equal(record["base_proposal"], context[218:220])
        np.testing.assert_array_equal(record["legal_residual"], residual)
        np.testing.assert_array_equal(record["unclipped_final"], [2, -2.5])
        self.assertTrue(record["final_clip_changed"])
        self.assertFalse(record["teacher_label"])

    def test_residual_can_override_base_to_any_legal_axis_target(self):
        context = self.controller.prepare(self.raw)
        desired = np.asarray([-.75, .875], np.float32)
        residual = (desired-context[218:220])/np.float32(2)
        np.testing.assert_array_equal(self.controller.action(residual), desired)

    def test_own_history_is_issued_not_base_or_external_actual_command(self):
        self.controller.prepare(self.raw)
        issued = self.controller.action(np.asarray([.125, .125], np.float32))
        external = np.asarray([-.5, .5], np.float32)
        observed = self.controller.observe(self.raw, external)
        self.assertTrue(observed["last_transition"]["external_application_changed"])
        np.testing.assert_array_equal(observed["last_transition"]["actual_applied"], external)
        np.testing.assert_array_equal(self.controller.prepare(self.raw)[220:], issued)

    def test_inputs_outputs_and_diagnostics_are_copied(self):
        pre = self.raw.copy()
        context = self.controller.prepare(pre)
        pre[:] = 99
        context[:] = 99
        residual = self.zero.copy()
        issued = self.controller.action(residual)
        expected = issued.copy()
        residual[:] = 99
        issued[:] = 99
        post = self.raw.copy()
        applied = expected.copy()
        summary = self.controller.observe(post, applied)
        post[:] = 99
        applied[:] = 99
        summary["last_transition"]["actual_post"][0] = 99
        base = self.controller.base_summary()
        base["pointer_correction_pixels"][0] = 99
        self.assertEqual(self.controller.summary()["last_transition"]["actual_post"][0], 0)
        self.assertEqual(self.controller.base_summary()["pointer_correction_pixels"][0], 0)
        np.testing.assert_array_equal(self.controller.prepare(self.raw)[220:], expected)

    def test_source_prior_arrays_are_copied(self):
        self.observations[:] = 99
        self.actions[:] = 99
        self.controller.prepare(self.raw)
        np.testing.assert_array_equal(self.controller.action(self.zero), [0, -.5])

    def test_requires_reset_and_action_observe_sequence(self):
        fresh = ResidualController(*fixture())
        with self.assertRaises(ValueError):
            fresh.prepare(self.raw)
        with self.assertRaises(ValueError):
            self.controller.action(self.zero)
        with self.assertRaises(ValueError):
            self.controller.observe(self.raw, self.zero)
        self.controller.prepare(self.raw)
        with self.assertRaises(ValueError):
            self.controller.observe(self.raw, self.zero)
        issued = self.controller.action(self.zero)
        with self.assertRaises(ValueError):
            self.controller.action(self.zero)
        with self.assertRaises(ValueError):
            self.controller.prepare(self.raw)
        self.controller.observe(self.raw, issued)
        with self.assertRaises(ValueError):
            self.controller.observe(self.raw, issued)

    def test_next_pre_must_match_actual_post(self):
        self.controller.prepare(self.raw)
        issued = self.controller.action(self.zero)
        post = self.raw.copy()
        post[0] = .1
        self.controller.observe(post, issued)
        with self.assertRaisesRegex(ValueError, "Pre-input"):
            self.controller.prepare(self.raw)
        self.controller.prepare(post)

    def test_raw_shape_type_nonfinite_query_and_travel_rejected_without_clock_change(self):
        variants = [self.raw.astype(np.float64), self.raw[:216],
                    np.full(217, np.nan, np.float32), np.full(217, np.inf, np.float32)]
        for index, value in ((22, .5), (19, -1)):
            bad = self.raw.copy()
            bad[index] = value
            variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError):
                self.controller.prepare(bad)
            with self.assertRaises(ValueError):
                self.controller.reset(bad)
        self.assertEqual(self.controller.summary()["base_calls"], 0)

    def test_illegal_residual_and_actual_applied_rejected_without_consuming_transition(self):
        self.controller.prepare(self.raw)
        bads = [np.zeros(2), np.zeros(3, np.float32), np.asarray([1.01, 0], np.float32),
                np.asarray([np.nan, 0], np.float32), np.asarray([np.inf, 0], np.float32)]
        for bad in bads:
            with self.assertRaises(ValueError):
                self.controller.action(bad)
        issued = self.controller.action(self.zero)
        for bad in bads:
            with self.assertRaises(ValueError):
                self.controller.observe(self.raw, bad)
        with self.assertRaises(ValueError):
            self.controller.observe(self.raw.astype(np.float64), issued)
        with self.assertRaises(ValueError):
            self.controller.observe(self.raw, issued, terminated=1)
        self.assertEqual(self.controller.summary()["steps"], 0)
        self.controller.observe(self.raw, issued)

    def test_reset_clears_clock_own_history_and_pending_transition(self):
        self.controller.prepare(self.raw)
        self.controller.action(np.ones(2, np.float32))
        self.controller.reset(self.raw)
        summary = self.controller.summary()
        self.assertEqual((summary["steps"], summary["base_calls"], summary["base_phase"]), (0, 0, 0))
        self.assertIsNone(summary["last_transition"])
        np.testing.assert_array_equal(self.controller.prepare(self.raw)[220:], [0, 0])

    def test_terminal_and_environment_truncation_finish_without_rearming(self):
        for altitude, terminal, truncated, reason in (
                (21, True, False, "terminal"), (-200, False, False, "terminal"),
                (17000, False, True, "terminal"), (21, False, True, "environment_truncated")):
            self.controller.reset(self.raw)
            self.controller.prepare(self.raw)
            issued = self.controller.action(self.zero)
            post = self.raw.copy()
            post[1] = altitude/16000
            summary = self.controller.observe(post, issued, terminated=terminal, truncated=truncated)
            self.assertTrue(summary["finished"])
            self.assertEqual(summary["reason"], reason)
            with self.assertRaises(ValueError):
                self.controller.prepare(post)
        for altitude in (-200, 17000):
            terminal_raw = self.raw.copy()
            terminal_raw[1] = altitude/16000
            with self.assertRaisesRegex(ValueError, "terminal"):
                self.controller.reset(terminal_raw)

    def test_full_1800_budget_clamps_phase_but_keeps_actual_clock(self):
        for tick in range(HORIZON):
            context = self.controller.prepare(self.raw)
            self.assertEqual(context[217], np.float32(min(tick, 599)/599))
            issued = self.controller.action(self.zero)
            summary = self.controller.observe(self.raw, issued)
            self.assertEqual(summary["base_calls"], tick+1)
        self.assertEqual(summary["reason"], "horizon")
        self.assertEqual(summary["base_phase"], 599)
        with self.assertRaises(ValueError):
            self.controller.prepare(self.raw)

    def test_normalizer_rejects_old217_and_changed_checkpoint_contract(self):
        rms = SimpleNamespace(mean=np.zeros(222), var=np.ones(222), count=1e-4)
        validate_normalizer(rms, contract())
        for size in (217, 223):
            bad = SimpleNamespace(mean=np.zeros(size), var=np.ones(size), count=1)
            with self.assertRaisesRegex(ValueError, "222"):
                validate_normalizer(bad, contract())
        for variance, count in ((np.full(222, -1), 1), (np.full(222, np.nan), 1),
                                (np.ones(222), 0), (np.ones(222), np.inf)):
            bad = SimpleNamespace(mean=rms.mean, var=variance, count=count)
            with self.assertRaises(ValueError):
                validate_normalizer(bad, contract())
        bad_contract = deepcopy(contract())
        bad_contract["residual_scale"] = 1
        with self.assertRaisesRegex(ValueError, "contract"):
            validate_normalizer(rms, bad_contract)


if __name__ == "__main__":
    unittest.main()
