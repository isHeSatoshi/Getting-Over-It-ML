"""Synchronous real-renderer bridge. Uses the visible embedded pane when present."""
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import warnings

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class BrowserBridge:
    def __init__(self, driver="auto", headless=True, runtime_config=None, page_fragment=None):
        self._server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._state = None
        self.driver = None
        self._cli = None
        self._cdp = None
        try:
            url = f"http://127.0.0.1:{self._server.server_port}/Getting%20Over%20It%20v1/research.html"
            if runtime_config:
                from urllib.parse import urlencode
                url += "?" + urlencode(runtime_config)
            if page_fragment:
                from urllib.parse import urlencode
                url += "#" + urlencode(page_fragment)
            cdp = os.environ.get("AGENT_BROWSER_CDP")
            if driver == "auto":
                driver = "embedded" if cdp else "selenium"
            if driver == "embedded":
                executable = shutil.which("agent-browser")
                if not executable or not cdp:
                    raise RuntimeError("Embedded driver needs agent-browser and AGENT_BROWSER_CDP")
                self._cli = [executable, "--cdp", cdp, "--json"]
                self._command(["open", url])
                self._command(["wait", "--fn", "window.researchReady || window.researchError"])
            elif driver == "selenium":
                try:
                    self._start_selenium(url, headless)
                except Exception as exc:
                    if os.environ.get("RL_BROWSER_DRIVER_FALLBACK", "1") != "1":
                        raise
                    warnings.warn(f"Selenium/chromedriver launch failed ({exc!r}); falling back to CDP")
                    if self.driver:
                        try:
                            self.driver.quit()
                        except Exception:
                            pass
                        self.driver = None
                    driver = "cdp"
            if driver == "cdp":
                self._start_cdp(url, headless)
            elif driver not in ("embedded", "selenium"):
                raise ValueError("Unknown browser driver")
            error = self.evaluate("window.researchError || null")
            if error:
                raise RuntimeError(error)
            self._state = self.evaluate("window.research.state()")
        except BaseException:
            self.close()
            raise

    def _start_selenium(self, url, headless):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        else:
            # Headed must match the verified reference rasterization (see research/cdp_browser.py).
            options.add_argument("--disable-accelerated-2d-canvas")
        options.add_argument("--mute-audio")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        if os.environ.get("RL_CHROME_BINARY"):
            options.binary_location = os.environ["RL_CHROME_BINARY"]
        if os.environ.get("RL_CHROME_CONTAINER") == "1":
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--use-gl=angle")
            options.add_argument("--use-angle=swiftshader")
            options.add_argument("--enable-unsafe-swiftshader")
        if os.environ.get("RL_CHROME_NO_SANDBOX") == "1":
            options.add_argument("--no-sandbox")
        # Chrome and its driver do not need deployment credentials.
        browser_env = {k: v for k, v in os.environ.items()
                       if k not in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "RL_CONTROL_TOKEN")}
        service = Service(executable_path=os.environ["RL_CHROMEDRIVER"], env=browser_env) if os.environ.get(
            "RL_CHROMEDRIVER") else Service(env=browser_env)
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_script_timeout(60)
        self.driver.get(url)
        WebDriverWait(self.driver, 60).until(
            lambda d: d.execute_script("return window.researchReady || window.researchError"))

    def _start_cdp(self, url, headless):
        import time
        from research.cdp_browser import CdpSession
        self._cdp = CdpSession.start(url, headless=headless)
        if not headless:
            self._cdp.bring_to_front()
        deadline = time.time() + 60
        while not self._cdp.evaluate("window.researchReady || window.researchError"):
            if time.time() > deadline:
                raise RuntimeError("Game page did not become ready")
            time.sleep(0.2)

    def _command(self, args, source=None):
        result = subprocess.run(self._cli + args, input=source, text=True,
                                capture_output=True, timeout=90, check=False)
        try:
            message = json.loads(result.stdout)
        except json.JSONDecodeError:
            message = {}
        if result.returncode:
            detail = message.get("error") or result.stderr.strip() or "No diagnostic output"
            raise RuntimeError(f"Browser command failed (exit {result.returncode}): {detail}")
        if not message.get("success"):
            raise RuntimeError(str(message.get("error") or "Browser returned an invalid response"))
        return message["data"]

    def evaluate(self, expression):
        if self._cli:
            return self._command(["eval", "--stdin"], expression).get("result")
        if self._cdp:
            return self._cdp.evaluate(expression)
        result = self.driver.execute_async_script(
            "const done=arguments[arguments.length-1];"
            "Promise.resolve().then(()=>(" + expression + "))"
            ".then(value=>done({value})).catch(error=>done({error:String(error.stack||error)}));")
        if "error" in result:
            raise RuntimeError(result["error"])
        return result.get("value")

    def reset(self, seed=0):
        self._state = self.evaluate(f"window.research.reset({int(seed)})")
        return dict(self._state)

    def read_state(self):
        return dict(self._state)

    def step_commands(self, commands):
        trace = self.evaluate(f"window.research.step({json.dumps(commands, allow_nan=False)})")
        if trace:
            self._state = trace[-1]
        return trace

    def close(self):
        # Never close the user's embedded browser or any unrelated process.
        if self._cdp:
            self._cdp.close()
            self._cdp = None
        if self.driver:
            self.driver.quit()
            self.driver = None
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join(timeout=5)
            self._server = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
