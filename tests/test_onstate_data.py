import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
import torch

from research.behavior_cloning import warm_start
from research.onstate_data import (
    ARRAY_SPEC, EXPECTED_ARRAY_HASHES, OnStateData, _DATA_TOKEN, digest, load_archive,
    normalize, normalizer, trusted_file, validate_arrays)
from research.onstate_study import ARMS
from tests.test_behavior_cloning import Fixture
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from research.reward import RewardConfig


def fixture_arrays():
    observations = np.zeros((5376, 217), dtype=np.float32)
    observations[:, :16] = np.random.default_rng(12).normal(size=(5376, 16)).astype(np.float32)
    rms = normalizer(observations[:3576])
    return {
        "observations": observations, "normalized_observations": normalize(observations, rms),
        "actions": np.tile([0.4, -0.3], (5376, 1)).astype(np.float32),
        "source_ids": np.r_[np.zeros(3576, dtype=np.int64), np.ones(1800, dtype=np.int64)],
        "source_rows": np.r_[np.arange(3576), np.arange(1800)].astype(np.int64),
    }


def fixture_hashes(arrays):
    return {
        "original_observations": digest(arrays["observations"][:3576]),
        "original_actions": digest(arrays["actions"][:3576]),
        "learner_observations": digest(arrays["observations"][3576:]),
        "learner_normalized_observations": digest(arrays["normalized_observations"][3576:]),
        "learner_actions": digest(arrays["actions"][3576:]),
        "original_source_rows": digest(arrays["source_rows"][:3576]),
    }


class OnStateDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def admitted_fixture(self):
        arrays = fixture_arrays()
        patcher = patch.dict(EXPECTED_ARRAY_HASHES, fixture_hashes(arrays))
        patcher.start()
        self.addCleanup(patcher.stop)
        return OnStateData(arrays, {"data_sha256": "fixture-data"}, _DATA_TOKEN)

    def setup_model(self, data):
        vector = VecNormalize(DummyVecEnv([Fixture]), norm_reward=False,
                              gamma=RewardConfig().gamma(1))
        vector.obs_rms = normalizer(data.arrays["observations"][:3576])
        vector.training = False
        model = PPO("MlpPolicy", vector, seed=9, gamma=vector.gamma, n_steps=8,
                    batch_size=4, n_epochs=1, device="cpu",
                    policy_kwargs={"net_arch": [16, 16]})
        self.addCleanup(vector.close)
        return model, vector

    def test_data_constructor_needs_validation_and_keeps_arrays_read_only(self):
        with self.assertRaisesRegex(ValueError, "validated"):
            OnStateData({}, {})
        data = self.admitted_fixture()
        self.assertEqual(data.training_arrays(ARMS[0])[0].shape, (3576, 217))
        self.assertEqual(data.training_arrays(ARMS[1])[0].shape, (5376, 217))
        self.assertTrue(all(not array.flags.writeable for array in data.arrays.values()))

    def test_balanced_sampler_exact_counts_repeatability_and_bounds(self):
        data = self.admitted_fixture()
        for arm, new_count in ((ARMS[0], 0), (ARMS[1], 16)):
            a = data.sample_indices(arm, np.random.default_rng(9), 64)
            b = data.sample_indices(arm, np.random.default_rng(9), 64)
            np.testing.assert_array_equal(a, b)
            self.assertEqual(int(np.count_nonzero(a >= 3576)), new_count)
            self.assertTrue((a >= 0).all() and (a < 5376).all())
        for size in (3, True, 0):
            with self.assertRaises(ValueError):
                data.sample_indices(ARMS[1], np.random.default_rng(9), size)

    def test_changed_labels_and_wrong_raw_normalization_are_rejected(self):
        arrays = fixture_arrays()
        with patch.dict(EXPECTED_ARRAY_HASHES, fixture_hashes(arrays)):
            arrays["actions"][4000, 0] += 0.01
            with self.assertRaisesRegex(ValueError, "logged array"):
                validate_arrays(arrays)
        arrays = fixture_arrays()
        with patch.dict(EXPECTED_ARRAY_HASHES, fixture_hashes(arrays)):
            arrays["normalized_observations"][0, 0] += 0.01
            with self.assertRaisesRegex(ValueError, "normalize"):
                validate_arrays(arrays)

    def test_safe_archive_roundtrip_and_wrong_header_refused_before_allocation(self):
        arrays = fixture_arrays()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.npz"
            np.savez_compressed(path, **arrays)
            decoded = load_archive(path)
            for key in ARRAY_SPEC:
                np.testing.assert_array_equal(decoded[key], arrays[key])
            with zipfile.ZipFile(path, "w") as archive:
                for key, (shape, dtype) in ARRAY_SPEC.items():
                    header = io.BytesIO()
                    np.lib.format.write_array_header_1_0(header, {
                        "shape": (10**9, 217) if key == "observations" else shape,
                        "descr": np.lib.format.dtype_to_descr(dtype), "fortran_order": False})
                    archive.writestr(key + ".npy", header.getvalue())
            with patch("research.onstate_data.np.load") as allocate:
                with self.assertRaisesRegex(ValueError, "before allocation"):
                    load_archive(path)
                allocate.assert_not_called()

    def test_bad_source_hash_or_path_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            path.write_text(json.dumps({"safe": True}))
            with self.assertRaisesRegex(ValueError, "pinned"):
                trusted_file(path, 1024, "0" * 64)
            with self.assertRaises(ValueError):
                trusted_file(Path("relative.json"), 1024)
            with self.assertRaises(ValueError):
                trusted_file(path, 1)

    def test_augmented_smoke_preserves_original_rms_value_std_and_ppo(self):
        data = self.admitted_fixture()
        model, vector = self.setup_model(data)
        parameters = {key: value.clone() for key, value in model.policy.state_dict().items()}
        rms = {key: np.asarray(getattr(vector.obs_rms, key)).copy() for key in ("mean", "var", "count")}
        progress = []
        result = warm_start(model, vector, *data.training_arrays(ARMS[1]),
                            fit_normalization=False, onstate_data=data, onstate_arm=ARMS[1], seed=9,
                            onstate_progress=lambda *counts: progress.append(counts))
        self.assertEqual(progress, [(8, 384, 128)])
        self.assertEqual(result["sample_presentations"], 512)
        self.assertEqual(result["onstate_sampling"]["original_presentations"], 384)
        self.assertEqual(result["onstate_sampling"]["logged_success_presentations"], 128)
        self.assertEqual(model.num_timesteps, 0)
        self.assertFalse(model.policy.optimizer.state)
        for key, value in model.policy.state_dict().items():
            if not key.startswith(("mlp_extractor.policy_net.", "action_net.")):
                self.assertTrue(torch.equal(value, parameters[key]))
        for key, value in rms.items():
            np.testing.assert_array_equal(getattr(vector.obs_rms, key), value)

    def test_full_work_refitting_and_substituted_data_refused(self):
        data = self.admitted_fixture()
        for kwargs in ({"pipeline_smoke": False}, {"fit_normalization": True}, {"updates": 9}):
            model, vector = self.setup_model(data)
            arguments = {"fit_normalization": False, "onstate_data": data, "onstate_arm": ARMS[1]}
            arguments.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                warm_start(model, vector, *data.training_arrays(ARMS[1]), **arguments)
        model, vector = self.setup_model(data)
        actions = data.training_arrays(ARMS[1])[1].copy()
        actions[0, 0] += 0.01
        with self.assertRaisesRegex(ValueError, "admitted"):
            warm_start(model, vector, data.training_arrays(ARMS[1])[0], actions,
                       fit_normalization=False, onstate_data=data, onstate_arm=ARMS[1])
        vector.obs_rms.mean[0] += 0.01
        with self.assertRaisesRegex(ValueError, "original frozen"):
            warm_start(model, vector, *data.training_arrays(ARMS[1]),
                       fit_normalization=False, onstate_data=data, onstate_arm=ARMS[1])

    def test_failed_progress_flush_cannot_silently_repeat_a_partial_warm_start(self):
        data = self.admitted_fixture()
        model, vector = self.setup_model(data)
        def fail(*counts):
            raise OSError("owned fixture progress failure")
        with self.assertRaisesRegex(OSError, "progress failure"):
            warm_start(model, vector, *data.training_arrays(ARMS[1]), fit_normalization=False,
                       onstate_data=data, onstate_arm=ARMS[1], onstate_progress=fail)
        with self.assertRaisesRegex(ValueError, "fresh learner"):
            warm_start(model, vector, *data.training_arrays(ARMS[1]), fit_normalization=False,
                       onstate_data=data, onstate_arm=ARMS[1])


if __name__ == "__main__":
    unittest.main()
