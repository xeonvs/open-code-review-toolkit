# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Community conduct policy and example-version consistency

- **Status:** active
- **Release classification:** `no-release`; governance documentation and correction of the public example do not authorize stable artifact publication. The example correction receives a Towncrier fragment for the next ordinary release.
- **Objective:** establish one public Code of Conduct with a confidential enforcement route, link it from contributor and project entry points, and complete the already-started toolkit-version update in the synthetic GitLab example without changing runtime behavior.
- **Owners and boundaries:** `CODE_OF_CONDUCT.md` owns community behavior, scope, reporting, privacy, and enforcement. `CONTRIBUTING.md` links contributors to that policy; `README.md` exposes it from the public documentation index; `docs/engineering/project_principles.md` records documentation ownership without duplicating conduct rules. The GitLab example remains synthetic documentation, while `tests/test_integration_contracts.py` protects its internally consistent release-derived wheel references.
- **Trust and privacy:** conduct reports use the repository's available private maintainer channel and must not be filed as public issues. Public files contain no private contacts or provider material. The example uses only public immutable release coordinates and does not introduce credentials.
- **Implementation slices:**
  1. [x] Complete the `0.6.0` example pin by deriving the checksum URL and wheel install path from `OCR_TOOLKIT_VERSION`; add a regression assertion and documentation changelog fragment.
  2. [x] Add Contributor Covenant 2.1 as `CODE_OF_CONDUCT.md`, adapt only the confidential reporting method, and add concise links/ownership entries in contributor and project documentation.
- **Validation:** self-review the complete diff before each commit; run the focused integration/documentation tests, `git diff --check`, and `scripts/quality.sh check`; confirm the conduct document has no placeholder contact method and the example has no hard-coded toolkit wheel/release version outside its single variable.
- **Checkpoint:** the example consistency test passes and self-review confirms that the checksum URL, requirement, downloaded filename, digest check, and installation now derive from one version variable.
- **Checkpoint:** Contributor Covenant 2.1 is the canonical conduct owner; README, contribution guidance, package metadata, CODEOWNERS, and the issue chooser point to it without copying its behavioral rules. The confidential route is distinct in purpose from vulnerability reporting and no placeholder contact remains.
- **Closure:** leave the branch ready for one protected documentation PR, with no push until the coherent work and validation are complete. Reset this file to its empty template in the final local commit because no stable release archive is required.
