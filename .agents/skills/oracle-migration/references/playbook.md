# Capture once, replay the rewrite

Treat captured legacy behavior as a versioned executable contract. Ordinary verification runs the replacement against stored expected observations. Legacy execution is required to create or extend that contract, not for every development iteration.

## 1. Discover and select a boundary

Read the source, callers, dependencies, and documentation. Choose a bounded routine or feature whose original implementation can run. Document input ownership, errors, quick returns, mutated state, ignored data, aliasing, layout, and intentional target-language API differences.

Capture at useful migration boundaries. For a numerical routine this may be entry/exit arrays and status. For a credit-card batch it may include starting balances, rates, dates, input records, written records, and ending balances. For a controller it includes initial state, parameters, ordered inputs, timestep, output signals, and updated state. Record representative scenarios and add explicit edge cases; production samples alone do not cover every branch.

## 2. Record the legacy system

Run the pinned original implementation with narrow entry/exit instrumentation or an adapter. Capture enough context to reproduce a call:

- Scenario, caller, callee, invocation or event order.
- Arguments and relevant state before the call.
- Outputs, status, mutations, and relevant state afterward.
- Data shape, layout, precision, alias relationships, and interpretation.
- Source revision, hashes, compiler/backend identity, configuration, and comparison-policy version.

Independently check a few asymmetric examples so layout and transpose bugs cannot hide in both adapters. Observe input restoration and protected storage. Disclose error-handler hooks or other instrumentation that changes process behavior.

Write a new baseline version only after successful capture and validation. It must contain original observations, not values computed by the replacement. Keep checksums and review baseline changes as changes to the acceptance contract. Verification and audit are read-only with respect to baselines. A checksum detects corruption; version control and review establish which baseline is trusted.

## 3. Run offline verification

Load and validate the baseline before building the candidate. Fail on missing cases, unknown policy/schema, corruption, malformed output, crashes, or timeouts. Do not auto-update expected values.

Run each new routine using its recorded inputs. Preserve call identity and original capture provenance in the report while recording the new candidate's build separately. Exercise replay with non-default seeds and verify that CLI defaults cannot relabel the data.

Use two levels for system migrations: isolated call replay for diagnosis and full scenario replay for integration. The latter executes the connected new system; recorded callees must not replace every new computation. Caller identities support diagnosis without requiring the rewrite to retain the same internal call graph.

## 4. Compare the observable contract

| Data | Comparison policy |
| --- | --- |
| Accounting amounts and records | Exact decimal/fixed-point semantics, including rounding and scale |
| Status, shape, discrete state | Exact |
| Floating-point numerical outputs | Operation- and scale-aware bounds, with an explicit accepted domain |
| Nearly cancelling sums | Bounds based on term magnitudes, not just the small final answer |
| Eigenvectors or nonunique factors | Residuals, orthogonality, ordering/sign allowances, invariant subspaces |
| Control-system traces | Values and state on a defined time/event grid; explicit timing policy |
| Protected inputs and padding | Unchanged under the stated representation policy |

Avoid a large absolute floor that lets zero pass for tiny results. Unsupported NaN/Inf results fail even if both sides agree. Never relax tolerances solely because a rewrite fails. Supplement the corpus with independent identities where valuable, and require representative broken candidates to be rejected.

## 5. Triage and extend deliberately

A mismatch report must resolve to the exact recorded call and both observations. Check capture/build identity, marshalling, state and event order, the translated algorithm, then the numerical policy. Retain reduced regression cases.

An audit reruns the original on stored inputs when you need to check provenance or diagnose a difference. Capturing new scenarios or changing the reference requires a new baseline version. A fixed corpus supports a fixed coverage claim; keep the generator and legacy source available for future extensions.

Refine the skill after a real trial: record the failure, the focused correction, and its persistent validation. Report whether evaluation was same-agent or independently performed. Do not claim performance, universal equivalence, or production coverage without evidence.

## Run this repository

The pilot translates SLICOT MB01UD into `hessenberg.Product` using Gonum BLAS. Its recorded caller is the Fortran harness, not a control application. There are no stateful application scenarios in this pilot.

Everyday prerequisites: Go 1.24+, Python 3.10+, and Make. Go must have its Gonum dependency available (the first module download may require network access). Offline here means independent of legacy execution and libraries.

```sh
make verify
uv run python3 oracle/run.py verify --case asymmetric-LT --report artifacts/replay.json
```

`make verify` runs Go checks, baseline/comparator/adapter checks, three compiled candidate mutations, and all captured calls. It requires neither an initialized SLICOT submodule nor gfortran/OpenBLAS. Select one captured call with `verify --case ID`.

The checked-in baseline is `oracle/baselines/mb01ud-v1/`: a readable manifest and compressed call records. Reports go under ignored `artifacts/`; temporary binaries are removed automatically.

Capture and audit additionally require Git, gfortran, and LP64 OpenBLAS with BLAS/LAPACK. Initialize the pinned source first. Existing Homebrew/pkg-config installations are detected; `FC` and `ORACLE_BLAS_LIBS` can select an installed toolchain.

```sh
git submodule update --init --recursive
uv run python3 oracle/run.py capture --output oracle/baselines/mb01ud-v2 --seed 20260912 --random-cases 400
make audit
```

Capture refuses an existing output directory and never builds Go. Audit rechecks the default baseline using Fortran and never builds Go; select another with `audit --baseline PATH`. Ordinary verification never captures or refreshes data. Native tests are isolated under `make audit`.

Read `docs/mb01ud-contract.md` for API and numerical details and `docs/acceptance.md` for measured acceptance. Plans should end with unresolved questions or “Unresolved questions: none.”

## Precedents

- [Pace's Fortran-to-Python atmospheric-model rewrite](https://gmd.copernicus.org/articles/16/2719/2023/) captures inputs and outputs around computation units with Serialbox, then validates units and larger assembled components. [pyFV3](https://github.com/NOAA-GFDL/pyFV3) documents versioned serialized Fortran data and replay adapters.
- [AWS's mainframe modernization workflow](https://aws.amazon.com/blogs/migration-and-modernization/automate-the-building-testing-and-deployment-processes-of-aws-mainframe-modernization-with-aws-blu-age/) separates an initial recording of legacy reference data from repeated replay and comparison. [CardDemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo) is a public credit-card demonstration application.
- [OpenFAST](https://openfast.readthedocs.io/en/main/source/testing/regression_test.html) compares simulation results with stored baselines and preserves baseline files during verification.
- [Simulink baseline testing](https://www.mathworks.com/help/sltest/functional-baseline-multirelease-and-parallel-tests.html) compares simulations with saved outputs. These last two are numerical baseline practices, not claims about specific language rewrites.
- The user-selected [Anthropic COBOL modernization video](https://youtu.be/OwMu0pyYZBc) motivated the demonstration. Its public description was reviewed, not its full transcript.
