import json
from inflight.gate.lambda_handler import handler


def test_handler_fetches_usage_and_blocks_used_sole(tmp_path, monkeypatch):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps({
        "resources": [{"id": "i-app", "type": "instance", "vpc_id": "vpc-1", "attrs": {"sg_ids": ["sg-app"]}},
                      {"id": "i-db", "type": "instance", "vpc_id": "vpc-1", "attrs": {"sg_ids": ["sg-db"]}}],
        "sg_rules": [{"rule_id": "r1", "sg_id": "sg-db", "direction": "ingress",
                      "protocol": "tcp", "from_port": 5432, "to_port": 5432, "ref_sg_id": "sg-app"}],
        "usage": [], "window_days": 90.0, "flow_logs_enabled": True,
        "ip_to_resource": {"10.0.1.20": "i-db"}, "vpc_cidrs": {"vpc-1": ["10.0.0.0/16"]}}), encoding="utf-8")
    monkeypatch.setenv("INFLIGHT_BASE_DIR", str(tmp_path))

    class FakeUsage:  # stand in for load_usage_from_aws
        def __call__(self, _sess, model, _win):
            from inflight.model import UsageRecord
            model.usage = [UsageRecord("i-app", "i-db", "tcp", 5432, 5, "t0", "t1")]
            model.flow_logs_enabled = True
            model.usage_complete = True
            return model
    monkeypatch.setattr("inflight.gate.lambda_handler.load_usage_from_aws", FakeUsage())

    out = handler({"snapshot": "snap.json", "change": {"kind": "remove_sg_rules", "rule_ids": ["r1"]},
                   "window_days": 90.0}, None, session=object())
    assert out["verdict"] == "block" and out["allow"] is False


def test_handler_fails_closed_on_fetch_error(tmp_path, monkeypatch):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps({
        "resources": [{"id": "i-app", "type": "instance", "vpc_id": "vpc-1", "attrs": {"sg_ids": ["sg-app"]}},
                      {"id": "i-db", "type": "instance", "vpc_id": "vpc-1", "attrs": {"sg_ids": ["sg-db"]}}],
        "sg_rules": [{"rule_id": "r1", "sg_id": "sg-db", "direction": "ingress",
                      "protocol": "tcp", "from_port": 5432, "to_port": 5432, "ref_sg_id": "sg-app"}],
        "usage": [], "window_days": 90.0, "flow_logs_enabled": True,
        "ip_to_resource": {"10.0.1.20": "i-db"}, "vpc_cidrs": {"vpc-1": ["10.0.0.0/16"]}}), encoding="utf-8")
    monkeypatch.setenv("INFLIGHT_BASE_DIR", str(tmp_path))
    led = tmp_path / "ledger.jsonl"

    def raising_fetch(_sess, _model, _win):
        raise RuntimeError("boto3 client error")
    monkeypatch.setattr("inflight.gate.lambda_handler.load_usage_from_aws", raising_fetch)

    out = handler({"snapshot": "snap.json", "change": {"kind": "remove_sg_rules", "rule_ids": ["r1"]},
                   "window_days": 90.0, "ledger": str(led)}, None, session=object())
    assert out["verdict"] == "block" and out["allow"] is False

    from inflight.ledger import Ledger
    assert led.exists()
    assert Ledger(str(led)).verify() is True
