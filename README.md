# Oracle Pattern

A skill and playbook project demonstrating how to migrate selected legacy numerical subroutines to Go, using the original implementation as an executable behavioral oracle.

The reference is [SLICOT](https://github.com/SLICOT/SLICOT-Reference), included as a pinned Git submodule at `reference/SLICOT-Reference`. The planned Go implementation will use Gonum as its BLAS/LAPACK provider.

## Demonstration reference

[Claude Code modernizes a legacy COBOL codebase](https://youtu.be/OwMu0pyYZBc) is the user-selected reference for developing the skill and playbook. This project applies the legacy-modernization theme to selected SLICOT subroutines and a Go/Gonum replacement.

The video transcript has not yet been reviewed; the workflow below records this project's proposed approach, not a verified summary of the video.

## Principle

Battle-tested code is executable documentation. Run the original and replacement implementations on the same inputs, compare their observable behavior, and retain reproducible evidence before accepting a migration.

The demonstration targets migrations where tests or documentation are insufficient. SLICOT itself includes documentation and example programs; these complement the executable reference.

## Planned oracle workflow

1. Select a small set of subroutines and trace their dependencies, argument contracts, workspace requirements, and failure behavior.
2. Build the pinned Fortran reference with a recorded compiler and BLAS/LAPACK backend.
3. Define a shared case format and separate adapters for the reference and Go implementation, preserving input copies where routines overwrite arguments.
4. Execute both implementations on identical deterministic cases, including boundary, singular, ill-conditioned, and invalid-input cases where the reference defines behavior.
5. Compare status codes, output shapes, mutations, and numerical results with explicitly justified tolerances. Use residuals and mathematical invariants for outputs that are not unique, such as eigenvectors and factorizations.
6. Save inputs, seeds, upstream commit, build configuration, outputs, and comparison diagnostics. Preserve mismatches as replayable regression cases.
7. Document intentional differences and require explained discrepancies before accepting a migrated routine.

The primary acceptance mechanism will be a runnable side-by-side oracle system, rather than a separately hand-authored expected-output suite. Persistent tests for adapters and comparison logic will guard the oracle infrastructure itself. Agreement with the reference establishes behavioral parity, not proof that the reference is mathematically correct.

## Clone

```sh
git clone --recurse-submodules https://github.com/jamestjsp/oracle-pattern.git
cd oracle-pattern
```

For an existing checkout:

```sh
git submodule update --init --recursive
```

## Status

Repository bootstrap only: the reference is pinned, but subroutines have not yet been selected and the skill, playbook, Go implementation, and executable oracle harness remain to be built.

## Reference license

SLICOT retains its upstream BSD-3-Clause license in `reference/SLICOT-Reference/LICENSE`. Preserve applicable upstream notices when translating or redistributing its code.
