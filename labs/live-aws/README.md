# Tier-3 live-AWS validation lab

Provisions the same minimal topology as the emulator lab, but on real AWS, to
validate Inflight's live boto3 adapter against the real EC2 API. Credentials come
from the default chain (an IAM user with EC2 + SSM read, never root); no keys are
stored here. It costs a few cents and is meant to be torn down immediately after.

## Run

```
terraform -chdir=labs/live-aws init
terraform -chdir=labs/live-aws apply -auto-approve
python labs/emulator/validate.py "$(terraform -chdir=labs/live-aws output -raw vpc_id)"
terraform -chdir=labs/live-aws destroy -auto-approve   # always tear down
```

## What it showed

Against real AWS, the adapter reads the VPC's security groups (including the
default self-referencing group), the app-to-db rule, and the instances, and
returns `needs-review`: with no Flow Log usage wired in, it cannot prove a change
safe, so it fails closed. This validates the live read path against the real EC2
API. Real Flow Logs driving `block` and `safe` verdicts is the next increment (see
the roadmap in the top-level README).
