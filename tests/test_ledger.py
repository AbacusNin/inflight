import json
from inflight.ledger import Ledger


def test_append_chains_and_verifies(tmp_path):
    p = tmp_path / "ledger.jsonl"
    led = Ledger(str(p))
    led.append({"verdict": "block", "change": "r1"})
    led.append({"verdict": "safe", "change": "r2"})
    assert led.verify() is True


def test_tamper_breaks_verification(tmp_path):
    p = tmp_path / "ledger.jsonl"
    led = Ledger(str(p))
    led.append({"verdict": "block"})
    lines = p.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["entry"]["verdict"] = "safe"
    p.write_text(json.dumps(rec) + "\n")
    assert Ledger(str(p)).verify() is False
