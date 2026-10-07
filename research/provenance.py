"""Fingerprints of game data and the actual (possibly uncommitted) harness."""
import hashlib
import platform
import subprocess
import json

from research.browser_bridge import ROOT


def fingerprint():
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    source = list((ROOT / "research").glob("*.py")) + list((ROOT / "research").glob("*.js"))
    source.append(ROOT / "Getting Over It v1/research.html")
    source.append(ROOT / "StaticCollisionMap.py")
    assets = ROOT / "Getting Over It v1/assets"
    aggregate = hashlib.sha256()
    for path in sorted(assets.iterdir()):
        if path.is_file():
            aggregate.update(path.name.encode())
            aggregate.update(bytes.fromhex(digest(path)))
    git_result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                text=True, capture_output=True, check=False)
    if git_result.returncode == 0:
        revision = git_result.stdout.strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True).strip())
        provenance_kind = "git_worktree"
    else:
        snapshot = ROOT / "deployment_provenance.json"
        if not snapshot.exists():
            raise RuntimeError("No Git or explicit deployment provenance available")
        recorded = json.loads(snapshot.read_text(encoding="utf-8"))
        revision, dirty = recorded["git_revision"], recorded["git_dirty"]
        provenance_kind = "deployment_snapshot"
    return {
        "platform": platform.platform(),
        "project_sha256": digest(assets / "project.json"),
        "runtime_sha256": digest(ROOT / "Getting Over It v1/script.js"),
        "asset_set_sha256": aggregate.hexdigest(),
        "source_sha256": {path.relative_to(ROOT).as_posix(): digest(path) for path in sorted(source)},
        "git_revision": revision, "git_dirty": dirty, "provenance_kind": provenance_kind,
    }
