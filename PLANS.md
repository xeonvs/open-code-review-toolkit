# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit site launch and release notification

Status: active

Release classification: no-release for the toolkit workflow; no runtime or published toolkit contract changes.
Plan Origin: plan_mode_approved

#### Goal and requested scope

Finish the English promotional site, add an automatically updated latest-release section and the approved CRO cat Easter egg, and prepare GitHub-to-Cloudflare delivery. The first public Cloudflare deployment requires a separate final owner approval. The site repository is `xeonvs/ocr-toolkit-site`; this public plan contains no private report source, raw telemetry, credentials, or local private paths.

#### Requirement traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Clear, edited site copy with only approved rounded operational shares | WQ-01, WQ-05 | done |
| REQ-002 | Latest stable GitHub Release shown compactly with full expandable notes and event-driven refresh | WQ-01, WQ-02, WQ-05 | done |
| REQ-003 | Approved cat frames and separate knock sound as an intentional, accessible Easter egg | WQ-01, WQ-05 | done |
| REQ-004 | Merge-triggered CI/CD with checked source and restricted credentials; no first deployment before approval | WQ-02, WQ-03, WQ-06 | in_progress |
| REQ-005 | Pre-commit Astra High review, Codex Security, Gitleaks, and first-user browser QA | WQ-04, WQ-05 | done |
| REQ-006 | Keep commit history free of temporary QA artifacts and private material; clean task-owned files before delivery | WQ-04, WQ-06 | in_progress |
| REQ-007 | Keep agent instructions and affected project documentation clear and consistent with implementation | WQ-04 | done |

#### Constraints and decisions

- Preserve the existing site palette and show a local visual example before finalizing. Use Workers.dev first; no custom domain in this delivery.
- The latest release is read at build time from GitHub Releases. Production builds fail when it is unavailable or does not match an event-provided release tag. No scheduled polling.
- Three taps on the separate brand symbol trigger the cat. The home link keeps normal behavior. Audio starts only from that gesture; reduced-motion visitors see a static cat without sound.
- Keep the site repository private without branch protection, as chosen by the owner. Direct pushes to `main` are operationally discouraged; the deployment workflow triggers on merged PRs and verified release dispatches only.
- `SITE_DEPLOY_ENABLED` remains unset or false through code merge and credential setup. The owner separately approved first publication after all checks and GitHub delivery; set it true only when those gates pass, then perform the first dispatch.
- Do not publish private report source, raw counts, original production paths, or other private material. The public page uses only rounded shares with a concise limitation.

#### Inputs and baseline

- Current toolkit GitHub Release and its immutable receipt are the release-content source; `.github/workflows/release.yml` owns publication.
- The site is an Astro static build targeting Cloudflare Workers Static Assets. Existing site CI checks its build, public paths, and secrets.
- Approved promo footage provides transparent cat frames and separate licensed sound material; only optimized derivatives enter the site repository.

#### Current work queue

| Queue | Work and exit evidence | Status |
| --- | --- | --- |
| WQ-01 | Edit site content, release rendering, cat interaction, and optimized media; local Astro check/build and source test pass | done |
| WQ-02 | Add secure post-release toolkit dispatch and site deploy workflows; validate YAML and exact trigger gates | done |
| WQ-03 | Store restricted Cloudflare account credentials and prepare a site-only GitHub dispatch credential; verify no deploy activation | done |
| WQ-04 | Review complete diff with separate Astra High reviewer and Codex Security, repair findings, run final mechanical gates | done |
| WQ-05 | Inspect desktop/mobile render and run sequential first-user browser passes, repair issues, then fresh passes; retain working screenshots outside repositories | done |
| WQ-06 | Commit, push, and reconcile CI and PR state; after separate owner approval activate and verify first Cloudflare publication | in_progress |

#### Verification and latest results

- Site `astro check`, latest-release parser tests, strict build against the current stable tag, and scoped `git diff --check` passed on the current worktree. An expected-tag mismatch fails the build.
- Four first-user browser personas ran in sequence; after fixes, four fresh personas repeated the path. On-site command copy took two actions for the impatient, mobile, and resilience personas; completing a real review still requires local toolkit setup. The 375 px mobile pass found no clipping or horizontal overflow. Browser automation could not establish video playback progress in its headless environment.
- A separate Astra High pre-commit review found and resolved skipped-release notification and recovery-receipt cases, and ensured the release parser tests run in both site CI and deployment validation. No remaining actionable findings were reported.
- Codex Security diff scans of both repositories completed with full changed-surface coverage and no reportable findings. Staged Gitleaks and the site public-path scanner passed; YAML syntax checks passed. `actionlint` was unavailable locally after a network timeout, so GitHub Actions execution remains the live workflow gate.
- Optimized cat assets were derived from the accepted gesture: transparent animation 2.667 seconds, separate 2.667-second audio, and a static PNG. Public media contains no source frame sequence.
- Toolkit sidecar YAML/Bash and current release/receipt conditions, site `actionlint`, public-path scanner, local Gitleaks, and Wrangler dry run have passed scoped checks. Aggregate review and final changed-state checks remain.
- Full reachable history in both repositories passed Gitleaks; historical object paths and text searches found no task QA artifacts or private report path. No history rewrite is indicated. Agent instruction contract is valid, affected Markdown links check cleanly, and the engineering index no longer has a duplicate nested archive entry. The workflow audit still flags four ordinary references to tokens/credentials as possible prompt injection; bounded inspection found no instruction override or secret disclosure request.
- Cloudflare deployment token and account ID are stored in the site Actions secrets; token API verification succeeded. The owner added the narrow GitHub cross-repository dispatch secret, and its presence was verified without reading the value. `SITE_DEPLOY_ENABLED` remains unset until publication setup.

#### Risks, recovery, and resume point

- GitHub Free does not enforce protection on the private site repository. Deployment verifies the current main tip and reruns gates but cannot prevent a maintainer from pushing directly.
- A new release event uses the owner-provided cross-repository credential scoped to the site Actions workflow. Rotate or revoke it if future GitHub authorization checks fail; do not substitute the existing broad local GitHub token.
- Failed release fetching or tag mismatch must stop production deployment. If a deployment fails after first approval, preserve the previous Worker version and use Cloudflare rollback or a verified prior site build.
- Resume at WQ-06: commit and merge the reviewed changes, verify GitHub checks, then activate Cloudflare and perform the first publication under the owner's separate approval recorded in this conversation.

#### Plan fidelity and closure

- [x] Requested outcomes, exclusions, decisions, sources, queue, and verification mapped above.
- [x] First unfinished safe action and separate publication gate recorded.
- [ ] Reconcile final source, CI checks, review findings, and publication state before closure.
- [ ] Close only when all implementation and publication requirements are actually met; an approved preview or green local build is not a live-site receipt.

Post-close delivery: user receives the verified Workers.dev URL and release-refresh evidence after separate publication approval. Until then, report the ready code, secrets, checks, and precise approval gate without claiming deployment.
