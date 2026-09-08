import pytest
from inflight.model import Change, Verdict
from inflight.snapshot import load_from_file
from inflight.engine import evaluate

CASES = [
    ("tests/fixtures/trap_sole_path.json", Verdict.BLOCK),
    ("tests/fixtures/trap_infrequent_job.json", Verdict.NEEDS_REVIEW),
    ("tests/fixtures/trap_redundant_path.json", Verdict.SAFE),
    ("tests/fixtures/trap_world_open_live.json", Verdict.BLOCK),
    ("tests/fixtures/trap_world_open_dead.json", Verdict.SAFE),
]


@pytest.mark.parametrize("path,expected", CASES)
def test_trap_corpus(path, expected):
    env = load_from_file(path)
    out = evaluate(env, Change(kind="remove_sg_rules", rule_ids=("r1",)))
    assert out.verdict is expected, out.reasons
