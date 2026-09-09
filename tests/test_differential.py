import pytest

from inflight.model import Change
from inflight.snapshot_describe import load_from_describe_dir
from harness.scope_classifier import in_scope_probes
from harness.batfish_runner import batfish_available
from harness.differential import run_differential, ip_to_instance, normalize_batfish

TWO_TIER = "tests/fixtures/aws/two-tier"
HYBRID = "tests/fixtures/aws/hybrid-cloud"
APP_DB = ("i-app0000000000001", "i-db00000000000001", "tcp", 5432)


def test_normalize_batfish_maps_dst_ip_to_instance():
    # pure unit, no Batfish: a raw (node, ip, proto, port) tuple normalizes its dst IP
    ip_map = {"10.0.1.20": "i-db00000000000001"}
    raw = {("i-app0000000000001", "10.0.1.20", "tcp", 5432)}
    assert normalize_batfish(raw, ip_map) == {APP_DB}


def test_ip_to_instance_reads_the_two_tier_snapshot():
    ipmap = ip_to_instance(TWO_TIER)
    assert "i-db00000000000001" in ipmap.values()
    assert "i-app0000000000001" in ipmap.values()


@pytest.mark.skipif(not batfish_available(), reason="Batfish service not reachable")
def test_inflight_agrees_with_batfish_in_scope():
    model = load_from_describe_dir(TWO_TIER, 90.0)
    probes = in_scope_probes(model)
    assert probes == {APP_DB}
    rule_id = next(r_id for r_id, r in model.sg_rules.items()
                   if r.ref_sg_id and r.from_port == r.to_port == 5432)
    report = run_differential(TWO_TIER, Change("remove_sg_rules", (rule_id,)))
    assert report["in_scope_agreements"] == {APP_DB}
    assert report["in_scope_mismatches"] == set()


@pytest.mark.skipif(not batfish_available(), reason="Batfish service not reachable")
def test_scope_partitioning_on_hybrid_cloud():
    model = load_from_describe_dir(HYBRID, 90.0)
    assert in_scope_probes(model) == set()  # hybrid-cloud has no in-scope path
    carried = set()
    for r in model.resources.values():
        carried |= set(r.attrs.get("sg_ids", []))
    # a real out-of-scope change Batfish will notice: internet SSH to an instance-carried SG
    rule_id = next(r_id for r_id, r in model.sg_rules.items()
                   if r.cidr == "0.0.0.0/0" and r.from_port == 22 and r.sg_id in carried)
    report = run_differential(HYBRID, Change("remove_sg_rules", (rule_id,)))
    assert report["in_scope_mismatches"] == set()
    assert report["out_of_scope_batfish_only"]  # non-empty: machinery ran, gap logged
