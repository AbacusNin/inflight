import argparse
import json
import sys

from inflight.model import Change, Verdict
from inflight.snapshot import load_from_file
from inflight.engine import evaluate

_EXIT = {Verdict.SAFE: 0, Verdict.NEEDS_REVIEW: 2, Verdict.BLOCK: 3}


def _load_change(path: str) -> Change:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Change(kind=raw["kind"], rule_ids=tuple(raw["rule_ids"]),
                  params=raw.get("params", {}))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inflight")
    sub = parser.add_subparsers(dest="command", required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--snapshot", required=True)
    ev.add_argument("--change", required=True)
    args = parser.parse_args(argv)

    try:
        env = load_from_file(args.snapshot)
        change = _load_change(args.change)
        result = evaluate(env, change)
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3  # fail closed
    report = {"verdict": result.verdict.value, "reasons": list(result.reasons)}
    print(json.dumps(report, indent=2))
    return _EXIT[result.verdict]
