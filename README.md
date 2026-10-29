# Inflight

Inflight decides whether a proposed security-group change is safe to apply, and
returns that decision with the evidence behind it: `safe`, `needs-review`, or
`block`. It is meant to sit in front of an automated remediation step as a
pre-flight check, so a fix that would sever a path something actually uses gets
caught before it runs.

## Why it exists

Cloud security tooling detects misconfigurations well and remediates them faster
every year. The part that stays hard is knowing, before a fix runs, whether the
fix breaks something that is in use. Generating the remediation is close to a
solved problem now (AWS and others will write the runbook for you), and letting a
model write the fix is the weak, error-prone step anyway. The value is in the
deterministic layer around the fix: deciding what to change and whether the
change is safe to apply. Inflight is that layer.

The decision is deterministic. The same snapshot and the same proposed change
always produce the same verdict, so the result is reproducible and auditable, and
nothing rests on a model at the point of decision.

## How it decides

Given a snapshot of an environment and a proposed change, Inflight:

1. Builds a model of the environment and computes network reachability itself,
   from security-group rules and NACL denies. It does not depend on any AWS
   analysis feature to hand it a reachability answer.
2. Annotates each reachable path with observed usage from VPC Flow Logs.
3. Applies the proposed change to a post-state model.
4. For each path the change affects, classifies it against three layers of
   evidence: structure (does a rule reference it), reachability (is there a path),
   and usage (did traffic actually flow). A path with observed traffic is high
   confidence; the absence of traffic is only as strong as the observation window.
5. Runs a counterfactual: for a path that is in use and would be severed, does an
   alternative path survive the change. A surviving alternative makes the removal
   safe; no alternative makes it a live sole path.
6. Aggregates a verdict, and records the decision with its evidence.

## What a verdict means

- `safe`: every affected path is either dead (no usage over a trusted window) or
  redundant (a surviving alternative path exists).
- `needs-review`: the evidence is not strong enough to clear the change. This
  includes a path that looks unused but only over a short window, and any change
  Inflight cannot model (see scope below).
- `block`: the change would sever a path that is in use and has no alternative.

Inflight fails closed. If it lacks the evidence to prove a change safe, it never
returns `safe`. A change it cannot model returns `needs-review`, an engine error
in the gate returns `block`, and an unresolvable snapshot returns `block`.

## Scope of v1

v1 confidently models intra-VPC, ingress, single-port security-group rules,
whether the source is another security group or a CIDR (including `0.0.0.0/0`
world-open rules, which it resolves from real Flow Log source addresses by CIDR
membership). It honors explicit NACL denies.

Anything outside that returns `needs-review` rather than a guess: egress rules,
ranged or all-ports rules, and internet-gateway, NAT, Transit Gateway, or peering
paths. IAM-diff and Terraform-plan gating are defined extension points, not built
in v1. This scope is deliberate, and the roadmap below tracks what extends it.

## Running it

Requires Python 3.14.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
```

Evaluate a proposed change against a snapshot. The exit code carries the verdict
(0 safe, 2 needs-review, 3 block, 1 usage error), so an orchestrator can branch on
it:

```bash
inflight evaluate --snapshot tests/fixtures/trap_sole_path.json --change tests/fixtures/change_remove_r1.json
```

That case blocks: removing the rule severs the only path the app tier uses to
reach the database. Removing a world-open SSH rule that has carried no traffic
over the window clears as safe:

```bash
inflight evaluate --snapshot tests/fixtures/trap_world_open_dead.json --change tests/fixtures/change_remove_r1.json
```

Those fixtures carry their usage inline. To decide against real traffic, point
Inflight at VPC Flow Logs, either a captured or exported log file:

```bash
inflight evaluate --snapshot snapshot.json --change change.json --flow-logs flows.log
```

or a live VPC, where it pulls the snapshot and the Flow Logs itself over a lookback
window using the ambient AWS credentials:

```bash
inflight evaluate --aws-vpc vpc-0abc123 --window-days 30 --change change.json
```

The fail-closed rule holds on the live path too. If flow logging did not cover the
full window, or the window is too short, or the resource map is incomplete, a
would-be `safe` becomes `needs-review` rather than clearing on an absence it cannot
trust.

A snapshot is a JSON description of resources, security-group rules, ENIs, routes,
NACLs, and usage. The fixtures under `tests/fixtures/` are worked examples, and
`tests/fixtures/minimal.json` is the smallest complete one.

## As a decision service

The verdict is decoupled from any one orchestrator. The same engine runs as the
CLI above and as an AWS Lambda handler (`inflight.gate.lambda_handler`) that
returns `{verdict, reasons, allow}`, where `allow` is true only for `safe`. The
Lambda fails closed to `block` on any error and constrains the snapshot path to an
allowed base directory. When the event carries a lookback window, it fetches the
target VPC's Flow Logs with its own role and decides against real usage, still
failing closed if the fetch or the coverage falls short. An SSM Automation document
can call the Lambda as a
pre-step and branch on `allow`; a sketch is in `docs/ssm-automation-adapter.md`.
The Lambda handler is tested offline. The SSM path has not run on live AWS yet,
and it needs a real account to check, because local emulators do not execute
Automation runbooks.

## Evidence and telemetry

Every decision can be written to a hash-chained, append-only ledger
(`inflight.ledger`), so a later reader can verify the record has not been altered.
Pass `--ledger PATH` to the CLI, or set `INFLIGHT_LEDGER` for the Lambda. The
engine also emits OpenTelemetry counters for verdicts and blast-radius size.

## Testing

```bash
.venv/Scripts/python.exe -m pytest
```

The suite's acceptance bar is a ground-truth trap corpus: cases where a
structure-only tool gets the answer wrong. A tightening that structure calls fine
but Flow Logs prove is the sole load-bearing path must block; a rule used by an
infrequent job that looks idle over a short window must return needs-review; a
redundant path removal must clear as safe. Property tests pin the invariants that
an unused path over a full window is safe and a used sole path is never safe.

Two harnesses take the bar past hand-authored cases.

The reachability half is checked by differential testing against Batfish, an
independent offline network-analysis engine. Inflight's "this change severs the
path" is compared against Batfish's own reachability answer, so the expected
result is not one I wrote. Two limits apply. The agreement on paths inside v1's
scope comes from a small synthetic two-tier network (`tests/fixtures/aws/two-tier/`).
The real topology in the suite, Batfish's hybrid-cloud example, holds no path
inside that scope, so it only exercises scope partitioning and out-of-scope
logging. The oracle is also Batfish's model of AWS, which is independent of
Inflight but is not AWS's own evaluator. These tests need a running Batfish
service and skip without one.

The usage half is checked by a synthetic Flow Log generator that emits real v2
records to a declared traffic profile, feeds them through the same ingestion path
the live tool uses, and asserts the verdict that profile implies: a busy sole path
blocks, a dead rule over a trusted window clears, a short window or an incomplete
map is held for review. This half has no independent oracle. It shows the pipeline
is self-consistent and that each verdict follows from the profile I declared.

Both harnesses run offline, with no AWS account.

## Runs against AWS

Two labs exercise the live read path. `labs/emulator/` provisions a small
app-to-database VPC in a local moto server with Terraform and runs the live adapter
against it. `labs/live-aws/` provisions the same topology on a real AWS account,
runs the adapter against the real EC2 API, and tears everything down. In both,
Inflight read the topology correctly and returned `needs-review`, because no Flow
Log usage was wired in and it could not prove the change safe.

Both runs predate Flow Log ingestion. Block and safe verdicts from live Flow Logs
are still untested against real AWS, and only the offline usage harness above
covers them.

## Roadmap

- Model rule age, so a rule newer than the observation window is held for review
  rather than cleared as unused. AWS does not expose a per-rule creation time in the
  snapshot data today, so this needs a separate source.
- Extend reachability to egress, ranged and all-ports rules, and internet-gateway,
  NAT, Transit Gateway, and peering paths.
- Complete the live AWS adapter: load RDS and other non-instance targets, paginate
  the describe calls, and capture egress rules.
- IAM-diff and Terraform-plan gating on the same impact-then-verdict contract.
- Strengthen the ledger from tamper-evident to tamper-resistant with a keyed
  signature or an external anchor.
