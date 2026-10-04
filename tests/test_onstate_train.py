import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research.onstate_train import NoTrainingPhysics, main, run


class OnStateTrainerTests(unittest.TestCase):
    def test_cli_refuses_full_local_work_before_data_access(self):
        args = ["trainer", "--arm", "original_demonstrations", "--seed", "9",
                "--dataset", str(Path.cwd() / "missing"), "--output-dir", str(Path.cwd() / "unused"),
                "--remote-training"]
        with patch("sys.argv", args), patch("research.onstate_train.load") as load:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main()
            load.assert_not_called()

    def test_unadmitted_direct_run_never_reads_data(self):
        args = SimpleNamespace(arm="original_plus_logged_success", seed=9, smoke=False,
                               remote_training=True, dataset="missing", output_dir="unused")
        with patch("research.onstate_train.load") as load:
            with self.assertRaisesRegex(ValueError, "validated parent"):
                run(args)
            load.assert_not_called()

    def test_training_interface_refuses_all_physics(self):
        interface = NoTrainingPhysics()
        with self.assertRaisesRegex(RuntimeError, "never reset"):
            interface.reset()
        with self.assertRaisesRegex(RuntimeError, "never step"):
            interface.step([0, 0])


if __name__ == "__main__":
    unittest.main()
