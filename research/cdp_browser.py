"""Chrome DevTools Protocol launcher/attacher: no chromedriver, no Selenium.

Viewing/launch tooling only; it drives the same research page as the Selenium path.
  * launch: start a fresh Chrome (own temp profile, ephemeral debugging port) and attach to its page.
  * attach: set RL_CDP_URL=http://127.0.0.1:9222 to open a new tab in a Chrome you started yourself
    with --remote-debugging-port=9222.
Chrome is located on Windows/macOS/Linux (override with RL_CHROME_BINARY).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # corporate proxies must not see localhost


def find_chrome():
    override = os.environ.get("RL_CHROME_BINARY")
    if override:
        if not Path(override).exists():
            raise RuntimeError(f"RL_CHROME_BINARY does not exist: {override}")
        return override
    candidates = []
    if sys.platform == "win32":
        for var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(var)
            if base:
                candidates.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                        candidates.append(Path(winreg.QueryValue(key, None)))
                except OSError:
                    pass
        except ImportError:
            pass
        for var in ("PROGRAMFILES(X86)", "PROGRAMFILES"):          # Edge is Chromium: last-resort fallback
            base = os.environ.get(var)
            if base:
                candidates.append(Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    elif sys.platform == "darwin":
        candidates += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                       Path("/Applications/Chromium.app/Contents/MacOS/Chromium")]
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))
    for path in candidates:
        if path.exists():
            return str(path)
    raise RuntimeError("Chrome not found. Install Google Chrome or set RL_CHROME_BINARY to chrome.exe / the Chrome binary.")


def _http_json(url, method="GET", timeout=10):
    request = urllib.request.Request(url, method=method)
    with _NO_PROXY.open(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body.strip().startswith(("{", "[")) else body


class CdpSession:
    """One page target controlled over a CDP websocket."""

    def __init__(self, ws_url, process=None, profile=None, attach_base=None, target_id=None):
        from websockets.sync.client import connect
        self._ws = connect(ws_url, max_size=None, compression=None, ping_interval=None, open_timeout=30)
        self._id = 0
        self._process, self._profile, self._attach_base, self._target_id = process, profile, attach_base, target_id

    @classmethod
    def start(cls, url, headless=True):
        base_attach = os.environ.get("RL_CDP_URL")
        if base_attach:
            base = base_attach.rstrip("/")
            target = _http_json(f"{base}/json/new?{urllib.parse.quote(url, safe='')}", method="PUT")
            return cls(target["webSocketDebuggerUrl"], attach_base=base, target_id=target["id"])
        profile = tempfile.mkdtemp(prefix="rl-chrome-")
        args = [find_chrome(), f"--user-data-dir={profile}", "--remote-debugging-port=0", "--no-first-run",
                "--no-default-browser-check", "--mute-audio", "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows",
                "--disable-features=CalculateNativeWinOcclusion", "--force-device-scale-factor=1",
                "--window-size=1100,820"]
        if headless:
            args.append("--headless=new")
        else:
            # Headed runs must match the verified reference rasterization: the SVG skin silhouettes
            # that feed collision are rasterized through a 2D canvas, and an accelerated 2D canvas
            # diverges from the reference at tick 2000 (measured; see LOCAL_REPLAY.md).
            args.append("--disable-accelerated-2d-canvas")
        if os.environ.get("RL_CHROME_NO_SANDBOX") == "1":
            args.append("--no-sandbox")
        if os.environ.get("RL_CHROME_CONTAINER") == "1":
            args += ["--disable-dev-shm-usage", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
        extra = os.environ.get("RL_CHROME_EXTRA_FLAGS", "").split()   # e.g. GPU/rasterization flags for recording
        args += extra
        args.append(url)
        env = {k: v for k, v in os.environ.items() if k not in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "RL_CONTROL_TOKEN")}
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            deadline = time.time() + 40
            while not port_file.exists():
                if process.poll() is not None:
                    raise RuntimeError(f"Chrome exited early (code {process.returncode}); try RL_CHROME_BINARY or --headless")
                if time.time() > deadline:
                    raise RuntimeError("Chrome did not publish a DevTools port")
                time.sleep(0.1)
            time.sleep(0.1)
            port = int(port_file.read_text().splitlines()[0])
            origin = url.split("#")[0].split("?")[0]
            while True:
                pages = [t for t in _http_json(f"http://127.0.0.1:{port}/json/list")
                         if t.get("type") == "page" and t.get("url", "").startswith(origin)]
                if pages:
                    break
                if time.time() > deadline:
                    raise RuntimeError("Game page target did not appear")
                time.sleep(0.2)
            return cls(pages[0]["webSocketDebuggerUrl"], process=process, profile=profile)
        except BaseException:
            cls._kill(process, profile)
            raise

    def call(self, method, **params):
        self._id += 1
        mid = self._id
        self._ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            message = json.loads(self._ws.recv(timeout=90))
            if message.get("id") == mid:
                if "error" in message:
                    raise RuntimeError(f"CDP {method}: {message['error']}")
                return message.get("result", {})

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", expression=f"Promise.resolve().then(()=>({expression}))",
                           awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in result:
            detail = result["exceptionDetails"]
            raise RuntimeError((detail.get("exception") or {}).get("description") or detail.get("text", "page error"))
        return result.get("result", {}).get("value")

    def bring_to_front(self):
        try:
            self.call("Page.bringToFront")
        except Exception:
            pass

    @staticmethod
    def _kill(process, profile):
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if profile:
            for _ in range(10):                                # Windows may hold profile files briefly
                shutil.rmtree(profile, ignore_errors=True)
                if not Path(profile).exists():
                    break
                time.sleep(0.5)

    def close(self):
        try:
            self._ws.close()
        except Exception:
            pass
        if self._attach_base and self._target_id:
            try:
                _http_json(f"{self._attach_base}/json/close/{self._target_id}")
            except Exception:
                pass
        self._kill(self._process, self._profile)
