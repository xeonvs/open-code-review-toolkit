# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### v0.11.1 PyPI index recovery (no-release)

The stable files are published on PyPI, but its Simple Index still omits
v0.11.1, blocking the release verifier. Add a one-version recovery path using
the PyPI version JSON API only when dispatched from protected main for the
original reviewed release. Compare exactly the reviewed wheel and sdist
hashes, verify their provenance, and run the existing installed-artifact matrix
before the unchanged GitHub Release job. Fail closed on missing, extra, or
conflicting registry data. Merge this policy-only change through a protected
PR, then dispatch the original release identity and reconcile external delivery.
