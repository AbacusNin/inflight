from inflight.model import Change, EnvironmentModel, Thresholds
from inflight.impact import analyze
from inflight.verdict import decide


def evaluate(model: EnvironmentModel, change: Change,
             thresholds: Thresholds = Thresholds()):
    findings = analyze(model, change, thresholds)
    return decide(findings)
