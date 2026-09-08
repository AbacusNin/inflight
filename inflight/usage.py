from inflight.model import EnvironmentModel, NetworkEdge, Thresholds, UsageRecord


def parse_flow_logs(records: list[dict]) -> list[UsageRecord]:
    agg: dict[tuple, dict] = {}
    for r in records:
        key = (r["srcaddr"], r["dstaddr"], r["protocol"], int(r["dstport"]))
        slot = agg.setdefault(key, {"count": 0, "first": r["start"], "last": r["end"]})
        slot["count"] += 1
        slot["first"] = min(slot["first"], r["start"])
        slot["last"] = max(slot["last"], r["end"])
    return [UsageRecord(src=k[0], dst=k[1], protocol=k[2], port=k[3],
                        flow_count=v["count"], first_seen=v["first"], last_seen=v["last"])
            for k, v in agg.items()]


def edge_usage(model: EnvironmentModel, edge: NetworkEdge) -> UsageRecord | None:
    for u in model.usage:
        if (u.src == edge.src and u.dst == edge.dst
                and u.protocol == edge.protocol and u.port == edge.port):
            return u
    return None


def is_used(model: EnvironmentModel, edge: NetworkEdge, thresholds: Thresholds) -> bool:
    u = edge_usage(model, edge)
    return u is not None and u.flow_count >= thresholds.min_flows_for_used
