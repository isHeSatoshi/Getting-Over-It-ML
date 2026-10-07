"""Explicit execution-backend selection. No fallback to the obsolete Node VM."""
import os
from research.browser_bridge import BrowserBridge


def make_bridge(backend="reference", driver="auto"):
    if backend == "fast":
        from research.fast_bridge import FastBridge
        return FastBridge()
    if backend != "reference":
        raise ValueError("Unknown execution backend")
    return BrowserBridge(driver=driver, headless=not bool(os.environ.get("FACTORY_DESKTOP_CDP_PORT")))
