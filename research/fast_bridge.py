"""Accelerated original game: exact collision memo and persistent local RPC.

This is not a custom physics approximation. Chrome still runs the original
compiled project and real renderer collision implementation.
"""
import json
import os
import secrets
import threading

from research.browser_bridge import BrowserBridge


class FastBridge(BrowserBridge):
    def __init__(self, headless=None, presentation=False):
        from websockets.sync.server import serve
        self._rpc_ready = False
        self._connection = None
        self._socket_server = None
        self._socket_thread = None
        self._connected = threading.Event()
        self._stop = threading.Event()
        self._request_id = 0
        self._rpc_lock = threading.Lock()
        token = secrets.token_urlsafe(32)

        def handler(connection):
            try:
                hello = json.loads(connection.recv(timeout=10))
                credential = hello.get("token") if isinstance(hello, dict) else None
                if not isinstance(credential, str) or not secrets.compare_digest(credential, token):
                    connection.close(code=1008, reason="Unauthorized")
                    return
                if self._connection is not None:
                    connection.close(code=1008, reason="Worker already connected")
                    return
                # Only the owned same-origin game page may connect.
                expected = f"http://127.0.0.1:{self._server.server_port}"
                if connection.request.headers.get("Origin") != expected:
                    connection.close(code=1008, reason="Wrong origin")
                    return
                self._connection = connection
                self._connected.set()
                self._stop.wait()
            finally:
                if self._stop.is_set():
                    connection.close()

        self._socket_server = serve(handler, "127.0.0.1", 0, compression=None,
                                    ping_interval=None, close_timeout=2, max_size=16 * 1024 * 1024)
        self._socket_thread = threading.Thread(target=self._socket_server.serve_forever, daemon=True)
        self._socket_thread.start()
        if headless is None:
            headless = not bool(os.environ.get("FACTORY_DESKTOP_CDP_PORT"))
        try:
            # RL_BROWSER_DRIVER=selenium|cdp. Windows defaults to CDP (no chromedriver); elsewhere Selenium
            # with automatic CDP fallback if chromedriver fails to start.
            driver = os.environ.get("RL_BROWSER_DRIVER") or ("cdp" if os.name == "nt" else "selenium")
            config = {"fast": "true"}
            if presentation:
                # Reproduce the title-screen state the real game has at play start, so the game's own
                # HUD (timer digits) and win animation render. Viewing only; physics untouched.
                config["present"] = "true"
            super().__init__(driver=driver, headless=headless, runtime_config=config,
                             page_fragment={"rpc_port": self._socket_server.socket.getsockname()[1],
                                            "rpc_token": token})
            if not self._connected.wait(timeout=30):
                raise RuntimeError("Fast worker did not authenticate")
            self._rpc_ready = True
            self._state = self._rpc("state")
        except BaseException:
            self.close()
            raise

    def _rpc(self, method, **payload):
        if not self._rpc_ready or self._connection is None:
            raise RuntimeError("Fast worker is unavailable")
        with self._rpc_lock:
            self._request_id += 1
            request_id = self._request_id
            self._connection.send(json.dumps({"id": request_id, "method": method, **payload}, allow_nan=False))
            reply = json.loads(self._connection.recv(timeout=60))
            if reply.get("id") != request_id:
                raise RuntimeError("Out-of-order fast worker response")
            if "error" in reply:
                raise RuntimeError(reply["error"])
            return reply["value"]

    def evaluate(self, expression):
        if self._rpc_ready:
            return self._rpc("evaluate", expression=expression)
        return super().evaluate(expression)

    def reset(self, seed=0):
        self._state = self._rpc("reset", seed=int(seed))
        return dict(self._state)

    def snapshot(self):
        """Exact in-page state handle (see research/runtime.js); stays in the browser."""
        return int(self._rpc("snapshot"))

    def restore(self, handle):
        self._state = self._rpc("restore", snapshot=int(handle))
        return dict(self._state)

    def drop_snapshot(self, handle):
        self._rpc("drop_snapshot", snapshot=int(handle))

    def seed_cell(self, cx, cy):
        return self._rpc("seed_cell", cx=cx, cy=cy)

    def explore_segment(self, snapshot, actions, hold, cx, cy, opts=None):
        """Step decisions from a snapshot; page registers new/faster cells (search bookkeeping)."""
        return self._rpc("explore_segment", snapshot=int(snapshot), actions=actions,
                         hold=int(hold), cx=cx, cy=cy, opts=opts)

    def register_current(self, cx, cy, retained):
        return self._rpc("register_current", cx=cx, cy=cy, retained=bool(retained))

    def rollout_batch(self, snapshot, candidates, hold, goal):
        return self._rpc("rollout_batch", snapshot=int(snapshot), candidates=candidates, hold=int(hold), goal=goal)

    def set_phi(self, W, H, x0, y1, unit, data):
        """Install an optional search-guidance potential grid (row-major, world y descending)."""
        return self._rpc("set_phi", W=int(W), H=int(H), x0=float(x0), y1=float(y1), unit=float(unit), data=data)

    def clear_cells(self):
        self._rpc("clear_cells")

    def step_commands(self, commands, after=False):
        """Step commands. With after=True, keep stepping past the win flag (ending playback, viewing only)."""
        trace = self._rpc("step", commands=commands, after=bool(after))
        if trace:
            self._state = trace[-1]
        return trace

    def close(self):
        self._rpc_ready = False
        self._stop.set()
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._socket_server is not None:
            self._socket_server.shutdown()
            self._socket_server = None
        if self._socket_thread is not None:
            self._socket_thread.join(timeout=5)
            self._socket_thread = None
        if getattr(self, "_server", None) is not None:
            super().close()
