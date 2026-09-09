from inflight.snapshot_describe import load_from_describe_dir


def test_hybrid_cloud_loads():
    env = load_from_describe_dir("tests/fixtures/aws/hybrid-cloud/aws_configs", window_days=90.0)
    assert len(env.sg_rules) > 0
    assert len(env.resources) > 0
