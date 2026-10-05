"""Run established and goal tests, excluding only the canceled unfinished residual worker."""
import unittest


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    # This uncommitted module belongs to the user-interrupted residual-worker
    # task. Its mock file timestamp is invalid; do not edit/revive that work.
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
    kept, excluded = [], []
    for test in flatten(suite):
        name = test.id()
        if "test_residual_worker." in name or name.endswith(".test_residual_worker"):
            excluded.append(name)
        else:
            kept.append(test)
    print(f"Goal/established suite: {len(kept)} tests; {len(excluded)} inactive residual-worker tests excluded.")
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(kept))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
