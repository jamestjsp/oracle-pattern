---
name: oracle-migration
description: Migrate legacy routines or features using versioned recordings of their inputs, outputs, and state changes as an executable contract. Use for rewrites with weak tests or documentation, caller-boundary capture, and numerical migration mismatches; not for greenfield implementation or performance-only tuning.
---

# Oracle Migration

Capture the legacy system's behavior once for each approved corpus version. Execute the replacement against those stored observations during everyday verification. Keep the legacy build available for new captures and explicit audits; it need not run on every verification.

Read [the playbook](references/playbook.md) for capture, offline replay, mismatch triage, and the SLICOT example.

## Establish the boundary

Inspect the pinned source, callers, dependencies, and available documentation. Define the supported domain, state, mutation, aliasing, errors, layout, and target API differences. Select stable migration boundaries; recording every implementation detail can constrain legitimate refactoring and overwhelm the corpus.

Record the actual caller and scenario. Do not present synthetic harness calls as production traces. Stateful systems need initial state and ordered events, not only argument/return pairs. Preserve final scenario observations as well as useful intermediate calls.

## Capture an independent baseline

Build and run the real legacy computation. Instrument entry and exit or use a narrow adapter to capture exact inputs, outputs, statuses, and relevant state changes. Record source revision/hashes, toolchain, backend, precision, configuration, and scenario identity. Confirm adapters with independently understood asymmetric examples.

Version the captured data separately from candidate results. Capture must not use the replacement to generate expected values, and must not overwrite an existing baseline. Store checksums and schema/comparison-policy versions. Missing or corrupt recordings must fail verification; never silently recapture them.

Preserve actual inputs, including dimensions and initialization where relevant, rather than only random seeds. Keep protected/ignored regions observable. Add targeted boundary cases to representative caller traces because recordings cover only exercised behavior.

## Replay the replacement

Build only the replacement and run it on recorded inputs. Compare discrete outputs and observable state exactly. For numerical outputs use justified scale-aware bounds, residuals, or invariant subspaces as appropriate; do not hide tiny wrong answers with a unit absolute tolerance floor. Reject unsupported nonfinite outputs and malformed observations.

Check both isolated routines and connected scenarios when migrating a system. Isolated replay diagnoses local defects; scenario replay detects integration errors and accumulated drift. Do not replace all migrated callees with recorded answers in the final system acceptance run.

Reports must identify the immutable baseline and the current candidate build separately. Preserve recorded seeds, caller context, and original provenance. Verify one-call selection, unknown-call rejection, and operation without the legacy toolchain. Keep executable negative controls proving that known defects fail.

## Diagnose, audit, and finish

Save mismatching observations and their call IDs. Determine whether the issue is in marshalling, the translation, state/ordering, the comparison contract, or the legacy environment. Reduce failures to persistent cases. Never change expected outputs or widen tolerances merely to pass.

Use a legacy audit to investigate a discrepancy or confirm a capture environment. Use a new baseline version to add coverage or adopt an intentional reference change; retain the old version's identity. Compare snapshots only within their declared numerical domain and policy.

Acceptance requires a legacy-origin baseline, passing offline replay, integrity/immutability checks, detected known-bad candidates, reviewed API differences, and honest coverage limits. Exercise the procedure on a real pilot and refine only the instructions implicated by observed failures. Metadata validation alone is not a behavioral evaluation.

For this repository, `docs/mb01ud-contract.md` and `docs/acceptance.md` describe the pilot. Follow the user's scope and existing authorization for installations, publication, and changes outside the migration.
