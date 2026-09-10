# Oracle Pattern

Capture legacy behavior once, then replay it against a modern replacement. Battle-tested code becomes a versioned executable contract through recorded inputs, outputs, and state changes.

This repository contains an [agent skill](.agents/skills/oracle-migration/SKILL.md), a [migration playbook](.agents/skills/oracle-migration/references/playbook.md), and a working SLICOT-to-Go demonstration. Invoke the repository-local skill as `$oracle-migration`.

## Verify the translation

```sh
git clone https://github.com/jamestjsp/oracle-pattern.git
cd oracle-pattern
make verify
```

Requirements: Go 1.24+, Python 3.10+, Make, and the Go module dependency. Verification runs Go against checked-in legacy recordings. It does not require Fortran, OpenBLAS, or an initialized reference submodule. The initial Gonum module download may require network access.

The pilot translates `MB01UD`, a Hessenberg matrix product, into [`hessenberg.Product`](hessenberg/product.go) using Gonum BLAS. Its [baseline](oracle/baselines/mb01ud-v1/manifest.json) contains 1,405 calls captured from the pinned SLICOT implementation. Inputs, expected outputs, status, and harness caller identity are stored in compressed records beside the manifest. These are synthetic harness scenarios, not production application traces.

Replay one recorded call:

```sh
uv run python3 oracle/run.py verify --case asymmetric-LT --report artifacts/replay.json
```

See the [contract](docs/mb01ud-contract.md) for numerical bounds and API differences, and [acceptance evidence](docs/acceptance.md) for results. The primary acceptance system is recorded legacy behavior; small infrastructure checks and compiled negative controls establish that it can detect defects.

## Capture and audit

These are explicit maintenance operations, separate from ordinary verification. They require gfortran, LP64 OpenBLAS with BLAS/LAPACK, and the pinned reference:

```sh
git submodule update --init --recursive
uv run python3 oracle/run.py capture --output oracle/baselines/mb01ud-v2 --seed 20260912 --random-cases 400
make audit
```

`capture` creates a new baseline and refuses to overwrite an existing directory. `audit` reruns the reference against stored inputs. Neither needs Go. Verification and audit never modify the baseline. Reports live under ignored `artifacts/`, and builds use automatically cleaned temporary directories.

The [playbook](.agents/skills/oracle-migration/references/playbook.md) includes scientific and mainframe precedents, caller-boundary capture, stateful scenario replay, toolchain setup, and baseline extension rules.

## Scope and attribution

This is one bounded numerical migration. It does not demonstrate application-level caller instrumentation or a complete control-system rewrite. Gonum supplies BLAS here; future LAPACK-dependent routines must verify provider coverage.

[SLICOT](https://github.com/SLICOT/SLICOT-Reference) remains pinned under `reference/SLICOT-Reference`. It includes documentation that supplements its executable behavior. [NOTICE](NOTICE) and [LICENSE-SLICOT](LICENSE-SLICOT) preserve source attribution and upstream terms. The [COBOL modernization video](https://youtu.be/OwMu0pyYZBc) is the user-selected inspiration.
