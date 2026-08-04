import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

for t in proj["targets"]:
    for vid, vinfo in t.get("variables", {}).items():
        if vinfo[0] == "SFX":
            print(f"Target '{t['name']}': SFX = repr({repr(vinfo[1])})")
