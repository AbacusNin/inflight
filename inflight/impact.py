from inflight.model import (
    Change, Classification, EnvironmentModel, Finding, NetworkEdge, Thresholds,
)
from inflight.reachability import permitted_edges, reachable
from inflight.change import apply_change
from inflight.usage import is_used


def affected_edges(pre: EnvironmentModel, change: Change) -> list[NetworkEdge]:
    return [e for e in permitted_edges(pre) if e.via_rule_id in change.rule_ids]


def classify_edge(pre, post, edge, thresholds) -> Finding:
    used = is_used(pre, edge, thresholds)
    survives = reachable(post, edge.src, edge.dst, edge.protocol, edge.port)
    if used:
        cls = Classification.LIVE_REDUNDANT if survives else Classification.LIVE_SOLE
        conf = "high"
    elif (pre.flow_logs_enabled and pre.window_days >= thresholds.window_days_high_confidence
          and pre.usage_complete):
        cls, conf = Classification.DEAD, "high"
    else:
        cls, conf = Classification.DEAD_UNCERTAIN, "low"
    evidence = {
        "used": used,
        "survives_post_change": survives,
        "window_days": pre.window_days,
        "flow_logs_enabled": pre.flow_logs_enabled,
        "usage_complete": pre.usage_complete,
    }
    return Finding(edge=edge, classification=cls, confidence=conf, evidence=evidence)


def analyze(pre: EnvironmentModel, change: Change, thresholds: Thresholds) -> list[Finding]:
    post = apply_change(pre, change)
    edges = affected_edges(pre, change)
    findings = [classify_edge(pre, post, e, thresholds) for e in edges]
    modeled = {e.via_rule_id for e in edges}
    unmodeled = [rid for rid in change.rule_ids if rid not in modeled]
    if unmodeled:
        findings.append(Finding(
            edge=None,
            classification=Classification.INSUFFICIENT_DATA,
            confidence="low",
            evidence={"unmodeled_rule_ids": unmodeled,
                      "reason": "change references rules with no modeled ingress impact; cannot prove safe"}))
    return findings
