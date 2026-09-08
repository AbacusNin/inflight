"""Run Inflight's live AWS adapter against the emulator lab and evaluate a rule
removal end to end. Reads the topology over boto3 (endpoint from the
AWS_ENDPOINT_URL env var, e.g. a local moto server), builds the internal model,
and prints the verdict.

Usage: python labs/emulator/validate.py <vpc_id>
"""
import sys

import boto3

from inflight.snapshot_aws import load_from_aws
from inflight.model import Change
from inflight.engine import evaluate


def main(vpc_id: str) -> int:
    env = load_from_aws(boto3.Session(), vpc_id, window_days=90.0)
    print("resources read:", sorted(env.resources))
    print("sg_rules read:")
    for rid, r in env.sg_rules.items():
        print(f"  {rid}: {r.direction} {r.protocol} {r.from_port}-{r.to_port} "
              f"ref={r.ref_sg_id} cidr={r.cidr}")
    print("flow_logs_enabled:", env.flow_logs_enabled, "(the emulator produces no flow records)")

    target = next((rid for rid, r in env.sg_rules.items()
                   if r.direction == "ingress" and r.ref_sg_id), None)
    if target is None:
        print("no ingress SG-reference rule found; nothing to evaluate")
        return 1
    print("\nproposed change: remove", target)
    result = evaluate(env, Change(kind="remove_sg_rules", rule_ids=(target,)))
    print("VERDICT:", result.verdict.value)
    for reason in result.reasons:
        print("  -", reason)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
