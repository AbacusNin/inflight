from inflight.model import EnvironmentModel
from inflight.snapshot_describe import build_model_from_describe


def load_from_aws(session, vpc_id: str, window_days: float) -> EnvironmentModel:
    ec2 = session.client("ec2")
    flt = {"Filters": [{"Name": "vpc-id", "Values": [vpc_id]}]}
    groups = ec2.describe_security_groups(**flt)["SecurityGroups"]
    reservations = ec2.describe_instances(**flt)["Reservations"]
    enis = ec2.describe_network_interfaces(**flt)["NetworkInterfaces"]
    vpcs = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"]
    return build_model_from_describe(groups, reservations, enis, window_days,
                                     vpc_id=vpc_id, vpcs=vpcs)
