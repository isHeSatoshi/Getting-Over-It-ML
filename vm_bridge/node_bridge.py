import os
import sys
import json
import time
import subprocess
from typing import Optional, Dict, Any

class NodeBridge:
    """High-speed headless Node.js scratch-vm Physics Server Bridge."""

    def __init__(self, port: int = 8000, headless: bool = True, driver_path: Optional[str] = None,
                 log_file=None, node_cmd: str = "node"):
        self.port = port
        self.log_file = log_file
        self.process = None
        self._last_state = None

        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_js = os.path.join(script_dir, "physics_server.js")

        self._log(f"[NodeBridge] Launching Node.js Physics Server ({server_js})...")

        # Drain stderr to DEVNULL to avoid OS pipe deadlock caused by scratch-vm logging
        self.process = subprocess.Popen(
            [node_cmd, server_js],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )

        # Wait for ready signal
        ready_line = self.process.stdout.readline()
        if not ready_line:
            raise RuntimeError("Node Physics Server process exited immediately.")
        
        try:
            ready_data = json.loads(ready_line)
            if ready_data.get("type") != "ready":
                raise RuntimeError(f"Unexpected ready response: {ready_line}")
            self._log(f"[NodeBridge] Physics Server ready! ({ready_data.get('targets')} targets loaded)")
        except Exception as e:
            raise RuntimeError(f"Failed to parse ready output '{ready_line}': {e}")

    def _log(self, msg: str):
        print(msg)
        sys.stdout.flush()
        if self.log_file:
            try:
                self.log_file.write(msg + "\n")
                self.log_file.flush()
            except Exception:
                pass

    def _send_cmd(self, cmd_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Physics Server process is dead.")
        
        line = json.dumps(cmd_dict) + "\n"
        self.process.stdin.write(line)
        self.process.stdin.flush()

        resp_line = self.process.stdout.readline()
        if not resp_line:
            raise RuntimeError("Physics Server process closed stdout stream.")
        
        return json.loads(resp_line)

    def reset(self) -> Optional[Dict[str, Any]]:
        resp = self._send_cmd({"type": "reset"})
        state = resp.get("state")
        self._last_state = state
        return state

    def read_state(self) -> Optional[Dict[str, Any]]:
        return self._last_state

    def step_screen_pointer(self, command_id: int, screen_x: float, screen_y: float,
                            is_down: bool = True, n_steps: int = 1, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        nx = max(-1.0, min(1.0, float(screen_x) / 240.0))
        ny = max(-1.0, min(1.0, float(screen_y) / 180.0))

        resp = self._send_cmd({
            "type": "step",
            "command_id": int(command_id),
            "nx": nx,
            "ny": ny,
            "is_down": bool(is_down),
            "n_steps": int(n_steps)
        })

        if resp.get("type") == "state":
            state = resp.get("state")
            self._last_state = state
            return state
        return None

    def close(self):
        self._log("[NodeBridge] Closing NodeBridge...")
        if self.process:
            try:
                if self.process.poll() is None:
                    self._send_cmd({"type": "close"})
            except Exception:
                pass
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                pass
            self.process = None
        self._log("[NodeBridge] NodeBridge closed.")
