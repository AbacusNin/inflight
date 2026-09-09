import ipaddress
from dataclasses import dataclass

from inflight.model import EnvironmentModel

_PROTO_NUM = {"tcp": 6, "udp": 17, "icmp": 1}


@dataclass
class FlowSpec:
    src: str       # edge source as permitted_edges yields it: a resource id or a CIDR
    dst: str       # edge destination: a resource id
    protocol: str  # "tcp" | "udp"
    port: int
    count: int


@dataclass
class Profile:
    window: tuple          # (start_epoch_seconds, end_epoch_seconds)
    flows: list             # list[FlowSpec]
    anchor_dst: str          # a resource id whose IP resolves, so anchors do not trip completeness
    anchor_port: int = 443  # a port with no matching rule, so anchors light no modeled edge


def _instance_ip(model: EnvironmentModel, resource_id: str) -> str:
    for ip, rid in model.ip_to_resource.items():
        if rid == resource_id:
            return ip
    raise ValueError(f"no IP maps to resource {resource_id!r}")


def _src_ip(model: EnvironmentModel, src: str) -> str:
    if "/" in src:  # a CIDR source: pick a representative address inside it
        net = ipaddress.ip_network(src, strict=False)
        return str(next(iter(net.hosts()), net.network_address))
    return _instance_ip(model, src)


def _v2_line(srcaddr, dstaddr, srcport, dstport, proto_num, start, end) -> str:
    # v2 default field order; benign packets/bytes; ACCEPT; log-status OK
    return (f"2 123456789012 eni-gen {srcaddr} {dstaddr} {srcport} {dstport} "
            f"{proto_num} 10 840 {start} {end} ACCEPT OK")


def generate_v2(model: EnvironmentModel, profile: Profile) -> list:
    """Emit v2 Flow Log lines for a declared profile. Two anchor records fix the
    observation window; per-flow records reproduce the profile after real ingest."""
    start, end = profile.window
    anchor_ip = _instance_ip(model, profile.anchor_dst)
    lines = [
        _v2_line("192.0.2.1", anchor_ip, 40000, profile.anchor_port, 6, start, start + 1),
        _v2_line("192.0.2.1", anchor_ip, 40000, profile.anchor_port, 6, end - 1, end),
    ]
    for f in profile.flows:
        src_ip = _src_ip(model, f.src)
        dst_ip = _instance_ip(model, f.dst)
        num = _PROTO_NUM[f.protocol]
        step = max(1, (end - start) // (f.count + 1))
        for i in range(f.count):
            t = start + (i + 1) * step
            lines.append(_v2_line(src_ip, dst_ip, 40000 + i, f.port, num, t, t + 1))
    return lines
