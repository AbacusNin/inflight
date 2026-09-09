import argparse
import json
import sys

from inflight.model import Change, Verdict
from inflight.snapshot import load_from_file
from inflight.engine import evaluate

_EXIT = {Verdict.SAFE: 0, Verdict.NEEDS_REVIEW: 2, Verdict.BLOCK: 3}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        raise SystemExit(1)


def _load_change(path: str) -> Change:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Change(kind=raw["kind"], rule_ids=tuple(raw["rule_ids"]),
                  params=raw.get("params", {}))


def _default_session(region):
    import boto3
    return boto3.Session(region_name=region) if region else boto3.Session()


def main(argv: list[str] | None = None, session=None) -> int:
    parser = _Parser(prog="inflight")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--snapshot")
    ev.add_argument("--change", required=True)
    ev.add_argument("--flow-logs")
    ev.add_argument("--aws-vpc")
    ev.add_argument("--window-days", type=float, default=90.0)
    ev.add_argument("--region")
    ev.add_argument("--ledger")
    args = parser.parse_args(argv)

    try:
        change = _load_change(args.change)
        if args.aws_vpc:
            from inflight.snapshot_aws import load_from_aws
            from inflight.flowlogs import load_usage_from_aws
            sess = session or _default_session(args.region)
            env = load_from_aws(sess, args.aws_vpc, args.window_days)
            env = load_usage_from_aws(sess, env, args.window_days)
        else:
            if not args.snapshot:
                parser.error("evaluate needs --snapshot or --aws-vpc")
            env = load_from_file(args.snapshot)
            if args.flow_logs:
                from inflight.flowlogs import load_usage_from_file
                env = load_usage_from_file(env, args.flow_logs)
        result = evaluate(env, change)
    except (OSError, KeyError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3  # fail closed
    report = {"verdict": result.verdict.value, "reasons": list(result.reasons)}
    if args.ledger:
        from datetime import datetime, timezone
        from inflight.ledger import Ledger
        Ledger(args.ledger).append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "snapshot": args.snapshot or f"aws-vpc:{args.aws_vpc}",
            "change": args.change,
            "verdict": result.verdict.value,
            "reasons": list(result.reasons),
        })
    print(json.dumps(report, indent=2))
    return _EXIT[result.verdict]
