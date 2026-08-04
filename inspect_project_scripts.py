import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

print("Targets in project:", len(proj["targets"]))
for t in proj["targets"]:
    name = t.get("name")
    for var_id, var_info in t.get("variables", {}).items():
        var_name = var_info[0]
        if "FRAME" in var_name or "PLAYER Y" in var_name:
            print(f"Target '{name}': Variable {var_name} (id={var_id}) = {var_info[1]}")

print("\nSearching blocks for FRAME variable mutations:")
for t in proj["targets"]:
    name = t.get("name")
    for block_id, block in t.get("blocks", {}).items():
        if isinstance(block, dict) and block.get("opcode") == "data_changevariableby":
            field_var = block.get("fields", {}).get("VARIABLE")
            if field_var and "FRAME" in field_var[0]:
                print(f"Target '{name}' block {block_id}: change {field_var[0]} by {block.get('inputs')}")
        if isinstance(block, dict) and block.get("opcode") == "data_setvariableto":
            field_var = block.get("fields", {}).get("VARIABLE")
            if field_var and "FRAME" in field_var[0]:
                print(f"Target '{name}' block {block_id}: set {field_var[0]}")
