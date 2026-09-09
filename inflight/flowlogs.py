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


_V2_FIELDS = ("version account-id interface-id srcaddr dstaddr srcport dstport "
              "protocol packets bytes start end action log-status").split()


def parse_v2(lines: list) -> list:
    return parse_custom(lines, _V2_FIELDS)


def parse_custom(lines: list, fields: list) -> list:
    """Parse Flow Log lines given the field order. Drops NODATA/SKIPDATA rows and
    portless (ICMP) rows; raises on a row whose field count does not match `fields`
    so malformed input fails loud rather than yielding less usage."""
    idx = {name: i for i, name in enumerate(fields)}
    out = []
    for line in lines:
        line = line.strip()
        if not line or line.split()[0] == "version":  # a header line
            continue
        parts = line.split()
        if len(parts) != len(fields):
            raise ValueError(f"flow log row has {len(parts)} fields, expected {len(fields)}")
        rec = {name: parts[i] for name, i in idx.items()}
        if rec.get("log-status", "OK") != "OK":
            continue
        dstport = rec.get("pkt-dstport") or rec.get("dstport", "-")
        if not str(dstport).isdigit():
            continue  # portless (ICMP) flow cannot match a port-scoped edge
        out.append({
            "srcaddr": rec.get("pkt-srcaddr") or rec["srcaddr"],
            "dstaddr": rec.get("pkt-dstaddr") or rec["dstaddr"],
            "protocol": rec["protocol"],
            "dstport": int(dstport),
            "start": int(rec["start"]),
            "end": int(rec["end"]),
            "action": rec.get("action", "ACCEPT"),
        })
    return out
