# Validation scope and acceptance gates

## Separate questions

1. **Source identity:** Did the package preserve the reviewed sources, helper, profile flags and input specifications?
2. **Tooling:** Do builds, wrappers, manifests, default-profile selection and explicit opt-in checks behave as designed?
3. **Controlled reproducibility:** Do final packaged builds reproduce the preserved profile-specific behavior under matched inputs, compiler/runtime identity and FP policy?
4. **Windows comparison:** Which files, times, variables and reference executable were actually compared, using what exclusions and tolerances?
5. **Platform qualification:** Was that exact package exercised on an actual Ubuntu 24.04 x86-64 target?
6. **Scientific suitability:** Are the model setup, warnings, conservation behavior and predictions acceptable for the intended application?

Passing one gate does not imply passing the others. The current observed host is Debian 13; Ubuntu 24.04 is the requested target and remains unverified until a target receipt establishes otherwise. Do not infer Ubuntu qualification from Linux execution or an ELF dependency audit.

## Profile contract

`strict` remains the default. It preserves the existing original port's source bytes and floating-point behavior, including diagnostic failures where these exist. A regression test can pass by reproducing a recorded strict failure; that is not a claim that strict completes every model case.

`windows-compatible-invalid-only` is an explicit experimental selection. It includes five reviewed power-call changes and invalid-exception masking. The policy must preserve the separately recorded divide-by-zero/overflow, rounding, FTZ and DAZ expectations; inspect the actual FP receipt. It is not permission for global exception suppression or new numerical changes. Matching printed Windows results does not establish internal-state identity or accuracy superiority.

## Preserved experiment observations

The pre-package controlled candidate produced these reported results:

- Detroit: all 36 compared scientific output files matched the official-original Windows return, whose recorded executable is `0eb294897682d6d3dabfac4ba6dc70fe96cfc29de7ebfdc75ffd6e6500edb163`, using the recorded clock-field exclusions (including the 72-byte binary clock), line-ending normalization and six explicit habitat-path correspondences.
- DeGray: all four available official-original Windows-reference output files matched, using the same recorded executable identity. This is limited reference coverage, not a statement about every possible DeGray output.
- Spokane: direct comparisons against both the official-original and the matched-compiler Windows returns retain subnormal CPL residual values and a small percent-error text difference for the constituent named `9CBODP` (maximum `4.5967667e-8` percentage points). The percent-error difference is not itself subnormal. The `9` is part of the constituent name, not a count of differences. Preserve their exact rows, quantities and values in the comparison receipt; do not relabel the case as an exact match or silently widen tolerances.

These are preserved experiment observations. They become evidence for this final package only after final-source identity and build/run regression gates pass. Package reruns compare against the accepted Linux candidate outputs, carrying forward the identified prior Windows comparison scope; they are not new Windows executions. Generated reports must distinguish historical evidence from newly executed package tests. Missing reference files and skipped comparisons are `not tested`, never `passed`.

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

Before an Ubuntu-qualified label: repeat build/startup/runtime checks and the agreed numerical regressions on actual Ubuntu 24.04 x86-64, with the supported compiler and independently acquired matching runtime. Re-audit the final ELF and library resolution. Never copy a different distribution's loader/glibc to manufacture a successful result.

Before production/default promotion: obtain the user's explicit decision, supported by application-specific scientific review and any agreed broader cases/restart/features. The present packaging task does not make that decision.

Any change to numerical source, FP policy, compiler/runtime, optimization flags, input values, profile default or comparison tolerances creates a new validation boundary. Keep the previous version and evidence accessible; document why the change was made and the tests repeated.
