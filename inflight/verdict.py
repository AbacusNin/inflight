from inflight.model import Classification, Finding, Verdict, VerdictResult


def decide(findings: list[Finding]) -> VerdictResult:
    reasons = []
    verdict = Verdict.SAFE
    for f in findings:
        if f.classification is Classification.LIVE_SOLE:
            verdict = Verdict.BLOCK
            reasons.append(
                f"blocks: {f.edge.src}->{f.edge.dst}:{f.edge.port} is a used sole path "
                f"({f.evidence})")
        elif f.classification is Classification.DEAD_UNCERTAIN and verdict is not Verdict.BLOCK:
            verdict = Verdict.NEEDS_REVIEW
            reasons.append(
                f"needs review: {f.edge.src}->{f.edge.dst}:{f.edge.port} looks unused but "
                f"the window is too short to be sure ({f.evidence})")
    if not reasons:
        reasons.append("safe: no used sole paths affected")
    return VerdictResult(verdict=verdict, findings=tuple(findings), reasons=tuple(reasons))
