# Change control and package versions

The model version remains CE-QUAL-W2 4.5.5. `VERSION` identifies the independent Linux packaging/tooling line. A package version does not imply an official upstream release, bitwise Windows equivalence, public distribution approval, or Ubuntu qualification.

The initial working identifier is `0.1.0-dev.20261009`. It is a development snapshot, not a release tag. Proposed later labels include `0.1.0-rc.1` only after the package's specified release-candidate gates pass, and `0.1.0` only after the approved scope is complete. Keep qualification limits visible in release notes; a version label cannot remove them.

For each accepted change, record:

- What changed and why, with the affected profile(s)
- Whether it touches scientific code, floating-point policy, input semantics, platform support, tooling or documentation
- Source/build/input/reference hashes and an actual Git commit if one exists
- Tests newly run, tests carried forward and tests not run
- Known residual differences, warnings, coverage limits and next required gate
- Any explicit approval required for a new numerical intervention, default promotion or publication

Use real commits from this snapshot forward. Do not manufacture historical commits or imply that a chronological prose log is a recovered Git history. Tag only actual reviewed commits and retain the tag-to-commit and release-archive hashes. Never reuse a released version name for changed bytes.

Keep exact source differences independently reviewable. The duplicate strict/candidate source trees are deliberate at this stage: their manifests make both profiles auditable and prevent accidental fallback or mixing. Refactoring them into a patch/overlay scheme would be a separate packaging change requiring regenerated source-identity checks, even if its intended output is identical.

Bug fixes that change scientific values or FP state must not be hidden in a packaging patch. Document candidate behavior independently from the upstream model's public version, and repeat all affected acceptance gates in `VALIDATION_POLICY.md`.
