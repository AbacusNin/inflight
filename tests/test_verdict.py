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
