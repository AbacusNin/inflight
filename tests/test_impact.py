from inflight.model import Change, Thresholds, Classification, UsageRecord
from inflight.snapshot import load_from_file
from inflight.impact import affected_edges, analyze


def test_affected_edges_are_those_via_changed_rule():
    env = load_from_file("tests/fixtures/minimal.json")
    edges = affected_edges(env, Change(kind="remove_sg_rules", rule_ids=("r1",)))
    assert len(edges) == 1 and edges[0].via_rule_id == "r1"


def test_used_sole_path_is_live_sole_high_confidence():
    env = load_from_file("tests/fixtures/minimal.json")
    env.usage.append(UsageRecord("i-app", "rds-app", "tcp", 5432, 500, "s", "e"))
    findings = analyze(env, Change(kind="remove_sg_rules", rule_ids=("r1",)), Thresholds())
    assert findings[0].classification is Classification.LIVE_SOLE
    assert findings[0].confidence == "high"


def test_unused_with_short_window_is_dead_uncertain():
    env = load_from_file("tests/fixtures/minimal.json")
    env.window_days = 3.0
    findings = analyze(env, Change(kind="remove_sg_rules", rule_ids=("r1",)), Thresholds())
    assert findings[0].classification is Classification.DEAD_UNCERTAIN
    assert findings[0].confidence == "low"
