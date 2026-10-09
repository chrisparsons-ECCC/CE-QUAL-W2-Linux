# Validation scope and acceptance gates

## Separate questions

1. **Source identity:** Did the package preserve the reviewed sources, helper, profile flags and input specifications?
2. **Tooling:** Do builds, wrappers, manifests, default-profile selection and explicit opt-in checks behave as designed?
3. **Controlled reproducibility:** Do final packaged builds reproduce the preserved profile-specific behavior under matched inputs, compiler/runtime identity and FP policy?
4. **Windows comparison:** Which files, times, variables and reference executable were actually compared, using what exclusions and tolerances?
5. **Platform qualification:** Was that exact package exercised on the specified actual OS/version and architecture, distinguishing the Ubuntu 24.04 target from the separate exploratory Ubuntu 26.04 scope?
6. **Scientific suitability:** Are the model setup, warnings, conservation behavior and predictions acceptable for the intended application?

Passing one gate does not imply passing the others. Initial package regressions ran on Debian 13. A later, independently reviewed Ubuntu 26.04 x86-64 VM return passed the agreed six-run exploratory controls. That review reconciled execution records and hashes; full VM outputs were not reread remotely. Ubuntu 24.04 remains unverified. Do not infer qualification for another OS/version, vendor CPU support or production suitability from either result or an ELF dependency audit.

## Profile contract

`strict` remains the default. It preserves the existing original port's source bytes and floating-point behavior, including diagnostic failures where these exist. A regression test can pass by reproducing a recorded strict failure; that is not a claim that strict completes every model case.

`windows-compatible-invalid-only` is an explicit experimental selection. It includes five reviewed power-call changes and invalid-exception masking. The policy must preserve the separately recorded divide-by-zero/overflow, rounding, FTZ and DAZ expectations; inspect the actual FP receipt. It is not permission for global exception suppression or new numerical changes. Matching printed Windows results does not establish internal-state identity or accuracy superiority.

## Comparison evidence and later coverage reviews

The candidate reproduces the preserved Linux controls. Its Windows evidence, including the later review of existing Spokane and DeGray files, is:

- Detroit: all 36 compared scientific output files matched the official-original Windows return, whose recorded executable is `0eb294897682d6d3dabfac4ba6dc70fe96cfc29de7ebfdc75ffd6e6500edb163`, using the recorded clock-field exclusions (including the 72-byte binary clock), line-ending normalization and six explicit habitat-path correspondences.
- DeGray: all 83 expected output names are now returned. All 81 nonempty scientific/diagnostic outputs match under the existing newline and named clock rules; the empty diagnostic log matches; compiler metadata remains an expected difference. The 77-file coverage gap was closed by collecting existing outputs, with no rerun or new tolerance. Original input/executable lineage does not substitute for a fresh Windows process-exit/runtime/FP receipt.
- Spokane: both official-original and matched-compiler Windows returns give the same complete residual ledger. It contains 9,410 `9CBODP` CPL differences (maximum `2.29246e-321 g/m^3`) and 100 snapshot balance/reporting differences. The corrected maximum snapshot percent difference is approximately `1.1872750e-7` percentage points, including `10CBODP` through the unchanged percent-value carry-forward. The old `4.5967667e-8` figure covered only 72 aligned tokens; the remaining 28 lines are now parsed. The percent difference is not subnormal. Preserve exact rows/quantities/values; do not relabel Spokane as an exact match or silently adopt an acceptance tolerance.

These observations are tied to preserved source and output identities. Final-package and later Ubuntu 26.04 reproduction gates passed for those identities, but their evidence and acceptance scopes remain distinct. Package reruns compare against the accepted Linux candidate outputs, carrying forward the identified prior Windows comparison scope; they are not new Windows executions. Generated reports must distinguish historical evidence from newly executed package tests. Missing reference files and skipped comparisons are `not tested`, never `passed`.

## Run and comparison requirements

- Stage an explicit input allowlist in a fresh run directory. Verify raw input hashes before execution. Preserve control values, dates, switches and forcing files. Record case-sensitive/literal-path aliases without altering contents.
- Record exact executable, compiler/runtime identity and build profile. Environment variables and output directories must not silently select the compatibility profile.
- Capture exit status, completion markers and achieved end time. A configured end time, a last output row or a zero-byte error file alone is not completion proof.
- Inventory expected/produced/reference files and preserve raw hashes. Treat missing, extra and truncated files as explicit findings.
- State normalization separately from numerical parsing: byte equality, equality after newline handling and parsed numerical equality are different claims. Formatting-only exclusions must be named and justified.
- Check timestamps/row counts/headers before comparing values. Record compared denominators, unparsed files and scope limitations. Output-sampled timesteps do not describe every internal timestep.
- Report nonfinite values and warnings in context, including pre-existing warnings. A suppressed invalid exception can permit execution while producing a nonfinite diagnostic; continuation is not proof of physical validity.
- Record maximum absolute and relative differences and their locations. Near-zero/subnormal values require an explicit absolute-scale discussion; avoid misleading relative-only percentages. Do not introduce acceptance tolerances retroactively to call a mismatch a pass.
- Keep raw scientific outputs in the private validation store. Commit small sanitized receipts, hashes, comparison rules and summaries sufficient to identify exactly what was checked.

## Required promotion evidence

Before a release-candidate label: verify final source manifests, run wrapper/build unit tests, rebuild both profiles, execute the agreed profile-specific case regressions, compare with preserved experiment/reference identities, and record the exact final package revision. Document incomplete gates.

Before an Ubuntu 24.04-qualified label: repeat build/startup/runtime checks and the agreed numerical regressions on actual Ubuntu 24.04 x86-64, with the supported compiler and independently acquired matching runtime. The completed exploratory Ubuntu 26.04 review does not satisfy that different target gate. Re-audit the final ELF and library resolution. Never copy a different distribution's loader/glibc to manufacture a successful result.

Before production/default promotion: obtain the application owner's explicit decision, supported by application-specific scientific review and any agreed broader cases/restart/features. Acceptance of Spokane's bounded residuals and the policy of continuing after invalid results remain pending. Evidence closure and publication of these results do not make that decision.

Any change to numerical source, FP policy, compiler/runtime, optimization flags, input values, profile default or comparison tolerances creates a new validation boundary. Keep the previous version and evidence accessible; document why the change was made and the tests repeated.
