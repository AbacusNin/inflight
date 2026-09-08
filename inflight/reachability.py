from inflight.model import EnvironmentModel, NetworkEdge


def _resources_with_sg(model: EnvironmentModel, sg_id: str) -> list[str]:
    return [r.id for r in model.resources.values()
            if sg_id in r.attrs.get("sg_ids", [])]


def _nacl_denies(model: EnvironmentModel, dst_id: str, protocol: str, port: int) -> bool:
    dst = model.resources.get(dst_id)
    subnet = dst.attrs.get("subnet_id") if dst else None
    for entry in model.nacls.get(subnet, []):
        if entry.get("action") == "deny" and entry.get("protocol") in (protocol, "-1"):
            if entry.get("from_port", 0) <= port <= entry.get("to_port", 65535):
                return True
    return False


def permitted_edges(model: EnvironmentModel) -> list[NetworkEdge]:
    edges: list[NetworkEdge] = []
    for rule in model.sg_rules.values():
        if rule.direction != "ingress":
            continue
        dsts = _resources_with_sg(model, rule.sg_id)
        if rule.ref_sg_id:
            srcs = _resources_with_sg(model, rule.ref_sg_id)
        elif rule.cidr:
            srcs = [rule.cidr]
        else:
            srcs = []
        for dst in dsts:
            if _nacl_denies(model, dst, rule.protocol, rule.from_port):
                continue
            for src in srcs:
                edges.append(NetworkEdge(
                    src=src, dst=dst, protocol=rule.protocol,
                    port=rule.from_port, via_rule_id=rule.rule_id))
    return edges


def reachable(model: EnvironmentModel, src: str, dst: str,
              protocol: str, port: int) -> bool:
    for e in permitted_edges(model):
        if (e.src == src and e.dst == dst and e.protocol == protocol
                and e.port <= port <= _rule_to_port(model, e.via_rule_id)):
            return True
    return False


def _rule_to_port(model: EnvironmentModel, rule_id: str) -> int:
    rule = model.sg_rules.get(rule_id)
    return rule.to_port if rule else 0
