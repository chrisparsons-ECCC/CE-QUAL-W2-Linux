# Changelog

This log describes the clean packaging snapshot and subsequent real changes. It is not reconstructed Git history.

## Experimental tooling update — 2026-10-10

- Added explicit-profile general-case and ensemble launchers for trusted, already Linux-ready cases, plus an exec shim, workflow guide and synthetic tests. Added read-only GitHub Actions tooling checks for Python 3.11/3.14; these are not solver qualification runs.
- Review hardening preserves the excluded vendor-log boundary, rejects nonregular JSON and unsafe parent-path tokens, rechecks build/input identities around execution, records bounded actual-runtime observations, and requires complete receipts before resume. Cancellation and failed-attempt evidence remain explicit.
- Source, FP policy, defaults, compiler/runtime locks, numerical controls, original regression harness/tests and package `VERSION` are unchanged. The publication allowlist adds only the five new package files.
- Local aggregate synthetic tests pass on Python 3.12.14. New-launcher native serial/concurrent model checks remain pending; prior three-case model qualification is carried forward only for the unchanged harness. No production promotion or model rerun is part of this integration.

## Documentation evidence update — 2026-10-09

- Recorded the independently reviewed Ubuntu 26.04 x86-64 VM reproduction of the published snapshot: both clean profiles, all six agreed regressions, 262 output records (242 raw-hash matches and 20 existing clock-only differences), 39 package tests and 22 handover tests. Strict Detroit remains the expected partial failure. This is a receipt-based exploratory result, not Ubuntu 24.04 qualification or vendor CPU-support approval.
- Closed DeGray's former 77-file Windows coverage gap by collecting existing outputs. The complete census is 81 matching nonempty scientific/diagnostic files, one matching empty log and one expected compiler metadata difference, with zero missing or unexplained files under the existing newline/clock rules. No new Windows run was performed.
- Completed Spokane's residual ledger: 9,410 subnormal-scale `9CBODP` contour differences and 100 snapshot balance/reporting differences. The corrected maximum percent discrepancy is approximately `1.1872750e-7` percentage points, including the unchanged writer's carry-forward into `10CBODP`. The older `4.5967667e-8` bound covered only 72 aligned tokens; 28 omitted-`E` lines are now accounted for.
- No numerical source, FP policy, default profile, compiler/runtime pin, build recipe, input manifest, comparison tolerance or accepted output-control hash changed. Package `VERSION` stays `0.1.0-dev.20261009`; this update is identified by its genuine documentation commit. Application-owner acceptance, production promotion and Ubuntu 24.04 qualification remain open.

The initial preparation entry below is retained as historical context; its then-limited Windows coverage is superseded by the dated evidence update above.

## 0.1.0-dev.20261009 — 2026-10-09

### Prepared

- Source-only package of the preserved CE-QUAL-W2 4.5.5 native Linux port.
- Separately hash-pinned strict/default and explicit `windows-compatible-invalid-only` profiles; compatibility is limited to the previously reviewed five power-call substitutions and invalid-exception helper.
- Explicit source/toolchain/build and case-input manifests, controlled build/run tools, and compact provenance.
- Git byte-preservation rules, publication allowlist/preflight, and provenance/validation/change-control guidance.

### Evidence and limitations

- Prior controlled candidate experiments reported Detroit 36-file agreement using recorded clock exclusions, newline normalization and habitat-path correspondences, and DeGray agreement for four available files against official-original Windows returns. Spokane retains subnormal CPL values and a small `9CBODP` percent-error text difference against both original and matched-compiler Windows returns. Final package regressions reproduced all six profile/case controls: 262 generated files, 242 raw matches and 20 audited clock-only differences. All 39 synthetic tests passed. Strict Detroit retains its expected partial failure; see `docs/VALIDATION_RESULTS.md` for identities, controls and limitations.
- Actual development host: Debian 13. Ubuntu 24.04 target qualification has not been performed by this snapshot preparation.
- Strict behavior remains the default. No production promotion or new numerical change is part of packaging.
- Compiler/runtime payloads, executables, case/output payloads, raw logs and prior Git metadata are excluded. Source-only publication was approved as a draft candidate; complete component-licensing review and any later binary redistribution remain distinct from that approval.
