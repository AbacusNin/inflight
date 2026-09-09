from inflight.model import (
    EnvironmentModel, Resource, SGRule, Change, Verdict,
)
from inflight.engine import evaluate


def _two_tier(*, flow_logs=True, window=90.0, usage_complete=True, usage=None):
    rules = {"r1": SGRule("r1", "sg-db", "ingress", "tcp", 5432, 5432, ref_sg_id="sg-app")}
    return EnvironmentModel(
        resources={"i-app": Resource("i-app", "instance", "vpc-1", {"sg_ids": ["sg-app"]}),
                   "i-db": Resource("i-db", "instance", "vpc-1", {"sg_ids": ["sg-db"]})},
        sg_rules=rules, enis={}, routes={}, nacls={}, usage=usage or [],
        window_days=window, flow_logs_enabled=flow_logs, usage_complete=usage_complete)


def test_complete_map_no_usage_over_full_window_is_safe():
    m = _two_tier()  # flow logs on, 90-day window, map complete, no usage
    r = evaluate(m, Change("remove_sg_rules", ("r1",)))
    assert r.verdict is Verdict.SAFE


def test_incomplete_map_degrades_to_needs_review():
    m = _two_tier(usage_complete=False)
    r = evaluate(m, Change("remove_sg_rules", ("r1",)))
    assert r.verdict is Verdict.NEEDS_REVIEW
    assert any("map is incomplete" in reason for reason in r.reasons)


def test_used_sole_path_blocks_even_with_incomplete_map():
    from inflight.model import UsageRecord
    used = [UsageRecord("i-app", "i-db", "tcp", 5432, 3, "t0", "t1")]
    m = _two_tier(usage_complete=False, usage=used)
    r = evaluate(m, Change("remove_sg_rules", ("r1",)))
    assert r.verdict is Verdict.BLOCK
