import socket


def batfish_available(host: str = "localhost", port: int = 9997) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _session(host: str = "localhost"):
    from pybatfish.client.session import Session
    bf = Session(host=host)
    return bf


def differential_reachable_pairs(before_dir: str, after_dir: str,
                                 host: str = "localhost") -> set:
    bf = _session(host)
    bf.set_network("inflight-harness")
    bf.init_snapshot(before_dir, name="before", overwrite=True)
    bf.init_snapshot(after_dir, name="after", overwrite=True)
    ans = bf.q.differentialReachability(
        pathConstraints=None).answer(snapshot="after", reference_snapshot="before")
    frame = ans.frame()
    return _pairs_from_frame(frame)


def _pairs_from_frame(frame) -> set:
    """Extract (src_instance, dst_instance, protocol, port) from the answer frame."""
    pairs = set()
    for _idx, row in frame.iterrows():
        flow = row.get("Flow") if hasattr(row, "get") else row["Flow"]
        src = getattr(flow, "ingressNode", None)
        dst = getattr(flow, "dstIp", None)
        proto = str(getattr(flow, "ipProtocol", "")).lower()
        port = getattr(flow, "dstPort", None)
        pairs.add((src, dst, proto, port))
    return pairs
