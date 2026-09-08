import json

from inflight.model import EnvironmentModel, Resource, SGRule, UsageRecord


def load_from_file(path: str) -> EnvironmentModel:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    resources = {r["id"]: Resource(**r) for r in raw["resources"]}
    sg_rules = {r["rule_id"]: SGRule(**r) for r in raw["sg_rules"]}
    usage = [UsageRecord(**u) for u in raw.get("usage", [])]
    return EnvironmentModel(
        resources=resources,
        sg_rules=sg_rules,
        enis=raw.get("enis", {}),
        routes=raw.get("routes", {}),
        nacls=raw.get("nacls", {}),
        usage=usage,
        window_days=raw["window_days"],
        flow_logs_enabled=raw["flow_logs_enabled"],
        ip_to_resource=raw.get("ip_to_resource", {}),
    )
