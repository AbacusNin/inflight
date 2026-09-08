import boto3
from botocore.stub import Stubber
from inflight.snapshot_aws import load_from_aws


def test_load_from_aws_maps_security_groups():
    ec2 = boto3.client("ec2", region_name="us-east-1",
                       aws_access_key_id="x", aws_secret_access_key="x")
    stub = Stubber(ec2)
    stub.add_response("describe_security_groups", {
        "SecurityGroups": [{
            "GroupId": "sg-db", "VpcId": "vpc-1",
            "IpPermissions": [{
                "IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432,
                "UserIdGroupPairs": [{"GroupId": "sg-app"}], "IpRanges": []}],
            "IpPermissionsEgress": []}]},
        {"Filters": [{"Name": "vpc-id", "Values": ["vpc-1"]}]})
    stub.add_response("describe_instances", {"Reservations": []},
                      {"Filters": [{"Name": "vpc-id", "Values": ["vpc-1"]}]})
    stub.add_response("describe_network_interfaces", {"NetworkInterfaces": []},
                      {"Filters": [{"Name": "vpc-id", "Values": ["vpc-1"]}]})
    stub.activate()

    class Sess:
        def client(self, _name):
            return ec2

    env = load_from_aws(Sess(), "vpc-1", window_days=90.0)
    assert any(r.ref_sg_id == "sg-app" and r.to_port == 5432
               for r in env.sg_rules.values())
