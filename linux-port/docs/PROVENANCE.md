# Source provenance and attribution

## Identity, not a release label alone

Model family: CE-QUAL-W2 4.5.5. Package lineage: the user-approved uploaded May 2026 solver source, followed by the previously tested native Linux platform-boundary port and a separately selected compatibility experiment. Package versioning is independent of the model version.

Recorded uploaded artifacts:

| Artifact | SHA-256 |
| --- | --- |
| Reassembled `v455.zip` | `fef68d3cd4dc4160b7fcc910b04aa8fc07c8ab511d84e8305b12e51ae4e9058a` |
| Nested `w2_source_5-21-2026.zip` | `7f0be0374e5a472acb8024d5e61bb20637be4e9c6d9db41ad74f57cc6311279a` |
| Supplied Windows `w2_v455_ifx.exe` | `0eb294897682d6d3dabfac4ba6dc70fe96cfc29de7ebfdc75ffd6e6500edb163` |

These content hashes identify the uploaded bytes. They do not authenticate their website origin, identify the compiler that built the supplied Windows executable, or establish a Git commit that produced it. The official-original Windows output returns used for the Detroit 36-file and DeGray four-file comparisons are recorded to that supplied executable identity. Spokane was directly compared against both official-original and matched-compiler Windows returns. These output-return lineage records are comparison evidence; they do not establish a matching source Git commit or the original compiler identity. Later instrumented Windows rebuilds used for internal traces are separate references and must not be substituted for the official-original full-output comparisons.

The [official ERDC repository](https://github.com/CE-QUAL-W2-ERDC/CE-QUAL-W2) was inspected at commit `5544026e3f1a39c0c9e827bd3dc2bbc13a94636c`. The separately located PSU `Version4.5.5` candidate was recorded at commit `ee2637bab6b8bb3f01738fcd792ded6eb9320d1c` in [drswells/CEQUALW2](https://github.com/drswells/CEQUALW2). Neither is asserted to match the uploaded May solver. Recorded comparison against the pinned ERDC model subtree found 27 Fortran/preprocessor files differing beyond line endings. The [PSU release log](https://www.cee.pdx.edu/w2/w2blog.htm) also records multiple updates carrying the 4.5.5 label. Do not replace hash-pinned input with a moving branch or infer equivalence from version text.

## Preserved port and explicit candidate

`config/sources-strict.json` hashes all 52 preserved source files. The strict profile is the existing Linux port, not an untouched Windows source tree. Its source identity is checked against the restored baseline provenance, SHA-256 `db08aefcb610d24ace602061b333d67517e703a191850469ed6e9eea3796fb4e`.

`config/sources-windows-compatible-invalid-only.json` hashes the independently preserved candidate. Relative to strict, only `heat-exchange.f90`, `temperature.F90` and `w2_cli.f90` differ; the candidate additionally compiles `source/helper/w2_invalid_mask.c`. The first two files contain the five reviewed power-call substitutions. The CLI/helper implements the separately reviewed invalid-exception mask policy. Source manifests and review diffs, rather than this summary, are the exact change authority. No new scientific change is implied by repackaging.

The preserved candidate build authority is identified by SHA-256 `3ab8c99ca977c4836a985f58ce29a3440bc243f9d522b0236b354e8b48a414c6`; the strict build-results authority by `38f4ccc85d21f35a7a18dc4940cdd1b0c7cab1435a2e5abf7eae3b4f0679e645`. These are historical evidence-object hashes, not hashes of newly sanitized documents or of final packaged executables.

`config/build-profiles.json` records the compile-unit order, flags and profile distinction. `config/toolchain-lock.json` records the preserved Intel IFX compiler/runtime content identity. The compiler, its installers/recovery archive, all runtime payloads, model binaries and case payloads are deliberately absent. A manifest entry naming a compiler library is a hash record, not that library's inclusion in the repository.

Source and compact evidence are reconstructed from retained verified artifacts. The package does not reconstruct old Git history. Any historical commit IDs in earlier reports are documentary references only unless the corresponding objects and ancestry are independently recovered and reviewed.

## Attribution and licensing boundary

The actual uploaded solver header in `source/strict/w2modules.F90` and its candidate counterpart carries **MIT License, Copyright (c) 2023 drswells**, including permission and warranty text. It also carries the original PSU/U.S. government disclaimer and legacy export wording. Preserve all these comments verbatim. Reproducing the historic export wording does not represent it as a current legal determination.

A separately preserved ERDC MIT notice has Copyright (c) 2026, Environmental Modeling Team / Environmental Laboratory / Engineer Research and Development Center / U.S. Army Corps of Engineers. It is contextual attribution for that source lineage; it must not replace the uploaded solver's drswells notice or be presented as a license for Intel components.

`particle.f90` retains named algorithm/book attributions. Their comments do not by themselves establish an independent license grant or a complete legal provenance review. Preserve them. Newly written CLI/helper/build/test/documentation additions must be attributed and licensed by the actual rights holder; do not invent an author or apply someone else's copyright to them. The component distinctions are recorded in `notices/README.md`; no new blanket third-party copyright is assigned by packaging.

This source-only candidate preserves the reviewed notices and component distinctions. It does not claim an exhaustive legal provenance audit or assign a new blanket license to all components. Binary redistribution has additional Intel static/shared-runtime provenance and notice requirements, even if the executable appears to link only a few shared libraries. Installing a compiler or holding a private recovery copy is not evidence that every component may be redistributed.

## Reproducibility record

Each meaningful validation should capture: full package commit (if one exists), package/source manifest hashes, selected profile, compiler and runtime hashes, actual host OS/architecture, flags and link order, input fixture hashes, filename-alias policy, environment/FP policy, start/end and process exit status, executable hash, output inventories and comparison configuration. Keep private machine paths and full logs outside the publishable package. Retain an access-controlled mapping from descriptive artifact IDs/hashes to their stored originals.

A hash match proves byte identity with the nominated object. It does not prove scientific correctness, legal provenance, target-platform support or origin authentication. See `VALIDATION_POLICY.md` for the separate acceptance gates.
