# Acceptance evidence

The capture-once MB01UD workflow passed on 2026-09-10. The translated Go algorithm is unchanged; this revision separates recorded legacy expectations from routine candidate verification.

## Results

| Gate | Result |
| --- | --- |
| Capture | 1,405 calls recorded from the pinned Fortran routine; no candidate execution |
| Offline Go verification | 1,405/1,405 passed |
| Explicit legacy audit | 1,405/1,405 passed |
| Single-call replay | asymmetric-LT passed; unknown call IDs rejected |
| Offline infrastructure checks | 13 passed |
| Native capture/audit check | 1 passed, including non-default seed preservation and overwrite refusal |
| Compiled negative controls | Omitted subdiagonal, ignored transpose, and input corruption all rejected |
| Go checks | Tests and vet passed |
| Skill validation | Bundled skill-creator metadata validator passed |
| Clean-copy verification | Full make verify passed without a reference checkout; FC and OpenBLAS flags unusable, CGO disabled, module network disabled |

The baseline has 605 deterministic cases plus 400 generated calls from each of seeds 20260910 and 20260911: **1,405 distinct calls**. Each trace identifies its scenario, harness caller, MB01UD callee, and invocation. No application caller instrumentation or stateful integration scenario is claimed.

Maximum numerical error/bound ratio in Go verification: `0.015473457034228295`. The legacy audit ratio was `0`. Comparison bounds and accepted domains are specified in [the contract](mb01ud-contract.md).

## Baseline identity

The checked-in [manifest](../oracle/baselines/mb01ud-v1/manifest.json) is the authoritative capture record; the adjacent compressed JSONL contains full inputs and expected observations.

- Calls SHA-256: `ece599f3cf93e26c3f5892b314a567a296835638160a22e486963c4afb84239d`.
- SLICOT revision: `4a752c35ab540ce6291be8590dd7ed47086fe4ff`.
- Capture: GNU Fortran (Homebrew GCC 15.2.0_1) 15.2.0; OpenBLAS 0.3.33; macOS arm64; one numerical-library thread.
- Candidate: go version go1.26.4 darwin/arm64; Gonum v0.17.0 native Go BLAS.

The manifest retains original capture source/library/binary hashes and compiler flags. Temporary build paths describe the capture invocation, not required permanent paths. Verification reports identify the baseline hashes and original seeds separately from current candidate build metadata. Reports can be regenerated with `make verify` and `make audit` under ignored `artifacts/`; binaries use automatically removed temporary directories.

## Refinement and cleanup

The former report-based replay rebuilt both implementations. It has been replaced by explicit `capture`, `verify`, and `audit` operations. Only capture creates expected results; existing baseline directories cannot be overwritten. Verification rejects missing/corrupt data, unsupported policies, empty/duplicate calls, invalid observations, and output paths inside the baseline.

The persistent regression for the previously discovered replay seed bug now checks that offline replay preserves the manifest's original seeds and identity. Integrity and negative-control checks operate on stored expected results. Native-toolchain checks are separate from everyday verification.

Removed superseded report/build artifacts, completed execution journals, the redundant acceptance-summary snapshot, and the two repeated live comparison campaigns. Retained the pinned reference, capture generator, curated edge cases, typed Go API checks, and numerical comparison policy because they support baseline extension and migration correctness.

This is a same-agent refinement trial with executable acceptance checks. It covers one synthetic harness-driven routine, not an entire control system, production workload, or performance claim. Output aliasing and unsupported nonfinite/overflowing computations remain outside the [declared domain](mb01ud-contract.md). Read the [playbook](../.agents/skills/oracle-migration/references/playbook.md) for the broader caller-capture and scenario-replay method and its published precedents.
