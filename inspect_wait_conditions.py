import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

player_target = [t for t in proj["targets"] if t.get("name") == "Player"][0]
blocks = player_target["blocks"]

print("Block dY (control_wait_until):")
print(json.dumps(blocks.get("dY"), indent=2))
cond1_id = blocks.get("dY", {}).get("inputs", {}).get("CONDITION", [None, None])[1]
if cond1_id and isinstance(cond1_id, str):
    print("Condition for dY:", json.dumps(blocks.get(cond1_id), indent=2))

print("\nBlock l/ (control_wait_until):")
print(json.dumps(blocks.get("l/"), indent=2))
cond2_id = blocks.get("l/", {}).get("inputs", {}).get("CONDITION", [None, None])[1]
if cond2_id and isinstance(cond2_id, str):
    print("Condition for l/:", json.dumps(blocks.get(cond2_id), indent=2))
