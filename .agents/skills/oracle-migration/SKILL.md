---
name: oracle-migration
description: Migrate a bounded legacy routine or feature by executing the original and replacement on identical inputs, comparing observable behavior, and retaining replayable evidence. Use for legacy rewrites with weak tests or documentation and for diagnosing migration mismatches; not for ordinary greenfield implementation or performance-only tuning.
---

# Oracle Migration

Treat the runnable legacy implementation as behavioral evidence. Translate the chosen feature into an idiomatic replacement while preserving the agreed observable contract. Documentation and generated expected values cannot substitute for executing the original.

Read [the playbook](references/playbook.md) when planning a migration, building an oracle, choosing numerical comparisons, or evaluating acceptance. It includes the runnable SLICOT-to-Go pilot and an acceptance checklist.

## Establish the boundary

- Inspect the exact legacy source revision, callers, dependency closure, existing examples, and build requirements. Select a routine small enough to cover fully but rich enough to expose meaningful behavior. Do not select a larger migration merely because its syntax looks simple.
- Record the supported domain, API/ABI mapping, input ownership, mutation, aliasing, error behavior, workspace, and intentional differences before translating. Decide which outputs have unique values and which admit equivalent representations.
- Follow the user's scope and existing authorization. Creating this skill or running a local oracle does not authorize publishing, changing upstream source, installing system packages, or expanding the migration.

## Build the oracle before trusting the rewrite

- Compile the pinned legacy source and real dependencies in a separate executable. Keep its adapter to marshalling and observations; do not reconstruct the algorithm or call the new implementation from the reference path.
- Anchor both adapters with small independently understood asymmetric inputs. Exercise distinct storage conventions, ignored regions, padding, mutation, and error paths. A legacy error-handler observation hook is acceptable if disclosed and kept separate from computational code.
- Drive both implementations from one serialized case. Preserve exact replay inputs, not just a seed. Exercise replay through the public command, including rejection of an unknown case; an in-memory serialization check alone does not validate replay. Check that replay preserves input provenance (including a non-default seed) while recording the new build separately. Fail on missing tools, build errors, crashes, timeouts, malformed output, missing cases, and nonfinite values outside the declared domain.

## Translate and compare

- Choose a target-language API that owns layout and sequencing details without disguising intentional compatibility changes. Verify provider coverage instead of assuming a numerical library implements every legacy dependency.
- Match statuses and structural outputs exactly. Check all observable input/output mutations and untouched regions. For floating-point results, choose bounds from operation size and scale before running the campaign; avoid global tolerances that hide small results. Use invariants/subspaces rather than raw vectors when valid results are nonunique.
- Cover control-flow branches, quick returns, invalid inputs where safe, structure, cancellation, and scale regimes. Add deterministic generated cases after explicit edge cases. Record the domain actually covered.
- Diagnose every mismatch as adapter, reference environment, translation, or contract/comparison behavior. Reduce it to a persistent case. Never regenerate the expected answer from the candidate or relax a bound solely to make a failure pass.

## Acceptance and skill refinement

Require: reproducible reference build; passing declared cases; unchanged protected inputs/storage; reviewed API differences; replayable reports with source/toolchain/backend identity and effective build settings; and evidence that known-bad candidates fail. Maintain runnable checks for the adapters and comparator—the differential oracle is the primary migration acceptance system, not an excuse to leave the harness unverified.

Before completion, run the playbook against the actual pilot from a fresh build and inspect the outputs. Compare what the instructions led you to verify against the acceptance gates. Fix the narrow instruction or executable defect that the trial exposed, rerun affected gates, then document the outcome and remaining limitations. Use a fresh generated seed after repairs. Do not claim universal equivalence, independent skill-agent evaluation, or performance improvements without corresponding evidence.

For this repository, start with `docs/mb01ud-contract.md` and `docs/acceptance.md`, resolved from the repository root. They are pilot evidence, not requirements for unrelated migrations. The reusable procedure is in the playbook above.
