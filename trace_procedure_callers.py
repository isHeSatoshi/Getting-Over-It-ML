import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

player_target = [t for t in proj["targets"] if t.get("name") == "Player"][0]
blocks = player_target["blocks"]

proc_def = blocks["lE"]
customcode = proc_def.get("inputs", {}).get("custom_block", [None, None])[1]
print("Procedure lE customcode:", customcode)

# Find procedure prototype
proto_id = blocks["lE"].get("inputs", {}).get("custom_block", [])[1]
proto_block = blocks.get(proto_id, {})
proccode = proto_block.get("mutation", {}).get("proccode")
print("Proccode:", proccode)

print("\nCallers of this procedure:")
for bid, b in blocks.items():
    if isinstance(b, dict) and b.get("opcode") == "procedures_call":
        if b.get("mutation", {}).get("proccode") == proccode:
            print(f" -> Call block {bid}: parent={b.get('parent')}")
