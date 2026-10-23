# Bounded-context recipes

These files contain no live hostname or credential. Copy exactly one policy to
`.opencodereview/review-context-policy.json` on the branch that will provide
protected policy authority P. With a protected actual MR target, P is that
target. With the default `auto` mode and an unprotected target, P is the same
project's authenticated protected default branch. The review still covers the
current MR's B..H delta; copying this file onto source H or unprotected target
T does not grant policy authority. Explicit `unprotected` remains the older
limited comment-only mode and does not acquire enriched policy context:

- `policy-discussions.json` selects generic discussions and verified remediation threads with current policy v4.
- `policy-ci-outcomes.json` selects exact same-revision GitLab checks and binds each check to path prefixes declared by current protected policy v4.

Current policy v4 does not accept `references`. Legacy v1-v3 references are parsed
but never executed: optional references are skipped, and required references make
the run comment-only. Configure any reviewed external tools separately through
the governed registry-v2 example in
[`modes/direct-mcp.gitlab-ci.yml`](../modes/direct-mcp.gitlab-ci.yml). Do not copy
old adapter commands or endpoints into a policy. See
[Bounded review context](../../../docs/review-context.md) for migration behavior.

For ordinary conversations only, remove `remediation_threads` from `policy-discussions.json`. For verified OCR-rooted remediation history only, remove `forge_discussions`. Keep both for both sources; the toolkit prevents a verified remediation root from appearing twice. See [Protected policy v4](../../../docs/review-context.md#protected-policy-v4) before changing `required`, account classes, resolved/outdated selection, or approval posture.

CI outcomes are execution context, not clean-review or approval authority. Keep `required: false` unless losing the selected provider snapshot must block approval, and list only stable job names whose declared prefixes accurately describe what the job executes. The toolkit never downloads logs or artifacts.
The source revision H must match the CI result; a merged-results commit or a
pipeline for another revision cannot prove H. An unprotected actual target is
comment-only even when a protected P admits this context; a prior bot approval
is not automatically removed by the current review.
