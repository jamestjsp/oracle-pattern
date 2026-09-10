# MB01UD pilot contract

Source: `reference/SLICOT-Reference/src/MB01UD.f`, pinned at `4a752c35ab540ce6291be8590dd7ed47086fe4ff`. Read the executable statements as well as the argument documentation. The pilot covers the entire routine, not the rest of SLICOT.

`B = alpha*op(H)*A` for left multiplication; `B = alpha*A*op(H)` for right multiplication. `A` and `B` are m by n. `H` is square of order m (left) or n (right), and upper Hessenberg. Its entries below the first subdiagonal are ignored. N means no transpose; T and C both transpose real data. Flags are case insensitive.

## Dependency closure

MB01UD calls `LSAME`, `DLACPY`, `DLASET`, `DSWAP`, `DTRMM`, `DAXPY`, and `XERBLA`. Compile the unmodified pinned routine, linking BLAS and LAPACK from an LP64 OpenBLAS build. The driver replaces only XERBLA with an observation hook so invalid calls return their INFO rather than potentially terminating the process. It records the handler argument independently. No SLICOT calculations are reimplemented in the reference adapter.

The Go implementation uses Gonum's native BLAS through `blas64.Trmm` and `blas64.Axpy`. Slice operations replace copy/set helpers. Direct subdiagonal access removes the temporary DSWAP used for column locality in Fortran. There is no need to call LAPACK in this Go pilot; Gonum remains the intended LAPACK provider for future routines that require it. It is not a claim that Gonum implements every SLICOT dependency.

## Calling convention mapping

| Concern | Fortran reference | Go Product |
| --- | --- | --- |
| Layout | Column major, explicit leading dimensions | Gonum row-major General descriptors |
| Output | Caller-provided B | Caller-provided B; preserves row padding |
| H and A | Unchanged on return, H temporarily modified internally | Read only throughout the operation |
| Workspace | None | None |
| Invalid arguments | INFO plus XERBLA | Typed ArgumentError; adapter maps fields to INFO |
| LDA and LDB minima | max(1,m) | max(1,n), because storage is row major |
| Empty dimensions | Validate scalars first, then no data access | Validate descriptors first, then no data access |
| alpha = 0 | Do not read H or A; zero B | Same; H/A slices may be nil |
| Aliasing | No B/A or B/H overlap promised by this pilot | B must not overlap A or H |

The adapter maps `side`, `trans`, `rows`, `cols`, `h`, `a`, `b` errors to -1, -2, -3, -4, -7, -9, -11. Invalid probes deliberately invalidate the corresponding native descriptor, not the same numeric stride in both layouts. Go also rejects mismatched shapes and undersized slices before writing output; these memory-safety checks have no safe Fortran counterpart and are covered by Go tests. Nil data is accepted only when the quick return does not access it. H and A may overlap each other because both are read only in Go; that is outside the paired oracle corpus.

## Supported numerical domain

Use float64, finite active operands and alpha, and products whose result and comparison scale remain finite. Generated campaigns cover mixed signs, zeros, cancellation, one-row/column cases, rectangular shapes, scales 1e-100 to 1e100, and alpha scales 1e-50 to 1e50. They do not prove accuracy for all representable floats. Active NaNs, infinities, overflowing results, overlapping output buffers, NaN payload fidelity, and cross-backend reproducibility beyond recorded runs are outside acceptance.

Ignored H entries and unused inputs for alpha=0 are poisoned with NaNs. They must not contaminate the finite result. Every returned H/A value must equal the input exactly (including signed zeros, with NaNs compared by category); all physical padding must remain the finite sentinel. Error cases must leave B unchanged. Mathematical zero results need not preserve a particular zero sign.

## Comparison rule

For each output element, form an independent magnitude scale from the mathematical product:

```
Sij = abs(alpha) * sum_q abs(op(H)[i,q] * A[q,j])  # left
Sij = abs(alpha) * sum_q abs(A[i,q] * op(H)[q,j])  # right
bound = 64 * epsilon_float64 * max(1,k) * Sij + 16 * smallest_subnormal
abs(reference_ij - candidate_ij) <= bound
```

The dimension factor allows rounding accumulation and the factor 64 conservatively allows differing BLAS evaluation orders. This is an engineering acceptance bound, not a forward-error theorem. Report the largest error/bound ratio so excess slack remains visible. There is no unit absolute floor that could hide a small but completely wrong result. alpha=0 is compared exactly. Any nonfinite result or comparison scale fails even if both executables agree. Near cancellation, use the sum of absolute terms rather than relative error against a nearly zero answer.

Separate hand-calculated asymmetric cases anchor the adapters and mathematical operation. The oracle is the authority for the broad generated corpus; those few anchors and infrastructure tests protect the oracle from common-mode mistakes. Neither parity nor these anchors prove the absence of a legacy defect.

## Recorded calls and replay

`oracle/cases.json` and the deterministic generator define capture inputs. Each case has `id`, `side`, `trans`, `m`, `n`, `alpha`, `pad`, `invalid`, and flattened logical row-major `h`, `a`, `b` arrays. Floats are strings, preserving float64 round trips, signed zero, and NaN sentinels without nonstandard JSON. Dimensions/padding are bounded to 256. `invalid` is 0 or the Fortran argument index to invalidate after allocating safe buffers.

`oracle/baselines/mb01ud-v1/manifest.json` identifies schema 2, policy `mb01ud-float64-v1`, original seeds, count, reference provenance, and the SHA-256 of `calls.jsonl.gz`. Each compressed JSON line has a `case`, an `expected` legacy observation, and a `trace` identifying scenario, caller, callee, and invocation. The caller is `oracle/reference/driver.f90`, the callee is MB01UD, and each isolated scenario makes one invocation. No application caller or stateful scenario is claimed.

Capture runs only the reference, observes all logical H/A/B entries, status, XERBLA, and physical padding, and refuses to overwrite an existing baseline. Each adapter packs logical matrices into its own native layout. Baseline creation validates observations before publishing the manifest; a failed or incomplete directory is not a valid baseline. The corpus combines 605 deterministic cases with 400 cases from each of seeds 20260910 and 20260911, deduplicating common deterministic cases.

`verify` validates the stored corpus, builds only Go, and compares current observations to `expected`. `verify --case ID` replays one stored call. It never requires or reads the reference checkout. Reports identify baseline manifest/data hashes and original seeds separately from current Go build provenance. `audit` builds only Fortran and compares new legacy observations, including the error hook, to the same baseline. Audit does not update expected results.

Missing/corrupt baselines, unknown schemas/policies, empty or duplicate cases, unexpected status, malformed outputs, timeouts, and missing selected calls fail. Reports cannot be written inside the baseline directory. Checksums detect corruption; reviewed Git revisions establish trusted baseline identity. New coverage requires a new versioned capture, never candidate-generated expected values.
