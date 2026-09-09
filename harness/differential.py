import glob
import json
import os
import tempfile

from inflight.model import Change
from inflight.snapshot_describe import load_from_describe_dir
from harness.change_on_snapshot import write_after_dir
from harness.reachability_delta import changed_paths
from harness.scope_classifier import in_scope_probes
from harness.batfish_runner import differential_reachable_pairs


def ip_to_instance(before_dir: str) -> dict:
    """Map every private and public IP in the snapshot to its instance id, so
    Batfish's IP-addressed destinations can be compared with Inflight's
    instance-id paths."""
    out = {}
    for path in glob.glob(os.path.join(before_dir, "**", "Reservations.json"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for res in data.get("Reservations", []):
            for inst in res.get("Instances", []):
                iid = inst["InstanceId"]
                for key in ("PrivateIpAddress", "PublicIpAddress"):
                    if inst.get(key):
                        out[inst[key]] = iid
                for ni in inst.get("NetworkInterfaces", []):
                    for pip in ni.get("PrivateIpAddresses", []):
                        if pip.get("PrivateIpAddress"):
                            out[pip["PrivateIpAddress"]] = iid
    for path in glob.glob(os.path.join(before_dir, "**", "NetworkInterfaces.json"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for eni in data.get("NetworkInterfaces", []):
            iid = eni.get("Attachment", {}).get("InstanceId")
            if not iid:
                continue
            for pip in eni.get("PrivateIpAddresses", []):
                if pip.get("PrivateIpAddress"):
                    out[pip["PrivateIpAddress"]] = iid
    return out


def normalize_batfish(raw: set, ip_map: dict) -> set:
    """Rewrite each Batfish (src_node, dst_ip, proto, port) into instance-id space
    by resolving the destination IP to its instance. The source node is left as-is:
    an instance source already matches Inflight's ids; a non-instance source
    (subnet, transit gateway) will not intersect the instance-id probe set, which
    is correct -- those are out of Inflight v1 scope."""
    return {(src, ip_map.get(dst, dst), proto, port) for (src, dst, proto, port) in raw}


def run_differential(before_dir: str, change: Change, window_days: float = 90.0) -> dict:
    """Apply change to the before snapshot and diff Inflight against Batfish, returning a dict
    with in_scope_agreements, in_scope_mismatches, and out_of_scope_batfish_only key sets."""
    before = load_from_describe_dir(before_dir, window_days)
    probes = in_scope_probes(before)
    ip_map = ip_to_instance(before_dir)
    with tempfile.TemporaryDirectory() as tmp:
        after_dir = write_after_dir(before_dir, change, os.path.join(tmp, "after"))
        after = load_from_describe_dir(after_dir, window_days)
        inflight_severed = changed_paths(before, after)["severed"] & probes
        batfish_norm = normalize_batfish(differential_reachable_pairs(before_dir, after_dir), ip_map)
    batfish_in_scope = batfish_norm & probes
    return {
        "in_scope_agreements": inflight_severed & batfish_in_scope,
        "in_scope_mismatches": inflight_severed ^ batfish_in_scope,
        "out_of_scope_batfish_only": batfish_norm - probes,
    }
