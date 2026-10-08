"""Watch what the project does after the win flag (viewing only).

Replays a verified route to success, then keeps stepping past it with a neutral pointer and saves a
screenshot plus the visible-target list every `--every` ticks, so the ending sequence (win animation,
end title / world record, the game's own timer digits) can be inspected. Route, physics and rewards
are untouched; presentation mode only reproduces the title-screen sprite state (see research/runtime.js).

  python explore/probe_ending.py --ticks 1200 --every 150
  python explore/probe_ending.py --fastest-frames 3000      # normal "Win" end title instead of world record
"""
import argparse, base64, json
from pathlib import Path
from research.fast_bridge import FastBridge

SET_FASTEST_JS = ("(n) => { const st = window.vm.runtime.getTargetForStage();"
                  " const v = Object.values(st.variables).find(v => v.name === '\\u2601 FASTEST');"
                  " if (!v) throw new Error('missing FASTEST'); v.value = String(n); return v.value; }")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", default="explore/runs/e28_SUCCESS_s3100.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ticks", type=int, default=1200, help="ticks to keep stepping after success")
    ap.add_argument("--every", type=int, default=150)
    ap.add_argument("--first-every", type=int, default=30, help="screenshot spacing for the first --first-ticks ticks")
    ap.add_argument("--first-ticks", type=int, default=600, help="window where the ending fades in")
    ap.add_argument("--fastest-frames", type=int, default=None, help="emulate a populated cloud leaderboard")
    ap.add_argument("--pointer", type=float, nargs=2, default=[0.0, 0.0])
    ap.add_argument("--out", default="explore/runs/e28_ending_probe")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    route = json.load(open(a.route))
    cmds, cid = [], 1
    for ax, ay in route["actions"]:
        for _ in range(route["hold"]):
            cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
    rows = []
    with FastBridge(headless=True, presentation=True) as b:
        b.reset(a.seed)
        if a.fastest_frames is not None:
            b.evaluate(f"({SET_FASTEST_JS})({int(a.fastest_frames)})")
        last = None
        for i in range(0, len(cmds), 2400):
            tr = b.step_commands(cmds[i:i + 2400])
            if tr: last = tr[-1]
            if last and (last["dead"] or last["success"]): break
        print("SUCCESS" if last["success"] else "NO-SUCCESS", "tick", last["tick"],
              "x", last["player_world_x"], "y", last["player_world_y"], flush=True)

        def snap(tag):
            b.evaluate("window.research.render()")
            if getattr(b, "_cdp", None) is not None:
                data = b._cdp.call("Page.captureScreenshot", format="png")
                png = base64.b64decode(data["data"])
            else:                                     # Selenium driver (headless on Linux)
                png = b.driver.get_screenshot_as_png()
            (out / f"{tag}.png").write_bytes(png)

        def visible():
            return b.evaluate("window.vm.runtime.targets.filter(t=>t.visible).map(t=>t.getName())")

        def splash():
            return b.evaluate("(() => { const t = window.vm.runtime.targets.filter(t=>t.getName()==='Splash');"
                              " return t.map(t=>({clone: !t.isOriginal, costume: t.getCostumes()[t.currentCostume].name,"
                              " visible: t.visible, ghost: t.effects.ghost, x: t.x, y: t.y})); })()")

        snap(f"t{last['tick']:05d}_success")
        print("visible at success:", visible(), flush=True)
        k, step = 0, a.first_every
        while k < a.ticks:
            tr = b.step_commands([{"x": a.pointer[0], "y": a.pointer[1], "id": cid + k + j} for j in range(step)], after=True)
            if not tr: break
            s = tr[-1]; k += step
            if k >= a.first_ticks: step = a.every
            snap(f"t{s['tick']:05d}")
            row = {"tick": s["tick"], "x": s["player_world_x"], "y": s["player_world_y"],
                   "camera": [s["camera_x"], s["camera_y"]], "frame": s["frame_id"],
                   "dead": s["dead"], "success": s["success"], "visible": visible(), "splash": splash()}
            rows.append(row); print(json.dumps({k: v for k, v in row.items() if k != "visible"}), flush=True)
            if s["dead"]: break
    (out / "probe.json").write_text(json.dumps(rows, indent=1))
    print("saved", out)


if __name__ == "__main__":
    main()
