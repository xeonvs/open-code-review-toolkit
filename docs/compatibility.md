# Open Code Review compatibility

The versioned support contract lives in [`compatibility/ocr-support.json`](../compatibility/ocr-support.json). It records the recommended OCR version, every tested or observed release, exact upstream asset digests, and a SHA-256 link to normalized machine evidence. The toolkit package never downloads OCR; deployments keep using an explicitly pinned, checksum-verified binary.

## Qualification lanes

The scheduled **OCR compatibility** workflow discovers stable upstream releases newer than the manifest monitoring floor. Drafts, prereleases, non-semantic tags, unexpected asset sets, oversized metadata or downloads, redirects outside the reviewed GitHub origins, and checksum disagreement fail closed. Every binary digest must agree with both GitHub release metadata and the upstream `sha256sum.txt`.

Candidate execution uses the verified Linux amd64 binary on an Ubuntu runner. The harness checks the reported version, the CLI flags consumed by the GitLab integration, range preview behavior, an actual JSON review through a deterministic local gateway, and the additive JSON fields consumed by posting. Evidence permits unknown new fields but requires the fields the toolkit reads.

Candidates then take one of two lanes:

- `automatic-safe`: only a newer patch in the already-tested major/minor line, with every probe passing and maintenance-only release notes containing no material compatibility signal. The workflow prepares an exact compatibility patch covering the manifest, evidence, runtime preflight version, GitLab example version/checksum, and public version references. It never writes directly to `main`.
- `human-review-required`: every minor/major release, skipped or non-increasing patch, changed or failed contract, material/security/deprecation/config/provider signal, or ambiguous release notes. The workflow creates or refreshes one qualification issue with machine evidence and a human checklist.

An automatic-safe result is not an automatic stable release. It must still pass a normal protected compatibility PR and a separate signed stable-release PR. If a dedicated OCR update bot credential is not configured, the workflow publishes the exact patch as an artifact and records the resume action in the issue; the default `GITHUB_TOKEN` is intentionally not used to create a PR that would fail to trigger the full protected workflow set.

## Promotion and rollback

Promotion changes `recommended_version`, advances `monitoring_floor`, adds the tested release and evidence, and updates every durable version/checksum pin. Never edit only one copy. Human-qualified candidates must record the compatibility conclusion and release-note impact. Automatic-safe candidates retain the same protected review boundary even though the patch itself is mechanical.

Rollback selects a previously tested manifest entry, restores its runtime/example/documentation pins, and travels through the same release-required path. Do not delete historical evidence: it explains the prior support decision and lets future qualification distinguish a rollback from an unseen release.
