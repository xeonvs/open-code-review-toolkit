# Bounded-context recipes

These files contain no live hostname or credential. Copy exactly one policy to `.opencodereview/review-context-policy.json` on the protected target branch:

- `policy-discussions.json` selects generic discussions and verified remediation threads with current policy v4.
- `policy-ci-outcomes.json` selects exact same-revision GitLab checks and binds each check to path prefixes declared by protected policy v3.

Current policy v4 does not accept `references`. Legacy v1-v3 references are parsed
but never executed: optional references are skipped, and required references make
the run comment-only. Configure any reviewed external tools separately through
the governed registry-v2 example in
[`modes/direct-mcp.gitlab-ci.yml`](../modes/direct-mcp.gitlab-ci.yml). Do not copy
old adapter commands or endpoints into a policy. See
[Bounded review context](../../../docs/review-context.md) for migration behavior.

For ordinary conversations only, remove `remediation_threads` from `policy-discussions.json`. For verified OCR-rooted remediation history only, remove `forge_discussions`. Keep both for both sources; the toolkit prevents a verified remediation root from appearing twice. See [Choosing a discussion policy](../../../docs/review-context.md#choosing-a-discussion-policy) before changing `required`, account classes, resolved/outdated selection, or approval posture.

CI outcomes are execution context, not clean-review or approval authority. Keep `required: false` unless losing the selected provider snapshot must block approval, and list only stable job names whose declared prefixes accurately describe what the job executes. The toolkit never downloads logs or artifacts.
