import json
import os
import boto3
from botocore.stub import Stubber
from harness.capture import capture


def test_capture_writes_describe_files(tmp_path):
    ec2 = boto3.client("ec2", region_name="us-east-1",
                       aws_access_key_id="x", aws_secret_access_key="x")
    stub = Stubber(ec2)
    stub.add_response("describe_security_groups", {"SecurityGroups": [{"GroupId": "sg-1"}]})
    stub.add_response("describe_instances", {"Reservations": []})
    stub.add_response("describe_network_interfaces", {"NetworkInterfaces": []})
    stub.activate()

    class Sess:
        def client(self, _n):
            return ec2

    out = capture(Sess(), str(tmp_path / "snap"), region="us-east-1")
    sg = json.load(open(os.path.join(out, "aws_configs", "us-east-1", "SecurityGroups.json")))
    assert sg["SecurityGroups"][0]["GroupId"] == "sg-1"
