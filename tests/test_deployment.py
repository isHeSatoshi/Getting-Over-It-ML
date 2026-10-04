import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
from deploy.bundle import build_bundle
from deploy.space_worker import (
    sanitized, ALLOWED_ARTIFACT_SUFFIXES, copy_artifact,
    batch_deadline, require_unattended_runtime, Worker)


class DeploymentTests(unittest.TestCase):
    def test_bundle_is_allowlisted_and_contains_runtime(self):
        with tempfile.TemporaryDirectory() as parent:
            bundle = build_bundle(Path(parent) / "bundle")
            self.assertTrue((bundle / "Dockerfile").exists())
            self.assertTrue((bundle / "Getting Over It v1/assets/project.json").exists())
            self.assertTrue((bundle / "research/fast_rpc.js").exists())
            self.assertTrue((bundle / "deploy/space_worker.py").exists())
            self.assertTrue((bundle / "tools/research_goal_metrics.py").exists())
            self.assertTrue((bundle / "tools/imitation_noise_probe.py").exists())
            self.assertTrue((bundle / "deployment_provenance.json").exists())
            self.assertFalse((bundle / "venv").exists())
            self.assertFalse((bundle / "chrome_profiles").exists())
            self.assertFalse((bundle / ".git").exists())
            self.assertFalse((bundle / "artifacts").exists())
            self.assertFalse((bundle / "Getting Over It v1/live_action.json").exists())
            self.assertFalse(any(p.name == ".env" for p in bundle.rglob("*")))

    def test_logs_redact_credentials(self):
        with patch.dict(os.environ, {"HF_TOKEN": "not-a-real-test-token"}):
            self.assertNotIn("not-a-real-test-token", sanitized("failure not-a-real-test-token"))

    def test_secrets_cannot_be_artifact_suffixes(self):
        self.assertNotIn(".env", ALLOWED_ARTIFACT_SUFFIXES)
        self.assertNotIn(".pem", ALLOWED_ARTIFACT_SUFFIXES)

    def test_active_telemetry_copies_only_complete_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "physical_trace.jsonl"
            source.write_bytes(b'{"tick":1}\n{"tick":')
            target = root / "snapshot/physical_trace.jsonl"
            self.assertTrue(copy_artifact(source, target, root / "status.json"))
            self.assertEqual(target.read_bytes(), b'{"tick":1}\n')

    def test_snapshot_does_not_include_records_appended_during_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "physical_trace.jsonl"
            source.write_bytes(b'{"tick":1}\n')
            target = root / "snapshot/physical_trace.jsonl"
            original_open = Path.open

            def append_after_open(path, *args, **kwargs):
                stream = original_open(path, *args, **kwargs)
                if path == source and args == ("rb",):
                    with original_open(source, "ab") as writer:
                        writer.write(b'{"tick":2}\n')
                return stream

            with patch.object(Path, "open", append_after_open):
                self.assertTrue(copy_artifact(source, target, root / "status.json"))
            self.assertEqual(target.read_bytes(), b'{"tick":1}\n')
            self.assertEqual(source.read_bytes(), b'{"tick":1}\n{"tick":2}\n')
            self.assertTrue(copy_artifact(source, target, root / "status.json"))
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_unfinished_record_spanning_snapshot_chunks_is_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "worker.log"
            source.write_bytes(b"complete line\n" + b"x" * (1024 * 1024 + 4096))
            target = root / "snapshot/worker.log"
            self.assertTrue(copy_artifact(source, target, root / "status.json"))
            self.assertEqual(target.read_bytes(), b"complete line\n")

    def test_text_without_complete_lines_produces_empty_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "monitor.csv"
            source.write_bytes(b"unfinished,header")
            target = root / "snapshot/monitor.csv"
            self.assertTrue(copy_artifact(source, target, root / "status.json"))
            self.assertEqual(target.read_bytes(), b"")

    def test_recent_checkpoint_is_not_copied_mid_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "model.zip"
            source.write_bytes(b"unfinished checkpoint")
            self.assertFalse(copy_artifact(source, root / "copy.zip", root / "status.json"))

    def test_changed_checkpoint_copy_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "model.zip"
            source.write_bytes(b"checkpoint")
            os.utime(source, (0, 0))
            target = root / "copy.zip"

            def mutate_during_copy(incoming, outgoing):
                outgoing.write_bytes(incoming.read_bytes())
                incoming.write_bytes(b"checkpoint with another chunk")

            with patch("deploy.space_worker.shutil.copyfile", mutate_during_copy):
                self.assertFalse(copy_artifact(source, target, root / "status.json"))
            self.assertFalse(target.exists())

    def test_absolute_deadline_cannot_extend_a_batch_budget(self):
        self.assertEqual(batch_deadline(100, 1, 200), 200)
        self.assertEqual(batch_deadline(100, 1, 10000), 3700)
        self.assertEqual(batch_deadline(100, 1), 3700)
        for value in ("nan", "inf", "-1"):
            with self.assertRaises(ValueError):
                batch_deadline(100, 1, value)

    def test_sleeping_or_scaled_runtime_refused_before_training(self):
        runtime = SimpleNamespace(hardware="cpu-upgrade", requested_hardware="cpu-upgrade",
                                  sleep_time=-1, raw={"replicas": {"current": 1, "requested": 1}})
        self.assertEqual(require_unattended_runtime(runtime)["sleep_time"], -1)
        runtime.sleep_time = None
        self.assertEqual(require_unattended_runtime(runtime)["sleep_policy"], "never")
        runtime.sleep_time = -1
        runtime.raw["replicas"]["current"] = 0
        self.assertEqual(require_unattended_runtime(runtime)["replicas"], 1)
        runtime.raw["replicas"]["current"] = 1
        runtime.sleep_time = 3600
        with self.assertRaisesRegex(RuntimeError, "never-sleep"):
            require_unattended_runtime(runtime)
        runtime.sleep_time = -1
        runtime.raw["replicas"]["requested"] = 2
        with self.assertRaisesRegex(RuntimeError, "replica"):
            require_unattended_runtime(runtime)
        runtime.raw["replicas"]["requested"] = 1
        runtime.hardware = "cpu-xl"
        with self.assertRaisesRegex(RuntimeError, "allocation"):
            require_unattended_runtime(runtime)

    def test_hung_final_upload_cannot_prevent_pause(self):
        worker = Worker.__new__(Worker)
        release = threading.Event()
        done = threading.Event()

        def stuck_upload():
            try:
                release.wait()
            finally:
                done.set()

        worker.sync = stuck_upload
        worker.pause = Mock()
        original = worker.bounded_sync
        worker.bounded_sync = lambda: original(timeout=0.01)
        try:
            worker.flush_and_pause()
            worker.pause.assert_called_once()
        finally:
            release.set()
            self.assertTrue(done.wait(1))

    def test_upload_failure_cannot_prevent_pause(self):
        worker = Worker.__new__(Worker)
        worker.sync = Mock(side_effect=RuntimeError("fixture upload failure"))
        worker.pause = Mock()
        worker.flush_and_pause()
        worker.pause.assert_called_once()

    def test_successful_flush_is_reported_and_then_paused(self):
        worker = Worker.__new__(Worker)
        events = []
        worker.sync = lambda: events.append("sync")
        worker.pause = lambda: events.append("pause")
        worker.flush_and_pause()
        self.assertEqual(events, ["sync", "pause"])


if __name__ == "__main__":
    unittest.main()
