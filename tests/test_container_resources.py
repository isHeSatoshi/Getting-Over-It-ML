from pathlib import Path
import tempfile
import unittest
from research.resources import effective_limits


class ContainerLimits(unittest.TestCase):
    def test_reads_declared_cpu_and_memory_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "cpu.max").write_text("200000 100000")
            (root / "memory.max").write_text(str(1024 * 1024 * 1024))
            (root / "memory.current").write_text(str(256 * 1024 * 1024))
            limits = effective_limits(root)
            self.assertLessEqual(limits["logical_cpus"], 2)
            self.assertEqual(limits["ram_bytes"], 1024**3)
            self.assertLessEqual(limits["available_ram_bytes"], 768 * 1024**2)
            self.assertEqual(limits["source"], "cgroup_v2")


if __name__ == "__main__":
    unittest.main()
