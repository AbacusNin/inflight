from inflight.model import Classification, Finding, Verdict, VerdictResult


def decide(findings: list[Finding]) -> VerdictResult:
    reasons = []
    verdict = Verdict.SAFE
    for f in findings:
        loc = f"{f.edge.src}->{f.edge.dst}:{f.edge.port}" if f.edge is not None else "change"
        if f.classification is Classification.LIVE_SOLE:
            verdict = Verdict.BLOCK
            reasons.append(f"blocks: {loc} is a used sole path ({f.evidence})")
        elif (f.classification in (Classification.DEAD_UNCERTAIN, Classification.INSUFFICIENT_DATA)
              and verdict is not Verdict.BLOCK):
            verdict = Verdict.NEEDS_REVIEW
            if f.classification is Classification.INSUFFICIENT_DATA:
                reasons.append(f"needs review: {loc} could not be analyzed ({f.evidence})")
            elif not f.evidence.get("flow_logs_enabled", True):
                reasons.append(
                    f"needs review: {loc} has no usage evidence, flow logs are disabled, "
                    f"so it cannot be cleared ({f.evidence})")
            else:
                reasons.append(
                    f"needs review: {loc} looks unused but the observation window is too short "
                    f"to be sure ({f.evidence})")
    if not reasons:
        reasons.append("safe: no used sole paths affected")
    return VerdictResult(verdict=verdict, findings=tuple(findings), reasons=tuple(reasons))
