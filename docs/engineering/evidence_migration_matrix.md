# Evidence Migration Matrix

This matrix is the history-backed removal gate for the pre-0.4 repository-context pipeline. It compares the implementation at the M1 merge-base (`4ccd46c`) with the typed evidence architecture. A row is complete only when synthetic tests prove the typed fact, trust/ref behavior, bounds, diagnostics, and MCP visibility; similar Markdown is not parity evidence.

| Legacy contract | Typed destination | Migration requirement | Status |
| --- | --- | --- | --- |
| Review language and trust instructions | compact bootstrap | English remains the default; an explicit language is a presentation setting; repository content remains untrusted | implemented, E2E pending |
| Base/head identity and changed-file discovery, including local/GitLab fallbacks | snapshots, `repository.file`, file deltas | one immutable ref pair shared with OCR; rename/deletion/symlink/submodule/shallow failures explicit | implemented |
| Changed files grouped by review category | `repository.change_category` | deterministic multi-category records derived from the immutable changed-path set, including deleted paths from the base tree | implemented |
| Python declarations, locks, requirements and runtime constraints | `dependency.declared`, `dependency.locked`, `runtime.declared` | preserve declaration versus resolved scope, source path, absence and parse diagnostics | partial |
| Go module/runtime declarations and sums | dependency/runtime facts | preserve module, requirement, toolchain, replace and locked checksum semantics | partial |
| Composer declarations, platform/runtime constraints and lock packages | dependency/runtime facts | preserve production/dev scope, PHP runtime constraints and locked versions | partial |
| JavaScript manifests, engines and lock packages | dependency/runtime facts | preserve production/dev scope, package-manager/runtime constraints and locked versions | partial |
| Ansible Galaxy requirements | dependency facts | preserve role/collection kind, source path, declared version and missing version | partial |
| Ansible core manifests, role metadata/defaults, playbook entrypoints, inventories and groups | `ansible.topology` | bounded immutable topology facts with explicit parser limitations | pending |
| Container/CI images and application/infrastructure pins | `container.image`, `ci.image`, `application.version` | CI/container image identities now separate source/component name from version so an update is `changed`; application/infrastructure pins remain pending | partial |
| Detected dependency/runtime manifest paths | `repository.manifest` | preserve ecosystem and immutable source path independently of detailed dependency values | implemented |
| Project guidance and accepted decisions | guidance/decision facts | base may guide; changed head cannot self-authorize; failures and truncation are diagnostics | implemented, parity expansion pending |
| GitLab project/pipeline/MR identifiers | `review.ci_context` | bounded allowlisted CI metadata only; no tokens, arbitrary environment, or forge coupling in core collectors | pending |
| Local installed tool versions | coverage diagnostic | deliberately removed: runner state is not immutable reviewed-repository evidence; declared versions remain available | pending |
| Section byte/character planning and safe Markdown | bootstrap planner plus MCP budgets | bootstrap remains below OCR hard limit; details stay bounded/paginated in MCP; truncation explicit | implemented |
| Legacy collection warnings and failures | `diagnostic.coverage` plus bounded preflight logs | no production collector writes ad-hoc stdout/stderr; the common plan renders safe lifecycle diagnostics | partial: legacy oracle isolated; typed diagnostics expansion pending |
| Per-file Git subprocess reads | bounded immutable batch reads | preflight size-checks each blob and the aggregate payload, omit individual over-limit candidates with explicit diagnostics, then read accepted candidates with a fixed process count per ref | implemented |

BL-006 and legacy removal remain blocked until every `pending` or `partial` row is either proven complete or changed to a documented, tested intentional contract change. BL-008 and BL-013 remain future work: M1 does not perform network dependency resolution or provider-specific external-reference enrichment.
