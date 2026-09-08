from inflight.model import Change, Verdict, UsageRecord
from inflight.snapshot import load_from_file
from inflight.engine import evaluate


def test_unused_full_window_is_safe():
    env = load_from_file("tests/fixtures/minimal.json")
    env.window_days = 90.0
    out = evaluate(env, Change(kind="remove_sg_rules", rule_ids=("r1",)))
    assert out.verdict is Verdict.SAFE


def test_used_sole_path_never_safe():
    env = load_from_file("tests/fixtures/minimal.json")
    env.usage.append(UsageRecord("i-app", "rds-app", "tcp", 5432, 10, "s", "e"))
    out = evaluate(env, Change(kind="remove_sg_rules", rule_ids=("r1",)))
    assert out.verdict is not Verdict.SAFE
