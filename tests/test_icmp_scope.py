from inflight.model import EnvironmentModel, Resource, SGRule, Change, Verdict
from inflight.engine import evaluate


def _two_tier(protocol, from_port, to_port):
    rules = {"r1": SGRule("r1", "sg-db", "ingress", protocol, from_port, to_port,
                           ref_sg_id="sg-app")}
    return EnvironmentModel(
        resources={"i-app": Resource("i-app", "instance", "vpc-1", {"sg_ids": ["sg-app"]}),
                   "i-db": Resource("i-db", "instance", "vpc-1", {"sg_ids": ["sg-db"]})},
        sg_rules=rules, enis={}, routes={}, nacls={}, usage=[],
        window_days=90.0, flow_logs_enabled=True, usage_complete=True)


def test_icmp_sole_path_with_no_observed_usage_needs_review_not_safe():
    # VPC Flow Logs cannot report a port for ICMP, so absence of usage here is
    # unobservable, not proof the path is dead -- must not clear to SAFE.
    m = _two_tier("icmp", -1, -1)
    r = evaluate(m, Change("remove_sg_rules", ("r1",)))
    assert r.verdict is Verdict.NEEDS_REVIEW


def test_tcp_sole_path_with_no_observed_usage_is_still_safe():
    # Guard against over-broadening: a port-keyed protocol under the same
    # complete/full-window conditions still clears to SAFE on absence.
    m = _two_tier("tcp", 5432, 5432)
    r = evaluate(m, Change("remove_sg_rules", ("r1",)))
    assert r.verdict is Verdict.SAFE
