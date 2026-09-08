from inflight.snapshot import load_from_file


def test_load_from_file_builds_model(tmp_path):
    env = load_from_file("tests/fixtures/minimal.json")
    assert "rds-app" in env.resources
    assert env.sg_rules["r1"].to_port == 5432
    assert env.flow_logs_enabled is True
    assert env.window_days == 90.0
