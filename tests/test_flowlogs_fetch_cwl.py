import boto3
from botocore.stub import Stubber
from inflight.flowlogs import discover_flow_logs, fetch_cloudwatch


def test_discover_cloudwatch_flow_log():
    ec2 = boto3.client("ec2", region_name="us-east-1",
                       aws_access_key_id="x", aws_secret_access_key="x")
    stub = Stubber(ec2)
    stub.add_response("describe_flow_logs", {"FlowLogs": [{
        "FlowLogId": "fl-1", "ResourceId": "vpc-1", "FlowLogStatus": "ACTIVE",
        "LogDestinationType": "cloud-watch-logs", "LogGroupName": "fl-group",
        "CreationTime": "2026-01-01T00:00:00Z"}]})
    stub.activate()

    class Sess:
        def client(self, _n): return ec2

    fls = discover_flow_logs(Sess(), "vpc-1")
    assert fls[0]["destination_type"] == "cloud-watch-logs"
    assert fls[0]["log_group"] == "fl-group"


def test_fetch_cloudwatch_pages_events():
    logs = boto3.client("logs", region_name="us-east-1",
                        aws_access_key_id="x", aws_secret_access_key="x")
    stub = Stubber(logs)
    stub.add_response("filter_log_events",
                      {"events": [{"message": "line-a"}], "nextToken": "t2"})
    stub.add_response("filter_log_events", {"events": [{"message": "line-b"}]})
    stub.activate()

    class Sess:
        def client(self, _n): return logs

    lines = fetch_cloudwatch(Sess(), "fl-group", 1000, 2000)
    assert lines == ["line-a", "line-b"]
