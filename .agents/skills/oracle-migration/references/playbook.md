# Legacy migration with an executable oracle

The outcome is a maintainable replacement plus evidence explaining where it agrees with the legacy system. Battle-tested code is executable documentation; it is not proof that every legacy behavior is desirable or mathematically correct.

This playbook is reusable. The commands in the final section belong to the SLICOT demonstration repository; adapt the implementation language, build, case protocol, and comparisons for a different system.

## 1. Discover one migration boundary

Read the source and its callers. Map the routine's dependencies and the sequence of externally observable actions. Existing comments, examples, and manuals guide investigation, but confirm important claims in executable statements. A legacy codebase with documentation can still benefit from an oracle.

Choose a bounded slice whose dependencies can actually run. Favor one routine with distinct branches over a large nominal feature whose dependencies must be stubbed. List inputs, outputs, mutation, initialization requirements, ignored storage, errors, quick returns, and aliasing. For numerical code also record dimensions, layout, leading dimensions, triangle conventions, workspace, overflow/underflow regimes, and nonunique outputs.

Write a small compatibility table separating preserved behavior, deliberate target-language API changes, and excluded behavior. A modern API can replace INFO and workspace arguments, but its adapter must expose enough information to compare the underlying contract. No silent “cleanup” of quirks or error ordering.

**Gate:** the slice and accepted domain are explicit, dependencies are available, and the reference can be built without inventing its behavior.

## 2. Freeze and execute the reference

Pin source by revision and record source hashes, compiler and flags, architecture, runtime/library identities, precision, integer ABI, and concurrency settings. Build the original computational source unchanged. Keep native calls in a separate process when that makes error containment and independence clearer.

A wrapper may decode cases, allocate memory, call the original, observe error handlers, and serialize results. It must not reproduce the operation it is meant to observe. Disclose hooks that change process behavior, such as intercepting a terminating XERBLA handler. Build/tool failures fail acceptance; never skip the oracle silently.

First run a small asymmetric case that can be checked independently. Avoid only identity, symmetric, or square inputs: they can conceal swapped dimensions, missing transpose, and reversed multiplication order. Confirm the wrapper observes modified and supposedly untouched buffers.

**Gate:** the real reference executes known inputs, and its identity and outputs are captured.

## 3. Define a replayable case protocol

One serialized case drives both implementations. Keep logical data separate from physical storage, and document how each adapter allocates and packs it. For numerical data, ensure serialization preserves float64 values; preserve signed zero or nonfinite categories where they matter. Retain the actual generated input with the seed and generator identity.

Poison ignored storage so accidental reads become visible. Guard padding and observe input restoration. Do not claim that guard regions prove absence of every out-of-bounds access; use bounds checks/sanitizers when appropriate. Keep undefined memory operations outside the executable corpus. Safe error probes can allocate valid buffers and then invalidate only a scalar argument that the legacy code checks before accessing memory.

Treat output lengths, status fields, parse failures, subprocess failures, and timeouts as part of the protocol. Store both outputs and diagnostics even on comparison failure. Replay rebuilds current code against stored inputs; reproducing an old toolchain requires separately preserving that environment. Verify replay with a non-default seed: input provenance must survive rather than being overwritten by current CLI defaults. Record the source report identity separately from the new build identity.

**Gate:** both adapters pass independent input/output anchors, and malformed or incomplete observations cannot be accepted.

## 4. Translate the slice into a coherent target API

Keep the algorithm and its dependencies visible during the first translation. Use the established target numerical provider for BLAS/LAPACK operations and verify the exact entrypoints and storage conventions. Do not implement new low-level kernels solely to avoid learning the provider's contract.

Preserve observable semantics while removing source-language machinery callers no longer need. For example, a column-locality swap can become direct row-major indexing if the inputs are still unchanged on return. Keep any revised shape checks or safe slice validation explicit in the compatibility table.

Prefer the smallest useful operation. Avoid a generic migration framework, plugin system, or public configuration surface for one pilot. Infrastructure should earn its complexity by enabling the next case, mismatch diagnosis, or replay.

## 5. Choose comparisons before viewing results

Use exact comparisons for discrete values, statuses, lengths, and protected storage. Numerical equality needs an operation-specific policy:

| Output | Comparison |
| --- | --- |
| Integer/status/records | Exact, with documented normalization only |
| Floating-point products | Scale- and dimension-aware error bounds |
| Nearly cancelling sums | Bound relative to sum of term magnitudes, not only the final answer |
| Eigenvectors, Schur factors, repeated roots | Residuals, orthogonality, invariant subspaces, and permitted ordering/sign changes |
| Unsupported NaN/Inf result | Fail explicitly, even if both sides emit it |
| Ignored NaN storage | Compare as a protected category if payloads are outside the contract |

Do not use a large constant absolute floor that allows “return zero” to pass for tiny results. Record maximum error relative to the chosen bound. Inspect whether a generous bound is hiding a defect. Bound justification is part of the report, not something to derive backward from the largest observed mismatch.

Use a few independent identities or hand-calculated anchors to catch shared adapter mistakes. These complement the oracle; they need not become a manually maintained expected-output suite for the whole legacy system.

## 6. Run a corpus that can falsify the migration

Start with all mode branches, degenerate dimensions, zero coefficients, nontrivial rectangular cases, leading-dimension padding, safe errors, and specified input/output mutations. Add seeded cases spanning signs, magnitudes, structure, and cancellation. Seeded random coverage does not replace explicit branch and boundary coverage.

Prove the harness has teeth: compile or inject representative wrong behavior and require a failure. Examples include dropping a structural contribution, ignoring a mode, changing an input, returning zero, corrupting status/padding, and producing nonfinite output. A test that only checks identical outputs pass does not establish detection.

For every discrepancy:

1. Save the exact case and both observations before editing code.
2. Check build identity and the adapters first, then the translation, then the numerical policy.
3. Reduce the case without losing the failure and retain it as a runnable regression.
4. Explain any intentional contract difference in the report; do not silently bless it.
5. Repair the responsible layer and rerun affected checks plus a fresh-seed campaign.

**Gate:** no unexplained mismatches in the declared domain; known defects are detected; failures are replayable.

## 7. Refine the skill from evidence

Use the skill to execute a real pilot. Record what was attempted, what failed or was insufficient, the narrow change made, and which check now demonstrates the improvement. Include environment recovery only if it is reusable and necessary. Do not grow the skill with hypothetical rules unrelated to observed decisions.

Review the result from a fresh checkout/build. If an independent agent evaluation is authorized, give it the skill and raw task without the intended answer; otherwise describe the evaluation accurately as a same-agent trial and executable checks. Do not equate a metadata validator with behavioral acceptance.

Acceptance requires all of the following:

- Reference provenance and a runnable build.
- A documented boundary and compatibility mapping.
- A replacement using the selected provider, with persistent checks for changed modules.
- Passing deterministic and generated side-by-side cases over the stated domain.
- Detection of known-bad candidates, malformed output, status errors, and storage changes.
- A saved failure/success report and an exercised replay path.
- Concrete skill refinements tied to trial evidence and explicit remaining limits.

Stop at the authorized deliverable. Report Git state and publishing state separately from numerical acceptance. End plans with unresolved questions or “Unresolved questions: none.”

## Run the SLICOT → Go demonstration

From the repository root, prerequisites are Git, Go 1.24 or newer, Python 3.10 or newer, gfortran, and LP64 OpenBLAS with BLAS and LAPACK symbols. Python uses only the standard library. On macOS the runner can discover an existing Homebrew OpenBLAS; on Linux it uses pkg-config when available, then the system linker. If needed, set `FC` to the compiler executable and `ORACLE_BLAS_LIBS` to linker flags such as `-L/path/to/lib -lopenblas`. These flags are recorded. Installing prerequisites is a separate user/environment action.

```sh
git submodule update --init --recursive
go test ./...
go vet ./...
uv run python3 -m unittest discover -s oracle -p 'test_*.py' -v
uv run python3 oracle/run.py --seed 20260910 --random-cases 400 --report artifacts/acceptance.json
uv run python3 oracle/run.py --seed 20260911 --random-cases 400 --report artifacts/fresh-seed.json
uv run python3 oracle/run.py --replay artifacts/acceptance.json --case asymmetric-LT --report artifacts/replay.json
```

Every oracle invocation rebuilds both binaries. The Python infrastructure checks also compile three deliberately broken candidates in a temporary directory without modifying production source. The commands exit nonzero for failed acceptance. Reports contain full replay inputs and outputs and are ignored by Git; retain them when investigating a failure.

The translated operation is `hessenberg.Product`; the reference is `reference/SLICOT-Reference/src/MB01UD.f`. Read `docs/mb01ud-contract.md` for exact layout/error mapping and tolerance policy, and `docs/acceptance.md` for the completed trial evidence. This pilot uses Gonum BLAS; future routines requiring LAPACK must verify Gonum's coverage explicitly.

To invoke this repository's skill, ask: “Use $oracle-migration to migrate one bounded legacy routine and verify it against the original.” Its discoverable entrypoint is `.agents/skills/oracle-migration/SKILL.md`; no global installation is required.

## Inspiration and attribution

The user-selected [Anthropic video, Claude Code modernizes a legacy COBOL codebase](https://youtu.be/OwMu0pyYZBc), describes analyzing an AWS mainframe demonstration and migrating functionality to Java, with documentation, planning, and iterative validation. Its public description was reviewed; this playbook does not claim a verified full transcript or quote specific video procedures. The executable numerical oracle, tolerance policy, and SLICOT-specific decisions here were developed and validated in this repository. SLICOT's license and source attribution are in `LICENSE-SLICOT` and `NOTICE`.
