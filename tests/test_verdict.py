from inflight.model import Finding, NetworkEdge, Classification, Verdict
from inflight.verdict import decide


def _f(cls, conf="high"):
    e = NetworkEdge("a", "b", "tcp", 5432, "r1")
    return Finding(edge=e, classification=cls, confidence=conf, evidence={})


def test_live_sole_blocks():
    assert decide([_f(Classification.LIVE_SOLE)]).verdict is Verdict.BLOCK


def test_dead_uncertain_needs_review():
    assert decide([_f(Classification.DEAD_UNCERTAIN, "low")]).verdict is Verdict.NEEDS_REVIEW


def test_all_safe_classes_are_safe():
    out = decide([_f(Classification.DEAD), _f(Classification.LIVE_REDUNDANT)])
    assert out.verdict is Verdict.SAFE


def test_empty_findings_is_safe():
    assert decide([]).verdict is Verdict.SAFE


def test_block_wins_over_needs_review_either_order():
    sole = _f(Classification.LIVE_SOLE)
    uncertain = _f(Classification.DEAD_UNCERTAIN, "low")
    assert decide([sole, uncertain]).verdict is Verdict.BLOCK
    assert decide([uncertain, sole]).verdict is Verdict.BLOCK


def test_insufficient_data_needs_review():
    f = Finding(edge=None, classification=Classification.INSUFFICIENT_DATA,
                confidence="low", evidence={})
    assert decide([f]).verdict is Verdict.NEEDS_REVIEW


def test_dead_uncertain_reason_distinguishes_no_flow_logs_from_short_window():
    e = NetworkEdge("a", "b", "tcp", 5432, "r1")
    no_logs = Finding(edge=e, classification=Classification.DEAD_UNCERTAIN, confidence="low",
                      evidence={"flow_logs_enabled": False, "window_days": 90.0})
    short = Finding(edge=e, classification=Classification.DEAD_UNCERTAIN, confidence="low",
                    evidence={"flow_logs_enabled": True, "window_days": 3.0})
    r_no_logs = decide([no_logs]).reasons[0]
    r_short = decide([short]).reasons[0]
    assert "flow logs are disabled" in r_no_logs
    assert "too short" in r_short and "flow logs are disabled" not in r_short
