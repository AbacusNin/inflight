# tests/test_properties_reachability.py
from inflight.model import EnvironmentModel, Resource, SGRule
from inflight.reachability import reachable


def _two_tier(port=5432, redundant=False):
    rules = {"r1": SGRule("r1", "sg-db", "ingress", "tcp", port, port, ref_sg_id="sg-app")}
    if redundant:
        rules["r2"] = SGRule("r2", "sg-db", "ingress", "tcp", port, port, ref_sg_id="sg-app")
    return EnvironmentModel(
        resources={"i-app": Resource("i-app", "instance", "vpc-1", {"sg_ids": ["sg-app"]}),
                   "i-db": Resource("i-db", "instance", "vpc-1", {"sg_ids": ["sg-db"]})},
        sg_rules=rules, enis={}, routes={}, nacls={}, usage=[],
        window_days=90.0, flow_logs_enabled=True)


def test_removing_sole_rule_severs_reachability():
    m = _two_tier()
    assert reachable(m, "i-app", "i-db", "tcp", 5432)
    m.sg_rules.clear()
    assert not reachable(m, "i-app", "i-db", "tcp", 5432)


def test_redundant_rule_keeps_reachability_after_one_removed():
    m = _two_tier(redundant=True)
    m.sg_rules.pop("r1")
    assert reachable(m, "i-app", "i-db", "tcp", 5432)


def test_reachability_is_deterministic():
    m = _two_tier()
    assert reachable(m, "i-app", "i-db", "tcp", 5432) == reachable(m, "i-app", "i-db", "tcp", 5432)


def test_renaming_resources_does_not_change_reachability():
    m = _two_tier()
    base = reachable(m, "i-app", "i-db", "tcp", 5432)
    # relabel the app instance; the SG wiring is identical, so reachability must hold
    m.resources.pop("i-app")
    m.resources["i-app2"] = Resource("i-app2", "instance", "vpc-1", {"sg_ids": ["sg-app"]})
    assert reachable(m, "i-app2", "i-db", "tcp", 5432) == base
