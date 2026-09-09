from inflight.snapshot_describe import load_from_describe_dir
from harness.scope_classifier import in_scope_probes


def test_in_scope_probe_from_minimal():
    model = load_from_describe_dir("tests/fixtures/aws/minimal", window_days=90.0)
    probes = in_scope_probes(model)
    assert ("i-app", "i-db", "tcp", 5432) in probes


def test_egress_and_ranged_rules_are_out_of_scope():
    from inflight.model import EnvironmentModel, Resource, SGRule
    r_egress = SGRule("e", "sg-a", "egress", "tcp", 443, 443, ref_sg_id="sg-b")
    r_ranged = SGRule("r", "sg-a", "ingress", "tcp", 5000, 6000, ref_sg_id="sg-b")
    model = EnvironmentModel(
        resources={"i-a": Resource("i-a", "instance", "vpc-1", {"sg_ids": ["sg-a"]}),
                   "i-b": Resource("i-b", "instance", "vpc-1", {"sg_ids": ["sg-b"]})},
        sg_rules={"e": r_egress, "r": r_ranged}, enis={}, routes={}, nacls={},
        usage=[], window_days=90.0, flow_logs_enabled=False)
    assert in_scope_probes(model) == set()
