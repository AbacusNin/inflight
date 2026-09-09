def build_ip_to_resource(reservations: list, enis: list) -> dict:
    """Map every private and public IP of every instance and ENI to its resource
    id, so Flow Log destinations (which are IP addresses) can be matched to modeled
    resources. An empty map is the root of the usage fail-open, so this must cover
    every ENI the snapshot knows."""
    out: dict[str, str] = {}
    for res in reservations:
        for inst in res.get("Instances", []):
            iid = inst["InstanceId"]
            for key in ("PrivateIpAddress", "PublicIpAddress"):
                if inst.get(key):
                    out[inst[key]] = iid
            for ni in inst.get("NetworkInterfaces", []):
                for pip in ni.get("PrivateIpAddresses", []):
                    if pip.get("PrivateIpAddress"):
                        out[pip["PrivateIpAddress"]] = iid
    for eni in enis:
        iid = eni.get("Attachment", {}).get("InstanceId")
        if not iid:
            continue
        for pip in eni.get("PrivateIpAddresses", []):
            if pip.get("PrivateIpAddress"):
                out[pip["PrivateIpAddress"]] = iid
    return out


def vpc_cidrs_from(vpcs: list) -> dict:
    """Map each VPC id to its CIDR blocks, used to tell an in-VPC destination
    (a missing-ENI completeness breach) from an out-of-VPC one (out of scope)."""
    out: dict[str, list] = {}
    for v in vpcs:
        cidrs = [c["CidrBlock"] for c in v.get("CidrBlockAssociationSet", [])
                 if c.get("CidrBlock")]
        if not cidrs and v.get("CidrBlock"):
            cidrs = [v["CidrBlock"]]
        out[v["VpcId"]] = cidrs
    return out
