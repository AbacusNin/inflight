from inflight.gate.lambda_handler import handler


def test_handler_blocks_and_disallows_sole_path():
    event = {"snapshot": "tests/fixtures/trap_sole_path.json",
             "change": {"kind": "remove_sg_rules", "rule_ids": ["r1"]}}
    out = handler(event, None)
    assert out["verdict"] == "block"
    assert out["allow"] is False


def test_handler_fails_closed_on_bad_input():
    out = handler({"snapshot": "does-not-exist.json",
                   "change": {"kind": "remove_sg_rules", "rule_ids": ["r1"]}}, None)
    assert out["verdict"] == "block"
    assert out["allow"] is False


def test_handler_rejects_path_traversal():
    out = handler({"snapshot": "../../../../etc/passwd",
                   "change": {"kind": "remove_sg_rules", "rule_ids": ["r1"]}}, None)
    assert out["verdict"] == "block"
    assert out["allow"] is False


def test_handler_writes_ledger_record(tmp_path):
    from inflight.ledger import Ledger
    led = tmp_path / "ledger.jsonl"
    handler({"snapshot": "tests/fixtures/trap_sole_path.json",
             "change": {"kind": "remove_sg_rules", "rule_ids": ["r1"]},
             "ledger": str(led)}, None)
    assert led.exists()
    assert Ledger(str(led)).verify() is True
