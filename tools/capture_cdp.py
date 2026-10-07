"""Capture real gameplay frames from the running original game over CDP.

chromedriver is unstable in this desktop session, so Chrome is driven directly
through the DevTools Protocol. Everything happens in one process: the asset
server, the browser, the stepping loop, and the PNG writes. This is capture
tooling for the video, not part of the challenge runtime.
"""
import base64
import json
import math
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PAGE = "/Getting%20Over%20It%20v1/research.html"
LOG_PATH = ROOT / "_cap.log"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def log(*parts):
    line = " ".join(str(p) for p in parts)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_port


class Cdp:
    """Minimal Chrome DevTools Protocol client over one target's WebSocket."""

    def __init__(self, ws_url):
        import websocket
        self.ws = websocket.create_connection(ws_url, timeout=180)
        self._id = 0

    def call(self, method, **params):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") != self._id:
                continue
            if "error" in message:
                raise RuntimeError(f"{method}: {message['error']}")
            return message.get("result", {})

    def evaluate(self, expression, await_promise=False):
        result = self.call("Runtime.evaluate", expression=expression,
                           returnByValue=True, awaitPromise=await_promise)
        if result.get("exceptionDetails"):
            details = result["exceptionDetails"]
            text = details.get("exception", {}).get("description") or details.get("text")
            raise RuntimeError(str(text))
        return result["result"].get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def start_chrome(port, profile):
    shutil.rmtree(profile, ignore_errors=True)
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--no-sandbox",
         "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
         "--mute-audio", "--hide-scrollbars", "--disable-extensions",
         "--disable-background-timer-throttling", "--remote-allow-origins=*",
         f"--user-data-dir={profile}", f"--remote-debugging-port={port}",
         "--window-size=680,700", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(160):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                return proc, json.load(r)["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("Chrome did not expose a debugging endpoint")


def open_page(browser_port, url):
    """Reuse the startup tab and drive it to the game page."""
    for _ in range(160):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{browser_port}/json/list", timeout=5) as r:
                targets = json.load(r)
        except Exception:
            targets = []
        for t in targets:
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl") \
                    and t.get("url", "").startswith(url):
                page = Cdp(t["webSocketDebuggerUrl"])
                page.call("Runtime.enable")
                page.call("Page.enable")
                return page
        pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        if pages:
            page = Cdp(pages[0]["webSocketDebuggerUrl"])
            page.call("Runtime.enable")
            page.call("Page.enable")
            page.call("Page.navigate", url=url)
            return page
        time.sleep(0.25)
    raise RuntimeError("target page never appeared")


def wait_ready(page):
    for _ in range(240):
        flag = page.evaluate(
            "window.researchError ? window.researchError : "
            "(window.researchReady ? 'ready' : 'wait')")
        if flag == "ready":
            return True
        if flag not in ("wait", None, "", "pending"):
            raise RuntimeError(flag)
        time.sleep(0.5)
    raise RuntimeError("research runtime never became ready")


def canvas_data_url(page):
    """Read the canvas backing store directly; headless compositing can skip it."""
    return page.evaluate("""(() => {
        const c = document.querySelector('canvas');
        if (!c) return null;
        return c.toDataURL('image/png');
    })()""")


def shot(page, out, name):
    """Capture a real composited frame of the stage.

    The stage is a WebGL canvas, so its backing store cannot be read back
    directly. Force a paint and take a composited screenshot instead.
    """
    box = None
    best = b""
    for attempt in range(5):
        page.evaluate("window.research.render()")
        # Two rAF ticks guarantee the WebGL frame reaches the compositor.
        page.evaluate("new Promise(r => requestAnimationFrame("
                      "() => requestAnimationFrame(() => r(true))))",
                      await_promise=True)
        box = page.evaluate(
            "(() => { const c = document.querySelector('canvas');"
            "if (!c) return null; const r = c.getBoundingClientRect();"
            "return {x: r.x, y: r.y, width: r.width, height: r.height}; })()")
        if not box or box["width"] < 2:
            data = page.call("Page.captureScreenshot", format="png")
        else:
            data = page.call("Page.captureScreenshot", format="png",
                             captureBeyondViewport=False, clip={
                                 "x": box["x"], "y": box["y"],
                                 "width": box["width"], "height": box["height"],
                                 "scale": 1})
        raw = base64.b64decode(data["data"])
        if len(raw) > len(best):
            best = raw
        if len(raw) > 20000:
            break
    (out / f"{name}.png").write_bytes(best)
    log("SHOT", name, len(best))
    if best:
        (out / f"{name}.png").write_bytes(best)
        log("SHOT", name, "canvas", len(best))
        return
    box = page.evaluate(
        "(() => { const c = document.querySelector('canvas');"
        "if (!c) return null; const r = c.getBoundingClientRect();"
        "return {x: r.x, y: r.y, width: r.width, height: r.height}; })()")
    if not box or box["width"] < 2:
        data = page.call("Page.captureScreenshot", format="png")
    else:
        data = page.call("Page.captureScreenshot", format="png", clip={
            "x": box["x"], "y": box["y"],
            "width": box["width"], "height": box["height"], "scale": 1})
    raw = base64.b64decode(data["data"])
    (out / f"{name}.png").write_bytes(raw)
    log("SHOT", name, "screenshot", len(raw))


def cmds(points):
    return [{"x": float(x), "y": float(y), "id": i + 1, "down": False}
            for i, (x, y) in enumerate(points)]


def step(page, commands):
    return page.evaluate(f"window.research.step({json.dumps(commands)})")


def render_state(page):
    return page.evaluate("""(() => {
        const c = document.querySelector('canvas');
        const r = window.vm && window.vm.renderer;
        const p = window.vm.runtime.targets.find(t => t.getName() === 'Player');
        const levels = window.vm.runtime.targets.filter(t => t.getName() === 'Level');
        return {
            canvas: c ? [c.width, c.height, c.clientWidth, c.clientHeight] : null,
            skins: r && r._allSkins ? Object.keys(r._allSkins).length : null,
            touchable: r && r.touchableDrawables ? r.touchableDrawables.length : null,
            player: p ? [p.visible, Math.round(p.x), Math.round(p.y)] : null,
            levelCount: levels.length,
            levelVisible: levels.filter(t => t.visible).length,
        };
    })()""")


def capture(page, out, scale=1):
    """Step the real game and save one cropped stage frame per beat."""
    results = {}

    # Beat 1: the starting position on the original terrain.
    page.evaluate("window.research.reset(1001)")
    shot(page, out, "01_spawn")
    results["spawn_y"] = page.evaluate("window.research.state().player_world_y")
    log("spawn", results["spawn_y"])

    # Beat 2: a scripted hammer swing on the ground.
    page.evaluate("window.research.reset(1001)")
    swing = [(90 * math.cos(i / 90 * 2 * math.pi), 90 * math.sin(i / 90 * 2 * math.pi))
             for i in range(90)]
    step(page, cmds(swing))
    shot(page, out, "02_swing")
    results["swing_y"] = page.evaluate("window.research.state().player_world_y")
    log("swing", results["swing_y"])

    # Beat 3: a sustained downward push lifts the body onto the rim.
    page.evaluate("window.research.reset(1001)")
    step(page, cmds([(0, -128)] * 120))
    shot(page, out, "03_push")
    results["push_y"] = page.evaluate("window.research.state().player_world_y")
    log("push", results["push_y"])

    # Beat 4: keep pushing to reach the rim lip.
    step(page, cmds([(0, -128)] * 60))
    shot(page, out, "04_rise")
    results["rise_y"] = page.evaluate("window.research.state().player_world_y")
    log("rise", results["rise_y"])

    # Beat 5: drive the hammer sideways across the rim.
    step(page, cmds([(120 * math.cos(i / 60 * math.pi), -40) for i in range(60)]))
    shot(page, out, "05_side")
    results["side_y"] = page.evaluate("window.research.state().player_world_y")
    log("side", results["side_y"])

    return results


def main():
    LOG_PATH.unlink(missing_ok=True)
    log("=== capture run ===")
    out = ROOT / "artifacts" / "video_capture"
    out.mkdir(parents=True, exist_ok=True)
    httpd, asset_port = start_server()
    browser_port = free_port()
    profile = ROOT / "_cdp_profile"
    chrome, browser_ws = start_chrome(browser_port, profile)
    page = None
    try:
        page = open_page(browser_port, f"http://127.0.0.1:{asset_port}{PAGE}")
        wait_ready(page)
        state = page.evaluate("window.research.state()")
        log("BACKEND", state["backend"], "SCHEMA", state["schema_version"])
        results = capture(page, out)
        log("RESULTS", json.dumps(results, indent=2))
        log("CAPTURE_DIR", out)
    except Exception as error:
        log("FAILED", type(error).__name__, error)
        raise
    finally:
        if page:
            page.close()
        chrome.terminate()
        try:
            chrome.wait(timeout=10)
        except Exception:
            chrome.kill()
        httpd.shutdown()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
