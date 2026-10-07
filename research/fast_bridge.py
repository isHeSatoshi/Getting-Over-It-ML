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
    def __init__(self, headless=None):
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
            super().__init__(driver="selenium", headless=headless, runtime_config={"fast": "true"},
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

    def step_commands(self, commands):
        trace = self._rpc("step", commands=commands)
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
