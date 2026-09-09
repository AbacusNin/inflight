from datetime import datetime, timezone
import boto3
from botocore.stub import Stubber
from inflight.model import EnvironmentModel, Resource, Thresholds
from inflight.flowlogs import (
    load_usage_from_aws, load_usage_from_file, effective_window_days, fields_from_format,
)


def test_fields_from_format_extracts_ordered_field_names():
    fmt = "${srcaddr} ${dstaddr} ${protocol} ${dstport} ${start} ${end} ${action} ${log-status}"
    assert fields_from_format(fmt) == ["srcaddr", "dstaddr", "protocol", "dstport",
                                       "start", "end", "action", "log-status"]


def _model():
    return EnvironmentModel(
        resources={"i-app": Resource("i-app", "instance", "vpc-1", {"sg_ids": ["sg-app"]}),
                   "i-db": Resource("i-db", "instance", "vpc-1", {"sg_ids": ["sg-db"]})},
        sg_rules={}, enis={}, routes={}, nacls={}, usage=[], window_days=90.0,
        flow_logs_enabled=False, ip_to_resource={"10.0.1.20": "i-db"},
        vpc_cidrs={"vpc-1": ["10.0.0.0/16"]})


def test_effective_window_is_capped_by_coverage():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    # logging began 3 days before now, requested window is 90 days
    assert effective_window_days("2026-01-07T00:00:00Z", 90.0, now) == 3.0


def test_no_active_flow_log_leaves_flow_logs_disabled():
    class FakeSession:  # discovery returns nothing
        def client(self, _n):
            class C:
                def describe_flow_logs(self, **_): return {"FlowLogs": []}
            return C()
    m = load_usage_from_aws(FakeSession(), _model(), 90.0)
    assert m.flow_logs_enabled is False


def _stubbed_session(flow_log: dict, log_events: list):
    ec2 = boto3.client("ec2", region_name="us-east-1",
                       aws_access_key_id="x", aws_secret_access_key="x")
    stub_ec2 = Stubber(ec2)
    stub_ec2.add_response("describe_flow_logs", {"FlowLogs": [flow_log]})
    stub_ec2.activate()

    logs = boto3.client("logs", region_name="us-east-1",
                        aws_access_key_id="x", aws_secret_access_key="x")
    stub_logs = Stubber(logs)
    stub_logs.add_response("filter_log_events", {"events": log_events})
    stub_logs.activate()

    class Sess:
        def client(self, name):
            return {"ec2": ec2, "logs": logs}[name]
    return Sess()


def test_short_live_coverage_caps_window_below_high_confidence():
    # the flow log went active 3 days ago; a 90-day request cannot manufacture
    # 90 days of coverage out of 3 days of logging
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    flow_log = {"FlowLogId": "fl-1", "ResourceId": "vpc-1", "FlowLogStatus": "ACTIVE",
                "LogDestinationType": "cloud-watch-logs", "LogGroupName": "fl-group",
                "CreationTime": "2026-01-07T00:00:00Z"}
    session = _stubbed_session(flow_log, [])

    m = load_usage_from_aws(session, _model(), 90.0, now=now)
    assert m.flow_logs_enabled is True
    assert m.window_days < Thresholds().window_days_high_confidence


def test_in_vpc_unresolved_destination_marks_usage_incomplete():
    # 10.0.1.99 is inside the modeled VPC's CIDR but has no matching ENI, so the
    # map cannot be trusted to have seen everything -- usage_complete must go False
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    flow_log = {"FlowLogId": "fl-1", "ResourceId": "vpc-1", "FlowLogStatus": "ACTIVE",
                "LogDestinationType": "cloud-watch-logs", "LogGroupName": "fl-group",
                "CreationTime": "2025-01-01T00:00:00Z"}
    line = "2 123456789 eni-1 10.0.1.10 10.0.1.99 40000 5432 6 10 840 1690000000 1690000060 ACCEPT OK"
    session = _stubbed_session(flow_log, [{"message": line}])

    m = load_usage_from_aws(session, _model(), 90.0, now=now)
    assert m.usage_complete is False


def test_creation_time_as_real_datetime_does_not_crash():
    # boto3/botocore return describe_flow_logs' CreationTime as a real
    # datetime.datetime object (a "timestamp"-shaped field), never a string.
    # A Stubber fixture that plants a raw string bypasses the wire-protocol
    # parser and masks that; this plants an actual datetime so the regression
    # (TypeError from creation_time.replace("Z", "+00:00")) is caught for real.
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    flow_log = {"FlowLogId": "fl-1", "ResourceId": "vpc-1", "FlowLogStatus": "ACTIVE",
                "LogDestinationType": "cloud-watch-logs", "LogGroupName": "fl-group",
                "CreationTime": datetime(2026, 1, 7, tzinfo=timezone.utc)}
    session = _stubbed_session(flow_log, [])

    m = load_usage_from_aws(session, _model(), 90.0, now=now)
    assert m.flow_logs_enabled is True
    assert m.window_days == 3.0


def test_effective_window_days_accepts_datetime_directly():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    started = datetime(2026, 1, 7, tzinfo=timezone.utc)
    assert effective_window_days(started, 90.0, now) == 3.0


def test_effective_window_days_treats_naive_datetime_as_utc():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    started = datetime(2026, 1, 7)  # naive, no tzinfo
    assert effective_window_days(started, 90.0, now) == 3.0


def test_effective_window_days_fails_closed_when_creation_time_unknown():
    # an unknown coverage start must not be able to clear a not-used edge to
    # safe by granting the full requested window (that was the old fail-open bug)
    assert effective_window_days(None, 90.0) == 0.0


def test_custom_log_format_routes_through_parse_custom_not_v2():
    # a per-flow-log LogFormat must drive parse_custom with its own field order;
    # routing it through parse_v2's fixed 14-field layout instead would either
    # crash on the field-count mismatch or silently misassign columns
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    custom_fmt = "${srcaddr} ${dstaddr} ${protocol} ${dstport} ${start} ${end} ${action} ${log-status}"
    flow_log = {"FlowLogId": "fl-1", "ResourceId": "vpc-1", "FlowLogStatus": "ACTIVE",
                "LogDestinationType": "cloud-watch-logs", "LogGroupName": "fl-group",
                "CreationTime": "2025-01-01T00:00:00Z", "LogFormat": custom_fmt}
    line = "10.0.1.10 10.0.1.20 6 5432 1690000000 1690000060 ACCEPT OK"
    session = _stubbed_session(flow_log, [{"message": line}])

    m = load_usage_from_aws(session, _model(), 90.0, now=now)
    assert any(u.dst == "i-db" and u.protocol == "tcp" and u.port == 5432
               for u in m.usage)


def test_load_usage_from_file_populates_model(tmp_path):
    lines = [
        "2 123456789012 eni-1 10.0.1.10 10.0.1.20 40000 5432 6 10 840 "
        "1690000000 1690086400 ACCEPT OK",
    ]
    path = tmp_path / "captured.log"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    m = load_usage_from_file(_model(), str(path))

    assert m.flow_logs_enabled is True
    assert m.usage_complete is True
    assert m.window_days == 1.0  # (1690086400 - 1690000000) / 86400
    assert any(u.dst == "i-db" and u.protocol == "tcp" and u.port == 5432
               for u in m.usage)
