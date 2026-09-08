# SSM Automation adapter

The gate runs as a pre-step in an SSM Automation document. `aws:invokeLambdaFunction`
calls the Inflight handler with the proposed change, and `aws:branch` reads `allow`.
When `allow` is false the automation stops before the remediation step. This path is
validated on live AWS, because LocalStack does not execute Automation runbooks.

Sketch:

    schemaVersion: '0.3'
    mainSteps:
      - name: preflight
        action: aws:invokeLambdaFunction
        inputs:
          FunctionName: inflight-gate
          Payload: '{"snapshot": "{{ SnapshotRef }}", "change": {{ Change }} }'
      - name: branchOnVerdict
        action: aws:branch
        inputs:
          Choices:
            - NextStep: applyRemediation
              Variable: '{{ preflight.Payload.allow }}'
              BooleanEquals: true
          Default: stop
      - name: applyRemediation
        action: aws:runCommand
        inputs: {}
      - name: stop
        action: aws:sleep
        inputs: {Duration: PT1S}
