from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class Resource:
    id: str
    type: str            # "instance" | "rds" | "security_group" | "subnet" | ...
    vpc_id: str
    attrs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SGRule:
    rule_id: str
    sg_id: str
    direction: str       # "ingress" | "egress"
    protocol: str        # "tcp" | "udp" | "-1"
    from_port: int
    to_port: int
    cidr: str | None = None
    ref_sg_id: str | None = None


@dataclass(frozen=True)
class NetworkEdge:
    src: str             # resource id or CIDR
    dst: str             # resource id
    protocol: str
    port: int
    via_rule_id: str


@dataclass(frozen=True)
class UsageRecord:
    src: str
    dst: str
    protocol: str
    port: int
    flow_count: int
    first_seen: str
    last_seen: str


@dataclass
class EnvironmentModel:
    resources: dict
    sg_rules: dict
    enis: dict
    routes: dict
    nacls: dict
    usage: list
    window_days: float
    flow_logs_enabled: bool
    ip_to_resource: dict = field(default_factory=dict)
    vpc_cidrs: dict = field(default_factory=dict)
    usage_complete: bool = True


@dataclass(frozen=True)
class Change:
    kind: str            # "remove_sg_rules" | "tighten_sg_rule"
    rule_ids: tuple
    params: dict = field(default_factory=dict)


class Classification(Enum):
    DEAD = "dead"
    DEAD_UNCERTAIN = "dead_uncertain"
    LIVE_REDUNDANT = "live_redundant"
    LIVE_SOLE = "live_sole"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class Finding:
    edge: "NetworkEdge | None"
    classification: Classification
    confidence: str      # "high" | "low"
    evidence: dict


class Verdict(Enum):
    SAFE = "safe"
    NEEDS_REVIEW = "needs_review"
    BLOCK = "block"


@dataclass(frozen=True)
class VerdictResult:
    verdict: Verdict
    findings: tuple
    reasons: tuple


@dataclass(frozen=True)
class Thresholds:
    window_days_high_confidence: float = 30.0
    min_flows_for_used: int = 1
