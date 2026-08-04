import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

player_target = [t for t in proj["targets"] if t.get("name") == "Player"][0]
blocks = player_target["blocks"]

print("Block lG (SUBSTACK):")
print(json.dumps(blocks.get("lG"), indent=2))

print("\nBlock yX (SUBSTACK2):")
print(json.dumps(blocks.get("yX"), indent=2))
