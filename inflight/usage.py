import ipaddress

from inflight.model import EnvironmentModel, NetworkEdge, Thresholds, UsageRecord

_PROTO_NUMBERS = {"6": "tcp", "17": "udp", "1": "icmp"}


def _norm_proto(protocol) -> str:
    """Normalize a VPC Flow Log protocol (numeric string like '6') to a name.
    Already-named protocols pass through unchanged."""
    return _PROTO_NUMBERS.get(str(protocol), str(protocol))


def resolve_flow_logs(model: EnvironmentModel, records: list[dict]) -> list[UsageRecord]:
    """Turn raw VPC Flow Log records (IP addresses, numeric protocol) into usage
    records keyed to match edges. The destination IP is resolved to a known
    resource id via model.ip_to_resource (flows to an unmodeled destination are
    dropped). The source IP is resolved to a resource id when known, otherwise the
    raw IP is kept so CIDR-sourced edges can match it by membership. The
    destination port is the edge port; the protocol is normalized to a name."""
    agg: dict[tuple, dict] = {}
    for r in records:
        dst = model.ip_to_resource.get(r["dstaddr"])
        if dst is None:
            continue
        src = model.ip_to_resource.get(r["srcaddr"], r["srcaddr"])
        key = (src, dst, _norm_proto(r["protocol"]), int(r["dstport"]))
        slot = agg.setdefault(key, {"count": 0, "first": r["start"], "last": r["end"]})
        slot["count"] += 1
        slot["first"] = min(slot["first"], r["start"])
        slot["last"] = max(slot["last"], r["end"])
    return [UsageRecord(src=k[0], dst=k[1], protocol=k[2], port=k[3],
                        flow_count=v["count"], first_seen=v["first"], last_seen=v["last"])
            for k, v in agg.items()]


def _src_matches(edge_src: str, usage_src: str) -> bool:
    """A resource-sourced edge matches its exact resource id; a CIDR-sourced edge
    matches any usage whose source IP falls within the CIDR."""
    if "/" in edge_src:
        try:
            return ipaddress.ip_address(usage_src) in ipaddress.ip_network(edge_src, strict=False)
        except ValueError:
            return False
    return usage_src == edge_src


def edge_flow_count(model: EnvironmentModel, edge: NetworkEdge) -> int:
    total = 0
    for u in model.usage:
        if (u.dst == edge.dst and u.protocol == edge.protocol and u.port == edge.port
                and _src_matches(edge.src, u.src)):
            total += u.flow_count
    return total


def is_used(model: EnvironmentModel, edge: NetworkEdge, thresholds: Thresholds) -> bool:
    return edge_flow_count(model, edge) >= thresholds.min_flows_for_used
