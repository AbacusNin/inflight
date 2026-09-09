from inflight.model import EnvironmentModel


def _resources_with_sg(model: EnvironmentModel, sg_id: str) -> list:
    return [r for r in model.resources.values() if sg_id in r.attrs.get("sg_ids", [])]


def in_scope_probes(model: EnvironmentModel) -> set:
    """Instance-to-instance, same-VPC, single-port ingress SG-reference paths that
    Inflight v1 is responsible for. Derived from the rules independently of
    Inflight's own reachability output, so a path Inflight wrongly omits is still
    in scope and will surface as a differential failure."""
    probes = set()
    for rule in model.sg_rules.values():
        if rule.direction != "ingress" or rule.from_port != rule.to_port:
            continue
        if not rule.ref_sg_id:
            continue  # CIDR-sourced probes need an external prober; instance-to-instance only here
        dsts = _resources_with_sg(model, rule.sg_id)
        srcs = _resources_with_sg(model, rule.ref_sg_id)
        for d in dsts:
            for s in srcs:
                if s.vpc_id == d.vpc_id and s.id != d.id:
                    probes.add((s.id, d.id, rule.protocol, rule.from_port))
    return probes
