import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

player_target = [t for t in proj["targets"] if t.get("name") == "Player"][0]
blocks = player_target["blocks"]

proc_def = blocks["lE"]
proto_id = proc_def["inputs"]["custom_block"][1]
proto = blocks[proto_id]
print("Procedure prototype mutation:", proto.get("mutation"))
