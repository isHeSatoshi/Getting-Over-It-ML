"""Print linked Scratch scripts with original block IDs for physics audits."""
import argparse
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1] / "Getting Over It v1/assets/project.json"


def scripts(project, names):
    for target in project["targets"]:
        if target["name"] not in names:
            continue
        blocks = target["blocks"]

        def expression(value):
            if isinstance(value, str) and value in blocks:
                b = blocks[value]
                fields = ",".join(str(v[0]) for v in b.get("fields", {}).values())
                args = ",".join(expression(v[1]) for v in b.get("inputs", {}).values())
                return f"{b['opcode']}({fields}{';' if fields and args else ''}{args})"
            if isinstance(value, list):
                return str(value[1]) if len(value) > 1 else str(value)
            return str(value)

        def chain(block_id, indent=0):
            while block_id:
                b = blocks[block_id]
                fields = ",".join(str(v[0]) for v in b.get("fields", {}).values())
                args = {k: expression(v[1]) for k, v in b.get("inputs", {}).items()
                        if not k.startswith("SUBSTACK") and k != "custom_block"}
                mutation = b.get("mutation", {}).get("proccode", "")
                if b["opcode"] == "procedures_definition":
                    mutation = blocks[b["inputs"]["custom_block"][1]]["mutation"]["proccode"]
                yield "  " * indent + f"[{block_id}] {b['opcode']} {fields} {mutation} {args}"
                for k, v in b.get("inputs", {}).items():
                    if k.startswith("SUBSTACK"):
                        yield from chain(v[1], indent + 1)
                block_id = b.get("next")

        yield f"\n# {target['name']}"
        for block_id, block in blocks.items():
            if block.get("topLevel"):
                yield from chain(block_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="*", default=["Player", "Level", "Hammer"])
    args = parser.parse_args()
    print("\n".join(scripts(json.loads(PROJECT.read_text(encoding="utf-8")), args.targets)))
