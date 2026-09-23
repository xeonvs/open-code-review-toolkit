# Agent Instructions

instruction_contract_version: 3

Use this file as the short repository map and route table for Open Code Review Toolkit maintenance. It points to canonical owners; it does not duplicate their rules.

## Repository Map

- `src/ocr_toolkit/` - runtime package and the `ocr-ci` command.
- `tests/` - regression, contract, and synthetic integration tests.
- `examples/gitlab/` - public synthetic GitLab CI examples.
- `docs/` - user, security, development, strategy, and release documentation.
- `.github/workflows/` - pinned CI, security, build, and release automation.

## Sources Of Truth

- `PLANS.md` - active or blocked repository work and its release classification.
- `docs/engineering/toolkit_strategy.md` and `ROADMAP.md` - durable direction and outcome state.
- `docs/engineering/project_principles.md` - cross-cutting engineering invariants and ownership boundaries; `docs/engineering/m5_context_contracts.md` owns the current context and evidence contracts.
- `docs/review-decision-flow.md` - canonical detailed Mermaid map for review, diagnostics, receipts, DLP, publication, and later-action decisions; keep it synchronized with runtime and public contracts.
- `docs/development.md` - implementation workflow, boundary checklists, local validation, and [OCR qualification maintenance](docs/development.md#maintaining-ocr-qualification).
- `docs/release.md` - release classification, authorization, publication, and archival lifecycle.
- `docs/codex/TASKS_BACKLOG.md` - inactive work with activation conditions.
- `docs/codex/AGENT_EXECUTION_PITFALLS.md` - incident catalogue for diagnosis, not an instruction source.
- `docs/configuration.md`, `docs/operations.md`, `docs/gitlab.md`, and `docs/security.md` - public product and operator contracts; `SECURITY.md` owns vulnerability reporting.
- `docs/engineering/execution_history/README.md` - archived release-plan index and historical receipts.

## Task Routes

Read the matching owners and run their applicable guards. The general repository route applies alongside a more specific route; a shared owner or unchanged-state guard needs only one current read or check.

<!-- ew:route id="repository-change" triggers="**" owners="docs/engineering/project_principles.md|docs/development.md" guards="manual_review:inspect the scoped final diff and applicable repository checks" -->
| `repository-change` | Every repository change | Project principles and development procedures | Scoped diff review and applicable checks |

<!-- ew:route id="planning" triggers="PLANS.md|docs/codex/TASKS_BACKLOG.md|plan closure|release classification" owners="docs/development.md|docs/release.md|skill://engineering-workflow/references/planning_and_backlog.md" guards="manual_review:reconcile the active plan classification status and exact resume point" -->
| `planning` | Active plan, backlog, classification, or closure | Development and release owners with installed planning reference | Plan and status reconciliation |

<!-- ew:route id="review-flow" triggers="docs/review-decision-flow.md|review execution|publication branch" owners="docs/review-decision-flow.md|docs/engineering/project_principles.md" guards="manual_review:compare changed execution branches with the decision flow" -->
| `review-flow` | Review execution or publication branch | Review decision flow and project principles | Branch and diagram comparison |

<!-- ew:route id="long-running-execution" triggers="long-running commands|builds|tests|local processes|polling|terminal sessions" owners="docs/engineering/project_principles.md|docs/development.md" guards="manual_review:verify process completion exit status bounded output and task-owned cleanup" -->
| `long-running-execution` | Long-running command, waiter, or process cleanup | Project principles and development procedures | Completion evidence and bounded output |

<!-- ew:route id="workflow-instructions" triggers="AGENTS.md|docs/engineering/project_principles.md|docs/codex/AGENT_EXECUTION_PITFALLS.md" owners="skill://engineering-workflow/references/instruction_lifecycle.md|docs/engineering/project_principles.md" guards="lint:instruction-contract" -->
| `workflow-instructions` | Instruction owner, route, or incident change | Installed instruction lifecycle and project principles | `lint:instruction-contract` |

<!-- ew:route id="release-lifecycle" triggers="docs/release.md|.github/workflows/release.yml|release-required change|release-deferred change|stable publication|release authorization|stable delivery|release closure" owners="docs/release.md" guards="release_gate:.github/workflows/release.yml|manual_review:reconcile current archive and external receipts" -->
| `release-lifecycle` | Release authorization, stable delivery, or closure | Release guide | Protected release gate and external receipt review |

<!-- ew:route id="development-validation" triggers="docs/development.md|status-bearing documents|parser changes|provider changes|subprocess changes" owners="docs/development.md" guards="manual_review:compare status documents with current implementation|test:scripts/quality.sh check" -->
| `development-validation` | Status or changed-boundary validation | Development guide | Status review and Python quality matrix |

<!-- ew:route id="trust-boundary" triggers="src/ocr_toolkit/**|tests/**|public fixtures|release artifacts" owners="docs/engineering/project_principles.md" guards="test:scripts/quality.sh check|lint:scripts/gitleaks.sh|manual_review:verify clean built artifacts and real external boundary evidence" -->
| `trust-boundary` | Runtime, test, or public-source trust boundary | Project principles | Behavioral tests, secret scan, and installed integration review |
