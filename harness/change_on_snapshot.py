import json
import os
import shutil

from inflight.model import Change


def _filter_group(group: dict, remove_ids: set) -> dict:
    sg_id = group["GroupId"]
    perms = []
    for i, perm in enumerate(group.get("IpPermissions", [])):
        pairs = [p for p in perm.get("UserIdGroupPairs", [])
                 if f"{sg_id}-in-{i}-{p['GroupId']}" not in remove_ids]
        ranges = [r for r in perm.get("IpRanges", [])
                  if f"{sg_id}-in-{i}-{r['CidrIp']}" not in remove_ids]
        if pairs or ranges:
            new_perm = dict(perm)
            new_perm["UserIdGroupPairs"] = pairs
            new_perm["IpRanges"] = ranges
            perms.append(new_perm)
    new_group = dict(group)
    new_group["IpPermissions"] = perms
    return new_group


def write_after_dir(before_dir: str, change: Change, after_dir: str) -> str:
    if change.kind != "remove_sg_rules":
        raise ValueError(f"harness supports remove_sg_rules only, got {change.kind}")
    remove_ids = set(change.rule_ids)
    if os.path.exists(after_dir):
        shutil.rmtree(after_dir)
    shutil.copytree(before_dir, after_dir)
    for root, _dirs, files in os.walk(after_dir):
        if "SecurityGroups.json" in files:
            path = os.path.join(root, "SecurityGroups.json")
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            data["SecurityGroups"] = [_filter_group(g, remove_ids)
                                      for g in data.get("SecurityGroups", [])]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
    return after_dir
