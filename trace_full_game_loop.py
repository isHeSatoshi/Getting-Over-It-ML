import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

player_target = [t for t in proj["targets"] if t.get("name") == "Player"][0]
blocks = player_target["blocks"]

def print_chain(start_id, indent=0):
    curr = start_id
    prefix = "  " * indent
    while curr:
        b = blocks.get(curr)
        if not b or not isinstance(b, dict):
            print(f"{prefix}End ({curr})")
            break
        op = b.get("opcode")
        inputs = b.get("inputs", {})
        fields = b.get("fields", {})
        print(f"{prefix}[{curr}] {op}")
        if op == "control_if_else" or op == "control_if":
            sub = inputs.get("SUBSTACK", [None, None])[1]
            if sub:
                print(f"{prefix}  -- SUBSTACK --")
                print_chain(sub, indent + 2)
            sub2 = inputs.get("SUBSTACK2", [None, None])[1]
            if sub2:
                print(f"{prefix}  -- SUBSTACK2 --")
                print_chain(sub2, indent + 2)
        elif op == "control_repeat_until" or op == "control_repeat":
            sub = inputs.get("SUBSTACK", [None, None])[1]
            if sub:
                print(f"{prefix}  -- REPEAT SUBSTACK --")
                print_chain(sub, indent + 2)
        curr = b.get("next")

print("=== Full Game Loop Block Tree ===")
print_chain("lE")
