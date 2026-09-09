import ipaddress

from inflight.usage import resolve_flow_logs


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


def _pkt(rec: dict, key: str, fallback: str) -> str:
    """Resolve a pkt-* override, falling back when the field is absent or the
    literal "-" placeholder VPC Flow Logs emit for an unavailable value. Without
    this, a v5 custom log that lists pkt-srcaddr/pkt-dstaddr but emits "-" for a
    non-NAT'd OK flow would corrupt srcaddr/dstaddr to "-", dropping the flow from
    usage matching and turning a used path into a false safe (fail-open)."""
    v = rec.get(key)
    return v if v and v != "-" else fallback


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
        dstport = rec.get("dstport", "-")
        if not str(dstport).isdigit():
            continue  # portless (ICMP) flow cannot match a port-scoped edge
        out.append({
            "srcaddr": _pkt(rec, "pkt-srcaddr", rec["srcaddr"]),
            "dstaddr": _pkt(rec, "pkt-dstaddr", rec["dstaddr"]),
            "protocol": rec["protocol"],
            "dstport": int(dstport),
            "start": int(rec["start"]),
            "end": int(rec["end"]),
            "action": rec.get("action", "ACCEPT"),
        })
    return out


def _in_vpc(ip: str, model) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for cidrs in model.vpc_cidrs.values():
        for cidr in cidrs:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
    return False


def resolve_with_completeness(model, records: list) -> tuple:
    """Resolve raw Flow Log records against the model, and report whether the map
    was complete for what was observed. A destination inside the modeled VPC space
    that does not resolve to a known resource means a missing ENI, so usage may be
    undercounted and absence can no longer be trusted."""
    complete = True
    for r in records:
        if r["dstaddr"] not in model.ip_to_resource and _in_vpc(r["dstaddr"], model):
            complete = False
            break
    return resolve_flow_logs(model, records), complete


def discover_flow_logs(session, vpc_id: str) -> list:
    """Find the ACTIVE flow logs covering a VPC and where they deliver."""
    ec2 = session.client("ec2")
    resp = ec2.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc_id]}])
    out = []
    for fl in resp.get("FlowLogs", []):
        if fl.get("FlowLogStatus") not in (None, "ACTIVE"):
            continue
        dest = fl.get("LogDestinationType", "cloud-watch-logs")
        entry = {"destination_type": dest, "creation_time": fl.get("CreationTime"),
                 "log_format": fl.get("LogFormat")}  # None for the default v2 format
        if dest == "cloud-watch-logs":
            entry["log_group"] = fl.get("LogGroupName")
        else:
            target = fl.get("LogDestination", "")  # arn:aws:s3:::bucket/prefix
            tail = target.split(":::", 1)[-1]
            bucket, _, prefix = tail.partition("/")
            entry["bucket"], entry["prefix"] = bucket, prefix
        out.append(entry)
    return out


def fetch_cloudwatch(session, log_group: str, start_ms: int, end_ms: int) -> list:
    logs = session.client("logs")
    lines, token = [], None
    while True:
        kw = {"logGroupName": log_group, "startTime": start_ms, "endTime": end_ms}
        if token:
            kw["nextToken"] = token
        resp = logs.filter_log_events(**kw)
        lines.extend(e["message"].strip() for e in resp.get("events", []))
        token = resp.get("nextToken")
        if not token:
            return lines
