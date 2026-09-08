from inflight.model import Change, Verdict
from inflight.snapshot import load_from_file
from inflight.engine import evaluate


def handler(event: dict, context) -> dict:
    try:
        env = load_from_file(event["snapshot"])
        raw = event["change"]
        change = Change(kind=raw["kind"], rule_ids=tuple(raw["rule_ids"]),
                        params=raw.get("params", {}))
        result = evaluate(env, change)
    except Exception as exc:  # fail closed: any failure blocks
        return {"verdict": "block", "reasons": [f"error: {exc}"], "allow": False}
    return {"verdict": result.verdict.value,
            "reasons": list(result.reasons),
            "allow": result.verdict is Verdict.SAFE}
