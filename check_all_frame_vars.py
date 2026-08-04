import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

for t in proj["targets"]:
    name = t.get("name")
    for vid, vinfo in t.get("variables", {}).items():
        if "FRAME" in vinfo[0].upper():
            print(f"Target '{name}': variable '{vinfo[0]}' (id={vid}, val={vinfo[1]})")
