import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

player_target = [t for t in proj["targets"] if t.get("name") == "Player"][0]
blocks = player_target["blocks"]

print("Block yZ:", json.dumps(blocks.get("yZ"), indent=2))
print("Block y!:", json.dumps(blocks.get("y!"), indent=2))
