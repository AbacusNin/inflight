from inflight.model import EnvironmentModel, Resource
from inflight.flowlogs import resolve_with_completeness


def _model(ip_map, cidrs):
    return EnvironmentModel(
        resources={"i-db": Resource("i-db", "instance", "vpc-1", {"sg_ids": ["sg-db"]})},
        sg_rules={}, enis={}, routes={}, nacls={}, usage=[], window_days=90.0,
        flow_logs_enabled=True, ip_to_resource=ip_map, vpc_cidrs={"vpc-1": cidrs})


def _rec(dst):
    return {"srcaddr": "10.0.1.10", "dstaddr": dst, "protocol": "6", "dstport": 5432,
            "start": 1, "end": 2, "action": "ACCEPT"}


def test_resolved_destination_is_complete():
    recs, complete = resolve_with_completeness(
        _model({"10.0.1.20": "i-db"}, ["10.0.0.0/16"]), [_rec("10.0.1.20")])
    assert complete is True and recs[0].dst == "i-db"


def test_in_vpc_unresolved_destination_breaks_completeness():
    _recs, complete = resolve_with_completeness(
        _model({}, ["10.0.0.0/16"]), [_rec("10.0.1.99")])
    assert complete is False


def test_out_of_vpc_unresolved_destination_is_ignored():
    _recs, complete = resolve_with_completeness(
        _model({}, ["10.0.0.0/16"]), [_rec("8.8.8.8")])
    assert complete is True
