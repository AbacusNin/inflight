import pytest

from inflight.snapshot_describe import load_from_describe_dir


def test_load_from_describe_dir_builds_model():
    env = load_from_describe_dir("tests/fixtures/aws/minimal", window_days=90.0)
    assert "i-app" in env.resources and "i-db" in env.resources
    rule = next(r for r in env.sg_rules.values() if r.ref_sg_id)
    assert rule.direction == "ingress" and rule.from_port == 5432 and rule.ref_sg_id == "sg-app"
    assert env.flow_logs_enabled is False


def test_load_from_describe_dir_rejects_non_snapshot_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_from_describe_dir(str(tmp_path), window_days=90.0)
