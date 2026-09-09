from inflight.snapshot_describe import load_from_describe_dir


def test_two_tier_map_and_cidrs():
    env = load_from_describe_dir("tests/fixtures/aws/two-tier", 90.0)
    # every instance private IP resolves to its instance id
    assert env.ip_to_resource.get("10.0.1.10") == "i-app0000000000001"
    assert env.ip_to_resource.get("10.0.1.20") == "i-db00000000000001"
    # the VPC CIDR is captured
    cidrs = [c for cs in env.vpc_cidrs.values() for c in cs]
    assert "10.0.0.0/16" in cidrs
