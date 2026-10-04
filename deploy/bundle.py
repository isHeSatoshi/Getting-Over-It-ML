"""Create an allowlisted deployment tree. Never copy profiles, logs, or credentials."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from research.browser_bridge import ROOT
from research.provenance import fingerprint


def build_bundle(output=None):
    output = Path(output) if output else ROOT / "artifacts" / (
        "hf_bundle_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    if not output.is_absolute():
        raise ValueError("Bundle path must be absolute")
    output.mkdir(parents=True, exist_ok=False)
    files = [ROOT / "StaticCollisionMap.py", ROOT / "requirements-research.txt",
             ROOT / "Getting Over It v1/script.js", ROOT / "Getting Over It v1/research.html",
             ROOT / "tools/research_goal_metrics.py", ROOT / "tools/hf_research_status.py",
             ROOT / "tools/imitation_noise_probe.py", ROOT / "tools/matched_host_inference.py"]
    files.extend(ROOT / "deploy" / name for name in ("Dockerfile", "requirements-space.txt", "README-space.md"))
    for folder, suffixes in (("research", (".py", ".js")), ("tests", (".py", ".js")),
                             ("deploy", (".py",)), ("docs", (".md",))):
        files.extend(p for p in (ROOT / folder).iterdir() if p.is_file() and p.suffix in suffixes)
    files.extend(p for p in (ROOT / "Getting Over It v1/assets").iterdir()
                 if p.is_file() and p.suffix in (".json", ".png", ".svg", ".wav", ".mp3"))
    for source in files:
        target = output / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for original, target in (("Dockerfile", "Dockerfile"), ("requirements-space.txt", "requirements-space.txt"),
                             ("README-space.md", "README.md")):
        shutil.copyfile(ROOT / "deploy" / original, output / target)
    (output / "deployment_provenance.json").write_text(json.dumps(fingerprint(), indent=2), encoding="utf-8")
    manifest = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    print(build_bundle())
