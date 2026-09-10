# Oracle Pattern

Migrate legacy code by running the original and replacement side by side. Battle-tested code is executable documentation: preserve its observable behavior, investigate discrepancies, and retain replayable evidence.

This repository contains a reusable agent skill, a migration playbook, and a working SLICOT-to-Go pilot. The primary acceptance system executes the original Fortran on every case; it does not derive expected answers from the rewrite.

## Start here

- [Oracle migration skill](.agents/skills/oracle-migration/SKILL.md) — discoverable locally as `$oracle-migration`.
- [Migration playbook](.agents/skills/oracle-migration/references/playbook.md) — discovery, reference build, contracts, comparisons, triage, and acceptance.
- [MB01UD contract](docs/mb01ud-contract.md) — scope, API mapping, numerical domain, and comparison policy.
- [Acceptance evidence](docs/acceptance.md) — trial results, skill refinements, and limitations.

## Working pilot

[SLICOT MB01UD](reference/SLICOT-Reference/src/MB01UD.f) multiplies a general matrix by an upper Hessenberg matrix, on either side and with optional transpose. Its Go translation is [`hessenberg.Product`](hessenberg/product.go), using Gonum BLAS. Gonum is the intended BLAS/LAPACK provider; this particular routine requires BLAS only in Go.

The [oracle runner](oracle/run.py) builds the pinned Fortran source against OpenBLAS and builds the Go candidate independently. It sends both the same logical matrices, checks numerical results, statuses, restored inputs, and physical padding, then saves full replayable reports. A small persistent harness test set anchors the adapters and checks the comparator; three compiled wrong candidates must be rejected.

```sh
git clone --recurse-submodules https://github.com/jamestjsp/oracle-pattern.git
cd oracle-pattern
make verify
```

Prerequisites: Go 1.24+, Python 3.10+, gfortran, Make, and LP64 OpenBLAS with BLAS/LAPACK. The runner discovers an existing Homebrew or pkg-config OpenBLAS, or uses the system linker. Set `ORACLE_BLAS_LIBS` when a custom library path is needed. Python's oracle code uses only the standard library. See the playbook for individual commands and toolchain details.

For an existing checkout, initialize the reference with `git submodule update --init --recursive`. Reports and binaries are written under ignored `artifacts/`. Replay one stored input against freshly built binaries:

```sh
uv run python3 oracle/run.py --replay artifacts/acceptance.json --case asymmetric-LT --report artifacts/replay.json
```

## Reference and scope

The user-selected [Anthropic video, Claude Code modernizes a legacy COBOL codebase](https://youtu.be/OwMu0pyYZBc), provides the modernization inspiration. Its public description was reviewed; this repository's numerical oracle procedure comes from the actual pilot, not a claimed full video transcript.

[SLICOT](https://github.com/SLICOT/SLICOT-Reference) is pinned as the Git submodule `reference/SLICOT-Reference`. It has documentation and examples; these supplement its executable behavior. The skill also applies when such supporting material is sparse.

Acceptance covers one routine and the documented finite-input domain on the recorded platform. It is not a complete SLICOT migration, proof that the reference has no bugs, or a performance claim. Source attribution and upstream redistribution terms are retained in [NOTICE](NOTICE) and [LICENSE-SLICOT](LICENSE-SLICOT).
