from inflight.model import VerdictResult, Verdict
from inflight.telemetry import record_verdict, build_test_meter


def test_record_verdict_increments_counter():
    meter, reader = build_test_meter()
    result = VerdictResult(verdict=Verdict.BLOCK, findings=(), reasons=("r",))
    record_verdict(result, meter)
    data = reader.get_metrics_data()
    metrics = [m for rm in data.resource_metrics for sm in rm.scope_metrics
               for m in sm.metrics]
    assert any(m.name == "inflight.verdicts" for m in metrics)
