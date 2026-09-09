import pytest
from inflight.flowlogs import parse_v2, parse_custom

V2 = "2 123456789 eni-1 10.0.1.10 10.0.1.20 40000 5432 6 10 840 1690000000 1690000060 ACCEPT OK"
NODATA = "2 123456789 eni-1 - - - - - - - 1690000000 1690000060 - NODATA"


def test_parse_v2_one_accept():
    recs = parse_v2([V2])
    assert recs == [{"srcaddr": "10.0.1.10", "dstaddr": "10.0.1.20", "protocol": "6",
                     "dstport": 5432, "start": 1690000000, "end": 1690000060,
                     "action": "ACCEPT"}]


def test_parse_v2_drops_nodata():
    assert parse_v2([NODATA]) == []


def test_parse_v2_raises_on_wrong_field_count():
    with pytest.raises(ValueError):
        parse_v2(["2 123456789 eni-1 10.0.1.10"])  # truncated OK-shaped row


def test_parse_custom_uses_field_list_and_pkt_addrs():
    fields = ["srcaddr", "dstaddr", "protocol", "dstport", "start", "end",
              "action", "log-status", "pkt-srcaddr", "pkt-dstaddr"]
    line = "3.3.3.3 1.1.1.1 6 5432 1690000000 1690000060 ACCEPT OK 10.0.1.10 10.0.1.20"
    recs = parse_custom([line], fields)
    # pkt-* recover the true in-VPC endpoints behind NAT
    assert recs[0]["srcaddr"] == "10.0.1.10" and recs[0]["dstaddr"] == "10.0.1.20"


def _flowlogs_reader_available() -> bool:
    try:
        import flowlogs_reader  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(not _flowlogs_reader_available(),
                     reason="flowlogs-reader not installed/importable on this Python")
def test_parse_v2_matches_flowlogs_reader():
    # Track a reference implementation: build its record from the same v2 line
    # and confirm our parser agrees on the fields the usage engine reads.
    from flowlogs_reader.flowlogs_reader import FlowRecord

    ref = FlowRecord.from_cwl_event({"message": V2})
    ours = parse_v2([V2])[0]
    assert ours["srcaddr"] == ref.srcaddr
    assert ours["dstaddr"] == ref.dstaddr
    assert ours["protocol"] == str(ref.protocol)
    assert ours["dstport"] == ref.dstport
