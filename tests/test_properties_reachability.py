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


def _two_rule_model(order):
    # same two rules every time (5432 and 443, both sg-db ingress via sg-app);
    # `order` controls the insertion order into sg_rules
    rules_by_id = {
        "r-5432": SGRule("r-5432", "sg-db", "ingress", "tcp", 5432, 5432, ref_sg_id="sg-app"),
        "r-443": SGRule("r-443", "sg-db", "ingress", "tcp", 443, 443, ref_sg_id="sg-app"),
    }
    sg_rules = {rule_id: rules_by_id[rule_id] for rule_id in order}
    return EnvironmentModel(
        resources={"i-app": Resource("i-app", "instance", "vpc-1", {"sg_ids": ["sg-app"]}),
                   "i-db": Resource("i-db", "instance", "vpc-1", {"sg_ids": ["sg-db"]})},
        sg_rules=sg_rules, enis={}, routes={}, nacls={}, usage=[],
        window_days=90.0, flow_logs_enabled=True)


def test_reachability_is_order_independent():
    # same rules, reversed insertion order into sg_rules; the answer must not depend on it
    forward = _two_rule_model(["r-5432", "r-443"])
    reverse = _two_rule_model(["r-443", "r-5432"])
    forward_result = reachable(forward, "i-app", "i-db", "tcp", 5432)
    reverse_result = reachable(reverse, "i-app", "i-db", "tcp", 5432)
    assert forward_result == reverse_result
    assert forward_result


def test_renaming_resources_does_not_change_reachability():
    m = _two_tier()
    base = reachable(m, "i-app", "i-db", "tcp", 5432)
    # keep the dict key "i-app" fixed and change only Resource.id; the engine must
    # key on Resource.id, not on the dict key, for reachability to still hold
    m.resources["i-app"] = Resource("i-app2", "instance", "vpc-1", {"sg_ids": ["sg-app"]})
    assert reachable(m, "i-app2", "i-db", "tcp", 5432) == base
