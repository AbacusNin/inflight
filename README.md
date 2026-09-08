# Inflight

Inflight decides whether a proposed security-group change is safe to apply. It
loads an environment snapshot, computes reachability, weighs observed usage, and
returns safe, needs-review, or block with the evidence behind the call.
