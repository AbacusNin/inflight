from inflight.model import Change, EnvironmentModel, Verdict
from inflight.snapshot import load_from_file
from inflight.engine import evaluate


def test_missing_usage_never_returns_safe():
    env = load_from_file("tests/fixtures/minimal.json")
    env.flow_logs_enabled = False
    env.usage = []
    out = evaluate(env, Change(kind="remove_sg_rules", rule_ids=("r1",)))
    assert out.verdict is not Verdict.SAFE


def test_unknown_rule_id_never_safe():
    env = load_from_file("tests/fixtures/minimal.json")
    out = evaluate(env, Change(kind="remove_sg_rules", rule_ids=("does-not-exist",)))
    assert out.verdict is not Verdict.SAFE


def test_egress_rule_removal_never_safe():
    env = load_from_file("tests/fixtures/egress_only.json")
    out = evaluate(env, Change(kind="remove_sg_rules", rule_ids=("e1",)))
    assert out.verdict is not Verdict.SAFE


def test_ranged_rule_change_never_safe():
    env = load_from_file("tests/fixtures/ranged_rule.json")
    out = evaluate(env, Change(kind="remove_sg_rules", rule_ids=("r1",)))
    assert out.verdict is not Verdict.SAFE
