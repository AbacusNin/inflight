from inflight.model import EnvironmentModel
from inflight.reachability import permitted_edges


def _path_set(model: EnvironmentModel) -> set:
    return {(e.src, e.dst, e.protocol, e.port) for e in permitted_edges(model)}


def changed_paths(before: EnvironmentModel, after: EnvironmentModel) -> dict:
    b, a = _path_set(before), _path_set(after)
    return {"severed": b - a, "added": a - b}
