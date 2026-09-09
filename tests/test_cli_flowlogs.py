import json

import boto3
from botocore.stub import Stubber

from inflight.gate.cli import main


def _write(tmp, name, obj):
    p = tmp / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return str(p)


def test_cli_offline_flow_logs_blocks_a_used_sole_path(tmp_path, capsys):
    snapshot = _write(tmp_path, "snap.json", {
        "resources": [{"id": "i-app", "type": "instance", "vpc_id": "vpc-1", "attrs": {"sg_ids": ["sg-app"]}},
                      {"id": "i-db", "type": "instance", "vpc_id": "vpc-1", "attrs": {"sg_ids": ["sg-db"]}}],
        "sg_rules": [{"rule_id": "r1", "sg_id": "sg-db", "direction": "ingress",
                      "protocol": "tcp", "from_port": 5432, "to_port": 5432, "ref_sg_id": "sg-app"}],
        "usage": [], "window_days": 90.0, "flow_logs_enabled": True,
        "ip_to_resource": {"10.0.1.20": "i-db", "10.0.1.10": "i-app"},
        "vpc_cidrs": {"vpc-1": ["10.0.0.0/16"]}})
    change = _write(tmp_path, "chg.json", {"kind": "remove_sg_rules", "rule_ids": ["r1"]})
    logs = tmp_path / "logs.txt"
    logs.write_text(
        "2 123 eni-1 10.0.1.10 10.0.1.20 40000 5432 6 9 800 1690000000 1697760000 ACCEPT OK\n",
        encoding="utf-8")
    code = main(["evaluate", "--snapshot", snapshot, "--change", change,
                 "--flow-logs", str(logs)])
    assert code == 3  # BLOCK exit code: a real used sole path
    assert json.loads(capsys.readouterr().out)["verdict"] == "block"


def _stubbed_aws_session():
    """A session backed by real boto3 clients wired to Stubber, standing in for a
    live AWS account: one VPC, an app instance and a db instance, an sg-db rule
    that permits sg-app on 5432/tcp, and a CloudWatch-backed flow log that shows
    the app instance actually using that path."""
    ec2 = boto3.client("ec2", region_name="us-east-1",
                       aws_access_key_id="x", aws_secret_access_key="x")
    stub_ec2 = Stubber(ec2)
    vpc_filter = {"Filters": [{"Name": "vpc-id", "Values": ["vpc-1"]}]}
    stub_ec2.add_response("describe_security_groups", {"SecurityGroups": [{
        "GroupId": "sg-db", "VpcId": "vpc-1",
        "IpPermissions": [{"IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432,
                           "UserIdGroupPairs": [{"GroupId": "sg-app"}], "IpRanges": []}],
        "IpPermissionsEgress": []}]}, vpc_filter)
    stub_ec2.add_response("describe_instances", {"Reservations": [{"Instances": [
        {"InstanceId": "i-app", "VpcId": "vpc-1", "PrivateIpAddress": "10.0.1.10",
         "SecurityGroups": [{"GroupId": "sg-app"}]},
        {"InstanceId": "i-db", "VpcId": "vpc-1", "PrivateIpAddress": "10.0.1.20",
         "SecurityGroups": [{"GroupId": "sg-db"}]},
    ]}]}, vpc_filter)
    stub_ec2.add_response("describe_network_interfaces", {"NetworkInterfaces": []}, vpc_filter)
    stub_ec2.add_response("describe_vpcs", {"Vpcs": [{"VpcId": "vpc-1", "CidrBlock": "10.0.0.0/16"}]},
                          {"VpcIds": ["vpc-1"]})
    stub_ec2.add_response("describe_flow_logs", {"FlowLogs": [{
        "FlowLogId": "fl-1", "ResourceId": "vpc-1", "FlowLogStatus": "ACTIVE",
        "LogDestinationType": "cloud-watch-logs", "LogGroupName": "fl-group",
        "CreationTime": "2026-01-01T00:00:00Z"}]},
        {"Filters": [{"Name": "resource-id", "Values": ["vpc-1"]}]})
    stub_ec2.activate()

    logs = boto3.client("logs", region_name="us-east-1",
                        aws_access_key_id="x", aws_secret_access_key="x")
    stub_logs = Stubber(logs)
    stub_logs.add_response("filter_log_events", {"events": [{
        "message": "2 123 eni-1 10.0.1.10 10.0.1.20 40000 5432 6 9 800 "
                   "1690000000 1697760000 ACCEPT OK"}]})
    stub_logs.activate()

    class Sess:
        def client(self, name):
            return {"ec2": ec2, "logs": logs}[name]
    return Sess()


def test_cli_live_aws_vpc_yields_a_real_verdict(tmp_path, capsys):
    change = _write(tmp_path, "chg.json", {"kind": "remove_sg_rules",
                                           "rule_ids": ["sg-db-in-0-sg-app"]})
    session = _stubbed_aws_session()

    code = main(["evaluate", "--aws-vpc", "vpc-1", "--change", change,
                 "--window-days", "90"], session=session)

    assert code == 3  # BLOCK: the injected stub session drives a real used sole path
    assert json.loads(capsys.readouterr().out)["verdict"] == "block"
