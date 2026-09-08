from inflight.model import NetworkEdge, Thresholds, EnvironmentModel, UsageRecord
from inflight.usage import resolve_flow_logs, is_used


def _env(usage, ip_to_resource=None):
    return EnvironmentModel(resources={}, sg_rules={}, enis={}, routes={},
                            nacls={}, usage=usage, window_days=90.0,
                            flow_logs_enabled=True,
                            ip_to_resource=ip_to_resource or {})


def test_resolve_flow_logs_normalizes_and_resolves():
    env = _env([], ip_to_resource={"10.0.1.5": "i-app", "10.0.2.9": "rds-app"})
    raw = [{"srcaddr": "10.0.1.5", "dstaddr": "10.0.2.9", "protocol": "6",
            "dstport": 5432, "start": "2026-08-01T00:00:00Z", "end": "2026-08-01T00:01:00Z"}]
    out = resolve_flow_logs(env, raw)
    assert len(out) == 1
    u = out[0]
    assert (u.src, u.dst, u.protocol, u.port) == ("i-app", "rds-app", "tcp", 5432)


def test_resolve_drops_flows_to_unknown_destination():
    env = _env([], ip_to_resource={"10.0.1.5": "i-app"})
    raw = [{"srcaddr": "10.0.1.5", "dstaddr": "10.9.9.9", "protocol": "6",
            "dstport": 5432, "start": "s", "end": "e"}]
    assert resolve_flow_logs(env, raw) == []


def test_is_used_reflects_min_flows():
    edge = NetworkEdge(src="i-app", dst="rds-app", protocol="tcp", port=5432, via_rule_id="r1")
    used_env = _env([UsageRecord("i-app", "rds-app", "tcp", 5432, 3, "s", "e")])
    empty_env = _env([])
    assert is_used(used_env, edge, Thresholds()) is True
    assert is_used(empty_env, edge, Thresholds()) is False


def test_is_used_matches_cidr_edge_by_membership():
    edge = NetworkEdge(src="0.0.0.0/0", dst="i-web", protocol="tcp", port=22, via_rule_id="r1")
    env = _env([UsageRecord("203.0.113.5", "i-web", "tcp", 22, 5, "s", "e")])
    assert is_used(env, edge, Thresholds()) is True
    edge2 = NetworkEdge(src="10.0.0.0/8", dst="i-web", protocol="tcp", port=22, via_rule_id="r2")
    assert is_used(env, edge2, Thresholds()) is False
