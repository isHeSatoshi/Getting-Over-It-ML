"""Run challenge evaluation cases over CDP.

chromedriver crashes in this desktop session, so this reuses the CDP client to
drive the real game and exercise `challenge.evaluate` end to end.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import capture_cdp as cap
from challenge.baselines import ConstantPushPolicy, NullPolicy
from challenge.env import GettingOverItChallengeEnv
from challenge.tiers import STANDARD_CASES

ROOT_DIR = Path(__file__).resolve().parents[1]


class CdpBridge:
    """Minimal bridge with the interface `RealGettingOverItEnv` expects."""

    def __init__(self, page):
        self.page = page

    def reset(self, seed=0):
        self.page.evaluate(f"window.research.reset({int(seed)})")
        return dict(self.page.evaluate("window.research.state()"))

    def step_commands(self, commands):
        return self.page.evaluate(f"window.research.step({json.dumps(commands)})")

    def evaluate(self, expression):
        return self.page.evaluate(expression)

    def read_state(self):
        return dict(self.page.evaluate("window.research.state()"))

    def close(self):
        pass


def main():
    httpd, port = cap.start_server()
    bp = cap.free_port()
    profile = ROOT_DIR / "_cdp_profile"
    chrome, bws = cap.start_chrome(bp, profile)
    page = None
    try:
        page = cap.open_page(bp, f"http://127.0.0.1:{port}{cap.PAGE}")
        cap.wait_ready(page)
        bridge = CdpBridge(page)
        env = GettingOverItChallengeEnv(bridge=bridge)

        from challenge.evaluate import run_case
        for policy in (NullPolicy(), ConstantPushPolicy()):
            case = STANDARD_CASES[0]
            started = time.time()
            result = run_case(env, policy, case, max_decisions=600)
            result["wall_seconds"] = round(time.time() - started, 2)
            print(policy.__class__.__name__, json.dumps(result, indent=2), flush=True)
        env.close()
    finally:
        if page:
            page.close()
        chrome.terminate()
        try:
            chrome.wait(timeout=10)
        except Exception:
            chrome.kill()
        httpd.shutdown()


if __name__ == "__main__":
    main()
