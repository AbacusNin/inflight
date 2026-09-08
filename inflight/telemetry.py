from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from inflight.model import VerdictResult


def build_test_meter():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    return provider.get_meter("inflight"), reader


def record_verdict(result: VerdictResult, meter) -> None:
    counter = meter.create_counter("inflight.verdicts")
    counter.add(1, {"verdict": result.verdict.value})
    blast = meter.create_counter("inflight.blast_radius")
    blast.add(len(result.findings), {"verdict": result.verdict.value})
