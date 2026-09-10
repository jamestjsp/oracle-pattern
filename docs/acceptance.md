# Acceptance evidence

The MB01UD pilot and repository-local oracle migration skill passed the declared acceptance gates on 2026-09-10. This is a same-agent implementation/refinement trial backed by independent executable comparisons, not an independent-agent skill evaluation.

## Results

| Gate | Observed result |
| --- | --- |
| Initial side-by-side trial | 655/655 cases passed, including 50 generated cases |
| Final campaign, seed 20260910 | 1,005/1,005 passed; 400 generated cases |
| Fresh seed 20260911 | 1,005/1,005 passed; 400 generated cases |
| Stored asymmetric-LT replay | Passed against rebuilt executables |
| Python infrastructure checks | 9 passed, including real CLI replay and unknown-case rejection |
| Compiled candidate mutations | All 3 rejected: omit subdiagonal, ignore transpose, corrupt A |
| Go checks | `go test ./...`, `go test -race ./...`, and `go vet ./...` passed |
| Skill metadata | Bundled skill-creator validator passed |
| Complete documented procedure | `make verify` passed |

Each final campaign contains the same 605 deterministic cases: 8 curated cases, 576 combinations of side/transpose/shape/alpha, and 21 safe invalid-argument probes. Across the two campaigns there are 1,405 distinct cases, not 2,010 distinct cases. The curated matrices include asymmetric products, cancellation, and zero subdiagonals. NaNs poison ignored storage and alpha=0 inputs. Both adapters are also checked against hand-calculated results.

The maximum observed absolute-error/comparison-bound ratio was `0.015473457034228295` for the primary campaign and `0.015355312898164861` for the fresh seed. Both are below 1. The bound is specified in [the contract](mb01ud-contract.md); these observations do not establish a universal error theorem.

## Recorded environment

- SLICOT commit `4a752c35ab540ce6291be8590dd7ed47086fe4ff`, unmodified.
- macOS 26.6.2, arm64; Go 1.26.4; Gonum v0.17.0 native Go BLAS.
- GNU Fortran 15.2.0 (Homebrew GCC 15.2.0_1).
- OpenBLAS 0.3.33, LP64; one OpenBLAS/OMP thread.
- Reference flags `-O2 -fcheck=all -fno-fast-math`; candidate built with `-trimpath`.

[Machine-readable evidence](acceptance-summary.json) records corpus and source hashes, effective Go settings, linked-library hashes, and gate outcomes without requiring a large report in Git. Full input/output/provenance reports are generated in `artifacts/acceptance.json`, `artifacts/fresh-seed.json`, and `artifacts/replay.json`. Those local reports record the build-time Git state and hashes; source hashes identify the tested working tree even when a run precedes its commit.

## Trial-driven refinements

| Evidence from the trial | Resulting refinement | Demonstration |
| --- | --- | --- |
| Native OpenBLAS was installed but pkg-config was unavailable | Runner detects existing Homebrew OpenBLAS and records the actual linked libraries | The compiled Fortran oracle ran successfully on this machine |
| Source inspection exposed temporary H swaps for column locality | Contract distinguishes internal mechanics from observable mutation; Go uses direct subdiagonal access | Input and padding observations pass, including poisoned lower storage |
| Agreement alone could conceal an ineffective comparison | Skill requires known-bad candidate rejection; persistent checks compile three mutants | All three are rejected against the actual Fortran executable |
| A unit absolute floor would hide tiny wrong answers | Comparison uses product-term scale; a 1e-200-versus-zero negative control must fail | `test_small_results_have_no_unit_absolute_tolerance_floor` passes |
| Serialization checks alone did not exercise the replay command | Skill explicitly requires public-command replay and unknown-case rejection; added a persistent CLI check | `test_cli_replay_preserves_exact_inputs_and_rebuilds` passes |
| Final audit reproduced a non-default replay seed being replaced by the CLI default | Replay retains its original seed and hashes the source report; skill requires input-provenance checks separately from new build identity | Regression first failed with `20260911 != 20260910`, then passed after repair |
| Version labels alone omit effective compiler settings | Reports include effective Go environment, source/binary hashes, and linked-library hashes | Final reports contain these fields |
| Skill validator's PyYAML dependency was absent | Ran the external validator with `uv run --with pyyaml`; did not add a Python dependency to the oracle | Metadata validation passed; oracle remains standard-library-only |

The finalized skill was re-read against the acceptance checklist and its documented commands were executed after the executable refinements. The source translation needed no numerical repair during these campaigns. The successful trial supports this pilot's workflow; it does not establish that arbitrary migrations will work without further refinement.

## Reproduce and limits

Run `make verify` from the repository root. It rebuilds both implementations, runs infrastructure checks and two campaigns, then replays a saved case. Tool/build failures are errors, not skips. See the [playbook](../.agents/skills/oracle-migration/references/playbook.md) for prerequisites and individual commands.

Acceptance is limited to MB01UD and the [documented domain](mb01ud-contract.md). Output/input aliasing, active nonfinite operands, NaN payload fidelity, overflowing computations, other SLICOT routines, and other platforms/backends are not covered. No speedup is claimed. The pilot calls Gonum BLAS; it does not demonstrate a Go LAPACK translation. The video's public description was reviewed, not its full transcript.
