import json

with open("Getting Over It v1/assets/project.json", "r", encoding="utf-8") as f:
    proj = json.load(f)

player_target = [t for t in proj["targets"] if t.get("name") == "Player"][0]
blocks = player_target["blocks"]

curr = "lc"
path = []
while curr:
    b = blocks.get(curr)
    if not b or not isinstance(b, dict):
        break
    path.append((curr, b.get("opcode"), b.get("fields"), b.get("inputs")))
    curr = b.get("parent")

print("Parent chain for caller of Game Loop (lc):")
for bid, op, fields, inputs in reversed(path):
    print(f" -> Block {bid} ({op}): fields={fields}")
