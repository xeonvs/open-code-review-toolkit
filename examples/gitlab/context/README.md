# Bounded-context recipes

These files contain no live hostname or credential. Copy exactly one policy to `.opencodereview/review-context-policy.json` on the protected target branch:

- `policy-discussions.json` selects generic discussions and verified remediation threads without requiring an external adapter.
- `policy-adapters.json` adds a required `tracker` issue source and is paired with exactly one operator-side adapter JSON supplied through `OCR_REVIEW_CONTEXT_ADAPTERS_JSON`.
- `policy-ci-outcomes.json` selects exact same-revision GitLab checks and binds each check to path prefixes declared by protected policy v3.

- `adapters-stdio.json` shows an operator-managed local proxy. Replace the example absolute command and provide `TRACKER_CONTEXT_TOKEN` in the runner environment.
- `adapters-remote.json` shows the same tracker adapter behind HTTPS. Replace the `.invalid` endpoint and provide `TRACKER_CONTEXT_AUTHORIZATION` in the runner environment.

The protected policy can narrow these allowlists but cannot add a command, endpoint, tenant, resource class, or credential. Both proxy variants must implement `ocr.context-adapter-request/v1` and `ocr.context-adapter-response/v1`, including object-level authorization in the atomic `authorize_and_resolve` operation. See [Bounded review context](../../../docs/review-context.md) for the exact contract and deployment boundary.

For ordinary conversations only, remove `remediation_threads` from `policy-discussions.json`. For verified OCR-rooted remediation history only, remove `forge_discussions`. Keep both for both sources; the toolkit prevents a verified remediation root from appearing twice. See [Choosing a discussion policy](../../../docs/review-context.md#choosing-a-discussion-policy) before changing `required`, account classes, resolved/outdated selection, or approval posture.

CI outcomes are execution context, not clean-review or approval authority. Keep `required: false` unless losing the selected provider snapshot must block approval, and list only stable job names whose declared prefixes accurately describe what the job executes. The toolkit never downloads logs or artifacts.
