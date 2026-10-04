"""Browser-owned recorded-action replay. No inference or training."""
import argparse
from datetime import datetime, timezone
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import threading

import numpy as np

from research.browser_bridge import BrowserBridge, QuietHandler, ROOT
from research.demonstrations import CRITICAL, game_contract_matches, require
from research.timing_campaign import contract, validate_run


def current_game_contract():
    """Verify actual game files without a detached shell's Git dependency."""
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assets = ROOT / "Getting Over It v1/assets"
    aggregate = hashlib.sha256()
    for path in sorted(assets.iterdir()):
        if path.is_file():
            aggregate.update(path.name.encode())
            aggregate.update(bytes.fromhex(digest(path)))
    return {"project_sha256": digest(assets / "project.json"),
            "runtime_sha256": digest(ROOT / "Getting Over It v1/script.js"),
            "asset_set_sha256": aggregate.hexdigest(),
            "source_sha256": {name: digest(ROOT / name) for name in CRITICAL}}


def playback_expression(record, commands, seed, label, minutes):
    expected = [[row["player_world_x"], row["player_world_y"]] for row in record["trace"]]
    parameters = json.dumps([commands, expected, seed, label, minutes])
    return f"""(()=>{{
        const [commands,expected,seed,label,minutes]={parameters};
        document.title='Getting Over It | Recorded learned ledge run';
        const banner=document.createElement('div');banner.id='replay-label';banner.textContent=label;
        banner.style.cssText='padding:12px;color:white;background:#173b36;font:16px sans-serif';
        document.body.prepend(banner);
        const end=performance.now()+minutes*60000;
        window.recordedReplay={{phase:'starting',loop:0,error:null}};
        let index=0;
        function restart(){{
            if(performance.now()>=end){{window.recordedReplay.phase='time_limit';return;}}
            research.reset(seed);index=0;window.recordedReplay.loop++;
            window.recordedReplay.phase='replaying';tick();
        }}
        function tick(){{
            if(performance.now()>=end){{window.recordedReplay.phase='time_limit';return;}}
            try{{
                const state=research.step([commands[index]])[0],target=expected[index];
                if(Math.abs(state.player_world_x-target[0])>1e-8 ||
                   Math.abs(state.player_world_y-target[1])>1e-8)
                    throw new Error('Recorded body-position mismatch at '+index);
                research.render();index++;window.recordedReplay.controlledTicks=index;
                if(index===commands.length){{
                    window.recordedReplay.phase='holding_final_pose';setTimeout(restart,15000);
                }}else setTimeout(tick,1000/30);
            }}catch(error){{
                window.recordedReplay.phase='error';window.recordedReplay.error=String(error);
                banner.textContent=label+' Replay stopped: '+String(error);
            }}
        }}
        restart();return window.recordedReplay;
    }})()"""


def launch(record, commands, seed, label, minutes):
    expression = playback_expression(record, commands, seed, label, minutes)
    if os.environ.get("FACTORY_DESKTOP_CDP_PORT") and os.environ.get("AGENT_BROWSER_CDP"):
        with BrowserBridge(driver="embedded") as bridge:
            proof = bridge.evaluate(expression)
        return proof, "Factory-owned persistent Browser pane, not a saved user profile"
    # Native fallback for a host without the Factory pane. No background Python
    # worker is needed after the browser loads all original costumes and assets.
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    options = Options()
    options.add_experimental_option("detach", True)
    options.add_argument("--mute-audio")
    options.add_argument("--disable-background-timer-throttling")
    env = {k: v for k, v in os.environ.items()
           if not any(x in k.upper() for x in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))}
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(env=env), options=options)
        driver.set_window_size(1100, 850)
        driver.get(f"http://127.0.0.1:{server.server_port}/Getting%20Over%20It%20v1/research.html")
        WebDriverWait(driver, 60).until(
            lambda d: d.execute_script("return window.researchReady || window.researchError"))
        proof = driver.execute_script("return " + expression)
        return proof, "Native detached Chrome; browser owns its bounded replay"
    finally:
        server.shutdown(); server.server_close()
        if driver:
            driver.service.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--case", default="nominal")
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--browser-owned", action="store_true", help="Compatibility flag; always browser-owned")
    args = parser.parse_args()
    require(all(path.is_absolute() for path in (args.trial, args.campaign, args.status))
            and 1 <= args.minutes <= 30, "Use absolute paths and a bounded viewer lifetime")
    manifest = json.loads((args.trial / "manifest.json").read_text(encoding="utf-8"))
    training = json.loads((args.trial / "training_summary.json").read_text(encoding="utf-8"))
    evaluation = json.loads((args.trial / "evaluation.json").read_text(encoding="utf-8"))
    campaign = json.loads(args.campaign.read_text(encoding="utf-8"))
    run = next(run for run in contract()["runs"] if run["name"] == args.trial.name)
    require(run["frame_skip"] == 1, "This viewer validates one-tick recorded trajectories")
    checked = validate_run(manifest, training, evaluation, run, campaign["provenance"])
    game_contract_matches(manifest, current_game_contract())
    record = next(r for r in evaluation["after"] if r["case"]["name"] == args.case)
    require(record["controlled_physics_ticks"] <= 1800, "Viewer trace exceeds its bounded horizon")
    seed = int(np.random.default_rng(record["seed"]).integers(0, 2**32))
    commands = [{"x": row["applied_action"][0] * 128, "y": row["applied_action"][1] * 128,
                 "id": index + 1} for index, row in enumerate(record["trace"])]
    label = (f"Recorded learned PPO: seed {run['seed']}, one-tick control, {args.case}. "
             "Original reference physics; NOT live training, local inference or full completion.")
    proof, lifetime = launch(record, commands, seed, label, args.minutes)
    require(proof["phase"] == "replaying" and proof["error"] is None, "Visible replay failed readiness")
    status = {"run": run["name"], "case": args.case, "purpose": label,
              "verified_result": checked["after"], "started_utc": datetime.now(timezone.utc).isoformat(),
              "maximum_minutes": args.minutes, "browser_proof": proof, "lifetime": lifetime}
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.status.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print("Visible browser replay ready:", args.status, flush=True)


if __name__ == "__main__":
    main()
