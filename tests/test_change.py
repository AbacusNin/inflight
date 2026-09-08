import copy
from inflight.model import Change
from inflight.snapshot import load_from_file
from inflight.change import apply_change


def test_remove_sg_rules_drops_rule_without_mutating_original():
    env = load_from_file("tests/fixtures/minimal.json")
    before = copy.deepcopy(env.sg_rules)
    post = apply_change(env, Change(kind="remove_sg_rules", rule_ids=("r1",)))
    assert "r1" not in post.sg_rules
    assert env.sg_rules == before


def test_tighten_sg_rule_narrows_ports():
    env = load_from_file("tests/fixtures/minimal.json")
    post = apply_change(env, Change(kind="tighten_sg_rule", rule_ids=("r1",),
                                    params={"from_port": 5433, "to_port": 5433}))
    assert post.sg_rules["r1"].from_port == 5433
