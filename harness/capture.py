import json
import os


def capture(session, out_dir: str, region: str = "us-east-1") -> str:
    ec2 = session.client("ec2")
    dest = os.path.join(out_dir, "aws_configs", region)
    os.makedirs(dest, exist_ok=True)
    writes = {
        "SecurityGroups.json": {"SecurityGroups": ec2.describe_security_groups()["SecurityGroups"]},
        "Reservations.json": {"Reservations": ec2.describe_instances()["Reservations"]},
        "NetworkInterfaces.json": {"NetworkInterfaces": ec2.describe_network_interfaces()["NetworkInterfaces"]},
    }
    for name, payload in writes.items():
        with open(os.path.join(dest, name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    return out_dir
