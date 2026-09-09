import pytest
from inflight.snapshot_describe import load_from_describe_dir
from inflight.flowlogs import load_usage_from_file
from harness.flowlog_gen import FlowSpec, Profile, generate_v2

TWO_TIER = "tests/fixtures/aws/two-tier"
APP, DB = "i-app0000000000001", "i-db00000000000001"
DAY = 86400


def _write(tmp_path, lines):
    p = tmp_path / "flows.log"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def test_round_trip_reproduces_the_profile(tmp_path):
    model = load_from_describe_dir(TWO_TIER, 90.0)
    prof = Profile(window=(1_690_000_000, 1_690_000_000 + 30 * DAY),
                   flows=[FlowSpec(APP, DB, "tcp", 5432, 5)], anchor_dst=DB)
    path = _write(tmp_path, generate_v2(model, prof))
    load_usage_from_file(model, path)
    rec = next(u for u in model.usage if u.dst == DB and u.port == 5432 and u.protocol == "tcp")
    assert rec.src == APP and rec.flow_count == 5


def test_window_is_fixed_by_the_anchors(tmp_path):
    model = load_from_describe_dir(TWO_TIER, 90.0)
    prof = Profile(window=(1_690_000_000, 1_690_000_000 + 7 * DAY), flows=[], anchor_dst=DB)
    path = _write(tmp_path, generate_v2(model, prof))
    load_usage_from_file(model, path)
    assert model.window_days == pytest.approx(7.0)


def test_protocol_name_becomes_iana_number():
    model = load_from_describe_dir(TWO_TIER, 90.0)
    prof = Profile(window=(1, 2), flows=[FlowSpec(APP, DB, "tcp", 5432, 1)], anchor_dst=DB)
    line = [ln for ln in generate_v2(model, prof) if " 5432 " in ln][0]
    assert line.split()[7] == "6"  # protocol field is the IANA number for tcp


def test_generated_record_parses_under_flowlogs_reader():
    frr = pytest.importorskip("flowlogs_reader")
    model = load_from_describe_dir(TWO_TIER, 90.0)
    prof = Profile(window=(1_690_000_000, 1_690_000_060),
                   flows=[FlowSpec(APP, DB, "tcp", 5432, 1)], anchor_dst=DB)
    line = [ln for ln in generate_v2(model, prof) if " 5432 " in ln][0]
    rec = frr.FlowRecord.from_cwl_event({"message": line})
    assert rec.dstport == 5432 and rec.protocol == 6  # flowlogs-reader casts protocol to int
