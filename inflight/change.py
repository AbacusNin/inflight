import copy
from dataclasses import replace

from inflight.model import Change, EnvironmentModel


def apply_change(model: EnvironmentModel, change: Change) -> EnvironmentModel:
    post = copy.deepcopy(model)
    if change.kind == "remove_sg_rules":
        for rid in change.rule_ids:
            post.sg_rules.pop(rid, None)
    elif change.kind == "tighten_sg_rule":
        for rid in change.rule_ids:
            rule = post.sg_rules.get(rid)
            if rule is not None:
                post.sg_rules[rid] = replace(
                    rule,
                    from_port=change.params["from_port"],
                    to_port=change.params["to_port"],
                )
    else:
        raise ValueError(f"unknown change kind: {change.kind}")
    return post
