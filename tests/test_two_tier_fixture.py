from inflight.snapshot_describe import load_from_describe_dir
from harness.scope_classifier import in_scope_probes


def test_two_tier_has_exactly_one_in_scope_probe():
    model = load_from_describe_dir("tests/fixtures/aws/two-tier", window_days=90.0)
    probes = in_scope_probes(model)
    assert probes == {("i-app0000000000001", "i-db00000000000001", "tcp", 5432)}
