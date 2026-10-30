# Agent Instructions

instruction_contract_version: 3

Use this file as the short repository map and route table for Open Code Review Toolkit maintenance. It points to canonical owners; it does not duplicate their rules.

## Repository Map

- `src/ocr_toolkit/` - runtime package and the `ocr-ci` command.
- `src/ocr_toolkit/context/dlp/` - shared DLP facade, admission and bounded text interpretation.
- `src/ocr_toolkit/dlp_audit/` - local-only private corpus diagnosis and replay.
- `src/ocr_toolkit/evidence/text_metadata.py` and `src/ocr_toolkit/diagrams/sources.py` - bounded Git text facts and optional diagram-reference acquisition.
- `tests/` - regression, contract, and synthetic integration tests.
- `examples/gitlab/` - public synthetic GitLab CI examples.
- `docs/` - user, security, development, strategy, and release documentation.
- `.github/workflows/` - pinned CI, security, build, and release automation.

## Sources Of Truth

- `PLANS.md` - active or blocked repository work and its release classification.
- `docs/engineering/toolkit_strategy.md` and `ROADMAP.md` - durable direction, evidence architecture, and outcome state.
- `docs/engineering/project_principles.md` - cross-cutting invariants; `docs/review-context.md` owns current context behavior and `docs/engineering/governed_federation_contracts.md` owns federation. The M5 foundation is archived in `docs/engineering/execution_history/review_context_design_checkpoint.md`.
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

<!-- ew:route id="review-context" triggers="src/ocr_toolkit/context/**|docs/review-context.md|review context admission|context publication" owners="docs/review-context.md|docs/engineering/project_principles.md" guards="manual_review:compare context acquisition admission store and publication with the current contract|test:scripts/quality.sh check" -->
| `review-context` | Review-context admission or publication | Current bounded-context contract and project principles | Context lifecycle comparison and quality checks |

<!-- ew:route id="dlp" triggers="src/ocr_toolkit/context/dlp/**|src/ocr_toolkit/common/redaction.py|src/ocr_toolkit/dlp_audit/**|DLP interpretation|DLP corpus audit" owners="docs/security.md|docs/dlp-audit.md|docs/development.md|docs/engineering/project_principles.md" guards="manual_review:compare material representations source proof sink authority private replay and resource bounds|test:scripts/quality.sh check|lint:scripts/gitleaks.sh" -->
| `dlp` | Shared DLP interpretation, redaction or local corpus audit | Security, audit and development contracts | Material/sink comparison, replay and bounded-work checks |

<!-- ew:route id="federation" triggers="src/ocr_toolkit/federation/**|docs/engineering/governed_federation_contracts.md|federation admission|external MCP gateway" owners="docs/engineering/governed_federation_contracts.md|docs/engineering/project_principles.md" guards="manual_review:compare registry admission gateway DLP and receipt changes with the federation contract|test:scripts/quality.sh check" -->
| `federation` | Governed external-tool admission or gateway | Federation contract and project principles | Gateway contract comparison and quality checks |

<!-- ew:route id="long-running-execution" triggers="long-running commands|builds|tests|local processes|polling|terminal sessions" owners="docs/engineering/project_principles.md|docs/development.md" guards="manual_review:verify process completion exit status bounded output and task-owned cleanup" -->
| `long-running-execution` | Long-running command, waiter, or process cleanup | Project principles and development procedures | Completion evidence and bounded output |

<!-- ew:route id="local-ocr-review" triggers="local OCR review|ocr-ci review --local|review artifacts" owners="docs/local.md|docs/development.md" guards="manual_review:verify selected auth mode qualified executable native model reachability supported local flags physical private paths terminal status report and admitted findings|manual_review:inspect failed auxiliary reads for material review gaps" -->
| `local-ocr-review` | Authorized real local OCR review | Local review and development procedures | Mode, binary, flags, private paths, result, findings and failed reads |

<!-- ew:route id="workflow-instructions" triggers="AGENTS.md|docs/engineering/project_principles.md|docs/codex/AGENT_EXECUTION_PITFALLS.md" owners="skill://engineering-workflow/references/instruction_lifecycle.md|docs/engineering/project_principles.md" guards="lint:instruction-contract" -->
| `workflow-instructions` | Instruction owner, route, or incident change | Installed instruction lifecycle and project principles | `lint:instruction-contract` |

<!-- ew:route id="agent-configuration" triggers=".codex/config.toml|.codex/agents/**|docs/codex/ENGINEERING_WORKFLOW_STATE.yaml" owners="skill://engineering-workflow/references/agent_orchestration.md|skill://engineering-workflow/references/instruction_lifecycle.md" guards="lint:instruction-contract|manual_review:inspect agent configuration and instruction semantics against the installed owners" -->
| `agent-configuration` | Agent settings, role instructions, or workflow state | Installed agent orchestration and instruction lifecycle | Contract lint and semantic configuration review |

<!-- ew:route id="release-lifecycle" triggers="docs/release.md|.github/workflows/release.yml|release-required change|release-deferred change|stable publication|release authorization|stable delivery|release closure" owners="docs/release.md" guards="release_gate:.github/workflows/release.yml|manual_review:reconcile current archive and external receipts" -->
| `release-lifecycle` | Release authorization, stable delivery, or closure | Release guide | Protected release gate and external receipt review |

<!-- ew:route id="development-validation" triggers="docs/development.md|status-bearing documents|parser changes|provider changes|subprocess changes" owners="docs/development.md" guards="manual_review:compare status documents with current implementation|manual_review:map changed producer-consumer handoffs and failure cleanup|test:scripts/quality.sh check" -->
| `development-validation` | Status or changed-boundary validation | Development guide | Status and handoff review; Python quality matrix |

<!-- ew:route id="dependency-audit" triggers="pre-push|pyproject.toml|uv.lock|.github/workflows/security.yml|scripts/dependency-audit.sh" owners="docs/development.md" guards="test:scripts/dependency-audit.sh" -->
| `dependency-audit` | Every push and dependency or audit-workflow change | Development guide | Shared local and hosted dependency audit |

<!-- ew:route id="trust-boundary" triggers="src/ocr_toolkit/**|tests/**|public fixtures|release artifacts" owners="docs/engineering/project_principles.md" guards="test:scripts/quality.sh check|lint:scripts/gitleaks.sh|manual_review:verify clean built artifacts and real external boundary evidence" -->
| `trust-boundary` | Runtime, test, or public-source trust boundary | Project principles | Behavioral tests, secret scan, and installed integration review |
