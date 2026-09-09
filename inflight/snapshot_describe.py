import glob
import json
import os

from inflight.model import EnvironmentModel, Resource, SGRule


def _rules_from_group(group: dict) -> list[SGRule]:
    out = []
    sg_id = group["GroupId"]
    for i, perm in enumerate(group.get("IpPermissions", [])):
        proto = perm.get("IpProtocol", "-1")
        frm = perm.get("FromPort", 0)
        to = perm.get("ToPort", 65535)
        for pair in perm.get("UserIdGroupPairs", []):
            out.append(SGRule(rule_id=f"{sg_id}-in-{i}-{pair['GroupId']}", sg_id=sg_id,
                              direction="ingress", protocol=proto, from_port=frm,
                              to_port=to, ref_sg_id=pair["GroupId"]))
        for rng in perm.get("IpRanges", []):
            out.append(SGRule(rule_id=f"{sg_id}-in-{i}-{rng['CidrIp']}", sg_id=sg_id,
                              direction="ingress", protocol=proto, from_port=frm,
                              to_port=to, cidr=rng["CidrIp"]))
    return out


def build_model_from_describe(groups, reservations, enis, window_days,
                              vpc_id="") -> EnvironmentModel:
    sg_rules = {}
    for g in groups:
        for rule in _rules_from_group(g):
            sg_rules[rule.rule_id] = rule
    resources = {}
    for res in reservations:
        for inst in res.get("Instances", []):
            sgs = [s["GroupId"] for s in inst.get("SecurityGroups", [])]
            resources[inst["InstanceId"]] = Resource(
                id=inst["InstanceId"], type="instance",
                vpc_id=inst.get("VpcId", vpc_id), attrs={"sg_ids": sgs})
    eni_map = {}
    for eni in enis:
        eni_map[eni["NetworkInterfaceId"]] = {
            "sg_ids": [g["GroupId"] for g in eni.get("Groups", [])],
            "subnet_id": eni.get("SubnetId")}
    return EnvironmentModel(resources=resources, sg_rules=sg_rules, enis=eni_map,
                            routes={}, nacls={}, usage=[], window_days=window_days,
                            flow_logs_enabled=False)


def _read_all(root: str, filename: str, key: str) -> list:
    items = []
    for path in glob.glob(os.path.join(root, "**", filename), recursive=True):
        with open(path, encoding="utf-8") as fh:
            items.extend(json.load(fh).get(key, []))
    return items


def load_from_describe_dir(path: str, window_days: float) -> EnvironmentModel:
    groups = _read_all(path, "SecurityGroups.json", "SecurityGroups")
    reservations = _read_all(path, "Reservations.json", "Reservations")
    enis = _read_all(path, "NetworkInterfaces.json", "NetworkInterfaces")
    return build_model_from_describe(groups, reservations, enis, window_days)
