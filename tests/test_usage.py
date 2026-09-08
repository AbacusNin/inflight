from inflight.model import NetworkEdge, Thresholds, EnvironmentModel, UsageRecord
from inflight.usage import parse_flow_logs, edge_usage, is_used


def _env(usage):
    return EnvironmentModel(resources={}, sg_rules={}, enis={}, routes={},
                            nacls={}, usage=usage, window_days=90.0,
                            flow_logs_enabled=True)


def test_parse_flow_logs_aggregates_by_edge():
    recs = [
        {"srcaddr": "i-app", "dstaddr": "rds-app", "protocol": "tcp",
         "dstport": 5432, "start": "2026-08-01T00:00:00Z", "end": "2026-08-01T00:01:00Z"},
        {"srcaddr": "i-app", "dstaddr": "rds-app", "protocol": "tcp",
         "dstport": 5432, "start": "2026-08-02T00:00:00Z", "end": "2026-08-02T00:01:00Z"},
    ]
    out = parse_flow_logs(recs)
    assert len(out) == 1
    assert out[0].flow_count == 2


def test_is_used_reflects_min_flows():
    edge = NetworkEdge(src="i-app", dst="rds-app", protocol="tcp", port=5432, via_rule_id="r1")
    used_env = _env([UsageRecord("i-app", "rds-app", "tcp", 5432, 3, "s", "e")])
    empty_env = _env([])
    assert is_used(used_env, edge, Thresholds()) is True
    assert is_used(empty_env, edge, Thresholds()) is False
