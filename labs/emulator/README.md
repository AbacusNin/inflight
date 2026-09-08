# Emulator validation lab

Stands up a minimal VPC (an app tier reaching a db tier over tcp/5432) in a local
AWS emulator, then runs Inflight's live boto3 adapter against it. This validates
the live read path end to end with no AWS account and no spend.

It targets a local [moto](https://github.com/getmoto/moto) server, which needs no
account or token. Terraform provisions the topology, so the lab doubles as an
infrastructure-as-code artifact.

## Run

From the repo root, in the project virtualenv, start the emulator:

```
moto_server -p 5001
```

Provision the lab:

```
terraform -chdir=labs/emulator init
terraform -chdir=labs/emulator apply -auto-approve
```

Run Inflight's adapter against it:

```
AWS_ENDPOINT_URL=http://localhost:5001 AWS_ACCESS_KEY_ID=test \
  AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 \
  python labs/emulator/validate.py "$(terraform -chdir=labs/emulator output -raw vpc_id)"
```

## What it shows

The adapter reads the real topology (two instances and the app-to-db ingress
rule) over boto3 from the emulator. The emulator produces no Flow Log usage, so
Inflight has no usage evidence and returns `needs-review` rather than a false
`safe`: the fail-closed behavior against a live AWS API. Block and safe verdicts,
which need usage evidence, are proven offline by the trap corpus under
`tests/fixtures/`, and are exercised against real Flow Logs on live AWS.
