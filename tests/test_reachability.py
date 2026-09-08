# tests/test_reachability.py
from inflight.snapshot import load_from_file
from inflight.reachability import permitted_edges, reachable


def test_permitted_edge_from_sg_reference():
    env = load_from_file("tests/fixtures/minimal.json")
    edges = permitted_edges(env)
    assert any(e.src == "i-app" and e.dst == "rds-app" and e.port == 5432
               for e in edges)


def test_reachable_true_then_false_after_rule_gone():
    env = load_from_file("tests/fixtures/minimal.json")
    assert reachable(env, "i-app", "rds-app", "tcp", 5432) is True
    env.sg_rules.clear()
    assert reachable(env, "i-app", "rds-app", "tcp", 5432) is False


def test_ranged_rule_produces_no_edge():
    env = load_from_file("tests/fixtures/ranged_rule.json")
    assert permitted_edges(env) == []
