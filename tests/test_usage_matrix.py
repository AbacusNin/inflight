from inflight.snapshot_describe import load_from_describe_dir
from inflight.flowlogs import load_usage_from_file
from inflight.model import EnvironmentModel, Resource, SGRule, Change, Verdict
from inflight.engine import evaluate
from harness.flowlog_gen import FlowSpec, Profile, generate_v2

TWO_TIER = "tests/fixtures/aws/two-tier"
APP, DB = "i-app0000000000001", "i-db00000000000001"
RULE = "sg-db0000000000001-in-0-sg-app000000000001"
DAY = 86400
W30 = (1_690_000_000, 1_690_000_000 + 30 * DAY)
W7 = (1_690_000_000, 1_690_000_000 + 7 * DAY)


def _verdict(model, profile, rule_id, tmp_path):
    path = tmp_path / "flows.log"
    path.write_text("\n".join(generate_v2(model, profile)) + "\n", encoding="utf-8")
    load_usage_from_file(model, str(path))
    return evaluate(model, Change("remove_sg_rules", (rule_id,))).verdict


def test_busy_sole_path_blocks(tmp_path):
    model = load_from_describe_dir(TWO_TIER, 90.0)
    prof = Profile(W30, [FlowSpec(APP, DB, "tcp", 5432, 20)], anchor_dst=DB)
    assert _verdict(model, prof, RULE, tmp_path) is Verdict.BLOCK


def test_zero_traffic_full_window_is_safe(tmp_path):
    model = load_from_describe_dir(TWO_TIER, 90.0)
    prof = Profile(W30, [], anchor_dst=DB)
    assert _verdict(model, prof, RULE, tmp_path) is Verdict.SAFE


def test_short_window_needs_review(tmp_path):
    model = load_from_describe_dir(TWO_TIER, 90.0)
    prof = Profile(W7, [], anchor_dst=DB)
    assert _verdict(model, prof, RULE, tmp_path) is Verdict.NEEDS_REVIEW


def _redundant_model():
    rules = {
        "r1": SGRule("r1", "sg-db", "ingress", "tcp", 5432, 5432, ref_sg_id="sg-app"),
        "r2": SGRule("r2", "sg-db", "ingress", "tcp", 5432, 5432, ref_sg_id="sg-app"),
    }
    return EnvironmentModel(
        resources={APP: Resource(APP, "instance", "vpc-1", {"sg_ids": ["sg-app"]}),
                   DB: Resource(DB, "instance", "vpc-1", {"sg_ids": ["sg-db"]})},
        sg_rules=rules, enis={}, routes={}, nacls={}, usage=[], window_days=90.0,
        flow_logs_enabled=False, ip_to_resource={"10.0.1.10": APP, "10.0.1.20": DB},
        vpc_cidrs={"vpc-1": ["10.0.0.0/16"]})


def test_redundant_path_is_safe(tmp_path):
    model = _redundant_model()
    prof = Profile(W30, [FlowSpec(APP, DB, "tcp", 5432, 5)], anchor_dst=DB)
    assert _verdict(model, prof, "r1", tmp_path) is Verdict.SAFE  # r2 still permits the path


MISCONFIG = "tests/fixtures/aws/misconfig"
WEB = "i-web00000000000001"
SSH_RULE = "sg-web000000000001-in-0-0.0.0.0/0"
RDP_RULE = "sg-web000000000001-in-1-0.0.0.0/0"


def test_partial_cidr_usage_blocks(tmp_path):
    model = load_from_describe_dir(MISCONFIG, 90.0)
    prof = Profile(W30, [FlowSpec("0.0.0.0/0", WEB, "tcp", 22, 3)], anchor_dst=WEB)
    assert _verdict(model, prof, SSH_RULE, tmp_path) is Verdict.BLOCK


def test_unused_open_ssh_is_safe(tmp_path):
    model = load_from_describe_dir(MISCONFIG, 90.0)
    prof = Profile(W30, [], anchor_dst=WEB)  # no SSH traffic over a full window
    assert _verdict(model, prof, SSH_RULE, tmp_path) is Verdict.SAFE


def test_used_open_rdp_blocks(tmp_path):
    model = load_from_describe_dir(MISCONFIG, 90.0)
    prof = Profile(W30, [FlowSpec("0.0.0.0/0", WEB, "tcp", 3389, 2)], anchor_dst=WEB)
    assert _verdict(model, prof, RDP_RULE, tmp_path) is Verdict.BLOCK
