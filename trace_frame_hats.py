import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

player_target = [t for t in proj["targets"] if t.get("name") == "Player"][0]
blocks = player_target["blocks"]

def trace_top(block_id):
    curr = block_id
    path = []
    while curr:
        b = blocks.get(curr)
        if not b or not isinstance(b, dict):
            break
        path.append((curr, b.get("opcode")))
        curr = b.get("parent")
    return path

print("Tracing block l) (change FRAME by 1):")
path = trace_top("l)")
for bid, op in reversed(path):
    print(f" -> {bid}: {op}")
