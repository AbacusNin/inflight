# tests/test_model.py
from inflight.model import (
    Resource, SGRule, NetworkEdge, EnvironmentModel, Change,
    Classification, Finding, Verdict, VerdictResult, Thresholds,
)


def test_environment_model_holds_resources_and_rules():
    r = Resource(id="rds-app", type="rds", vpc_id="vpc-1")
    rule = SGRule(rule_id="r1", sg_id="sg-db", direction="ingress",
                  protocol="tcp", from_port=5432, to_port=5432, ref_sg_id="sg-app")
    env = EnvironmentModel(
        resources={r.id: r}, sg_rules={rule.rule_id: rule}, enis={},
        routes={}, nacls={}, usage=[], window_days=90.0, flow_logs_enabled=True,
    )
    assert env.resources["rds-app"].type == "rds"
    assert env.sg_rules["r1"].to_port == 5432


def test_thresholds_have_sane_defaults():
    t = Thresholds()
    assert t.window_days_high_confidence == 30.0
    assert t.min_flows_for_used == 1
