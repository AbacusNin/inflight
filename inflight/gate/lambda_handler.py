import os
import sys
from datetime import datetime, timezone

from inflight.model import Change, Verdict
from inflight.snapshot import load_from_file
from inflight.engine import evaluate
from inflight.ledger import Ledger
from inflight.flowlogs import load_usage_from_aws


def _resolve_within(base: str, candidate: str) -> str:
    """Resolve candidate under base and refuse anything that escapes base."""
    real_base = os.path.realpath(base)
    real_cand = os.path.realpath(os.path.join(real_base, candidate))
    if real_cand != real_base and not real_cand.startswith(real_base + os.sep):
        raise ValueError("snapshot path escapes the allowed base directory")
    return real_cand


def _record(event: dict, payload: dict) -> None:
    path = event.get("ledger") or os.environ.get("INFLIGHT_LEDGER")
    if path:
        Ledger(path).append({"timestamp": datetime.now(timezone.utc).isoformat(), **payload})


def _session(region):
    import boto3
    return boto3.Session(region_name=region) if region else boto3.Session()


def handler(event: dict, context, session=None) -> dict:
    base = os.environ.get("INFLIGHT_BASE_DIR", os.getcwd())
    try:
        snapshot = _resolve_within(base, event["snapshot"])
        env = load_from_file(snapshot)
        if event.get("window_days"):
            sess = session or _session(event.get("region"))
            env = load_usage_from_aws(sess, env, float(event["window_days"]))
        raw = event["change"]
        change = Change(kind=raw["kind"], rule_ids=tuple(raw["rule_ids"]),
                        params=raw.get("params", {}))
        result = evaluate(env, change)
    except Exception as exc:  # fail closed: any failure blocks
        print(f"inflight error: {exc}", file=sys.stderr)  # detail to logs, not to the payload
        out = {"verdict": "block", "reasons": ["blocked: evaluation error"], "allow": False}
        _record(event, out)
        return out
    out = {"verdict": result.verdict.value,
           "reasons": list(result.reasons),
           "allow": result.verdict is Verdict.SAFE,
           "window_days": env.window_days,
           "flow_logs_enabled": env.flow_logs_enabled,
           "usage_complete": env.usage_complete}
    _record(event, out)
    return out
