# Changelog

This log describes the clean packaging snapshot and subsequent real changes. It is not reconstructed Git history.

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
