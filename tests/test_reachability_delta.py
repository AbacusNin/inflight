import copy
from inflight.snapshot_describe import load_from_describe_dir
from harness.reachability_delta import changed_paths


def test_severed_path_detected():
    before = load_from_describe_dir("tests/fixtures/aws/minimal", window_days=90.0)
    after = copy.deepcopy(before)
    after.sg_rules.clear()
    delta = changed_paths(before, after)
    assert ("i-app", "i-db", "tcp", 5432) in delta["severed"]
    assert delta["added"] == set()
