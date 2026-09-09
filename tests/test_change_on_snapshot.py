from inflight.model import Change
from inflight.snapshot_describe import load_from_describe_dir
from harness.change_on_snapshot import write_after_dir


def test_remove_rule_produces_after_without_it(tmp_path):
    before = load_from_describe_dir("tests/fixtures/aws/minimal", window_days=90.0)
    target = next(r_id for r_id, r in before.sg_rules.items() if r.ref_sg_id)
    after_dir = str(tmp_path / "after")
    write_after_dir("tests/fixtures/aws/minimal", Change("remove_sg_rules", (target,)), after_dir)
    after = load_from_describe_dir(after_dir, window_days=90.0)
    assert target not in after.sg_rules
    assert len(after.sg_rules) == len(before.sg_rules) - 1
