"""Owned-process resource measurement. Never inspect other processes' arguments."""
import argparse
from datetime import datetime, timezone
import json
import os
import platform
import statistics
import subprocess
import threading
import time
from pathlib import Path

import psutil
from research.browser_bridge import ROOT


def effective_limits(cgroup_root=Path("/sys/fs/cgroup")):
    """Container limits, not the often much larger host reported by psutil."""
    memory = psutil.virtual_memory()
    result = {"logical_cpus": float(psutil.cpu_count(logical=True) or 1),
              "ram_bytes": memory.total, "available_ram_bytes": memory.available}
    try:
        result["logical_cpus"] = min(result["logical_cpus"], len(psutil.Process().cpu_affinity()))
    except (AttributeError, OSError, psutil.Error):
        pass
    try:
        quota, period = (cgroup_root / "cpu.max").read_text().split()
        if quota != "max":
            result["logical_cpus"] = min(result["logical_cpus"], int(quota) / int(period))
        maximum = (cgroup_root / "memory.max").read_text().strip()
        if maximum != "max":
            limit = int(maximum)
            current = int((cgroup_root / "memory.current").read_text().strip())
            result["ram_bytes"] = min(result["ram_bytes"], limit)
            result["available_ram_bytes"] = min(result["available_ram_bytes"], max(0, limit - current))
            result["source"] = "cgroup_v2"
    except (OSError, ValueError, ZeroDivisionError):
        result.setdefault("source", "host_or_unlimited")
        try:
            quota = int((cgroup_root / "cpu/cpu.cfs_quota_us").read_text())
            period = int((cgroup_root / "cpu/cpu.cfs_period_us").read_text())
            if quota > 0:
                result["logical_cpus"] = min(result["logical_cpus"], quota / period)
            limit = int((cgroup_root / "memory/memory.limit_in_bytes").read_text())
            current = int((cgroup_root / "memory/memory.usage_in_bytes").read_text())
            result["ram_bytes"] = min(result["ram_bytes"], limit)
            result["available_ram_bytes"] = min(result["available_ram_bytes"], max(0, limit - current))
            result["source"] = "cgroup_v1"
        except (OSError, ValueError, ZeroDivisionError):
            pass
    return result


def hardware():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(ROOT))
    result = {"os": platform.platform(), "physical_cores": psutil.cpu_count(logical=False),
              "logical_processors": psutil.cpu_count(logical=True), "ram_bytes": memory.total,
              "available_ram_bytes": memory.available, "project_disk_free_bytes": disk.free}
    if os.name == "nt":
        command = ("$c=Get-CimInstance Win32_Processor; $m=Get-CimInstance Win32_PhysicalMemory;"
                   "@{cpu_name=$c.Name;ram_module_speeds_mts=@($m|ForEach-Object{$_.ConfiguredClockSpeed})}"
                   "|ConvertTo-Json -Compress")
        reply = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                               text=True, capture_output=True, timeout=20)
        if reply.returncode == 0:
            result.update(json.loads(reply.stdout))
    result["gpu_shared"] = gpu()
    result["effective_limits"] = effective_limits()
    return result


def gpu():
    try:
        reply = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                                "--format=csv,noheader,nounits"], text=True, capture_output=True, timeout=5)
        if reply.returncode:
            return {"available": False}
        entries = []
        for line in reply.stdout.splitlines():
            name, total, used, utilization = [s.strip() for s in line.split(",")]
            entries.append({"name": name, "vram_mib": float(total), "used_mib": float(used),
                            "utilization_percent": float(utilization)})
        return {"available": True, "devices": entries, "attribution": "whole-device, not owned-worker memory"}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False}


class OwnedProcessSampler:
    def __init__(self, interval=0.2):
        self.root = psutil.Process()
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()
        self._thread = None
        self._previous = {}

    def sample(self):
        now = time.perf_counter()
        processes = [self.root] + self.root.children(recursive=True)
        rss = private = threads = 0
        core_usage = 0.0
        for process in processes:
            try:
                mem = process.memory_info()
                times = process.cpu_times()
                cpu = times.user + times.system
                key = (process.pid, process.create_time())
                if key in self._previous:
                    old_cpu, old_time = self._previous[key]
                    core_usage += max(0, cpu - old_cpu) / (now - old_time)
                self._previous[key] = (cpu, now)
                rss += mem.rss
                private += getattr(mem, "private", 0)
                threads += process.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        record = {"seconds": now, "rss_bytes": rss, "private_bytes": private,
                  "cpu_core_equivalents": core_usage, "threads": threads, "processes": len(processes)}
        self.samples.append(record)

    def __enter__(self):
        self.sample()
        def loop():
            while not self._stop.wait(self.interval):
                self.sample()
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args):
        self._stop.set()
        self._thread.join(timeout=5)
        self.sample()

    def summary(self):
        return {
            "samples": len(self.samples), "peak_rss_mib": max(s["rss_bytes"] for s in self.samples) / 2**20,
            "peak_private_mib": max(s["private_bytes"] for s in self.samples) / 2**20,
            "median_cpu_core_equivalents": statistics.median(s["cpu_core_equivalents"] for s in self.samples[1:]),
            "peak_cpu_core_equivalents": max(s["cpu_core_equivalents"] for s in self.samples),
            "peak_threads": max(s["threads"] for s in self.samples),
            "note": "RSS can double-count shared pages; private commit is Windows-specific; CPU=one core equivalents",
        }


def replay_buffer_bytes(transitions, observation_dim=217, action_dim=2):
    # SB3 stores both observations; extra arrays are float32 rewards/dones/timeouts.
    return transitions * ((2 * observation_dim + action_dim + 3) * 4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions", type=int, default=256)
    args = parser.parse_args()
    if not 32 <= args.decisions <= 512:
        parser.error("Resource measurement budget must be 32..512 decisions")
    from research.backends import make_bridge
    from research.env import RealGettingOverItEnv
    import torch
    torch.set_num_threads(1)
    output = ROOT / "artifacts" / ("resources_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    report = {"hardware": hardware(), "phases": {}, "replay_buffer_estimates": {
        str(n): replay_buffer_bytes(n) for n in (100000, 200000, 1000000)}}
    with OwnedProcessSampler() as startup:
        worker = make_bridge("fast")
        env = RealGettingOverItEnv(bridge=worker, horizon=args.decisions + 1)
        env.reset(seed=42)
    report["phases"]["worker_and_terrain_startup"] = startup.summary()
    with worker:
        with OwnedProcessSampler() as active:
            begin = time.perf_counter()
            for _ in range(args.decisions):
                _, _, term, trunc, _ = env.step([0, -0.625])
                if term or trunc: break
            elapsed = time.perf_counter() - begin
        report["phases"]["one_fast_worker_steps"] = {**active.summary(), "decisions_per_second": args.decisions / elapsed}
        with OwnedProcessSampler() as evaluation_peak:
            with make_bridge("reference", "selenium") as reference:
                evaluation = RealGettingOverItEnv(bridge=reference, horizon=64)
                evaluation.reset(seed=42)
                for _ in range(32):
                    evaluation.step([0, -0.625])
        report["phases"]["training_worker_plus_reference_evaluation"] = evaluation_peak.summary()
    report["gpu_shared_after"] = gpu()
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("Evidence:", output)


if __name__ == "__main__":
    main()
