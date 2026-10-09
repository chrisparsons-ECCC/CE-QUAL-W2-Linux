# Validation results: 0.1.0-dev.20261009

The initial packaged source, build recipe and runner passed six controlled Linux regressions on Debian on 2026-10-09. Across **262 generated files**, **242 were byte-identical** to their profile-specific controls and **20 differed only in previously audited clock fields**. There were no unexplained changes, missing outputs or extra scientific outputs. The original results below are Debian-host results. A separate same-day Ubuntu 26.04 VM reproduction subsequently passed the same six profile/case controls; its receipt-level scope is recorded below. Ubuntu 24.04 qualification remains open. The later Spokane and DeGray reviews re-examined existing outputs without running the model or changing the acceptance controls.

## Initial Debian package runs

The strict controls are the preserved original native Linux port. The compatibility controls are the accepted five-power-site plus invalid-only-mask experiment. Each package run used a fresh build/run location, pinned input bytes and the exact installed compiler/runtime identities. Package tests did not execute Windows again.

| Profile | Case | Native exit | Wrapper status | Generated outputs | Raw matches | Clock-only differences | Result |
|---|---|---:|---:|---:|---:|---:|---|
| strict | Spokane | 0 | 0 | 12 | 9 | 3 | PASS |
| strict | Detroit | -6 | 134 | 35 | 32 | 3 | PASS: expected partial failure |
| strict | DeGray | 0 | 0 | 83 | 79 | 4 | PASS |
| windows-compatible-invalid-only | Spokane | 0 | 0 | 12 | 9 | 3 | PASS |
| windows-compatible-invalid-only | Detroit | 0 | 0 | 37 | 34 | 3 | PASS |
| windows-compatible-invalid-only | DeGray | 0 | 0 | 83 | 79 | 4 | PASS |

Strict Detroit reproduces native floating-invalid error 65 and the `calculate_tke` traceback at `az.f90:100`. Its partial output set and nonzero status are required controls; this row does not mean the strict run completed. The compatibility Detroit run completes with the accepted output set.

All 27 Spokane, 50 original Detroit and 31 DeGray inputs retained their exact hashes. Detroit staging also recreated its 44 already-reviewed Linux literal-backslash aliases without changing their contents. The package validator permits only named model/build clocks and CPU-duration fields; Detroit's binary `TITLE(11)` exclusion is precisely 72 bytes at offset 724. Compiler version/build text remains compared. Package regression checks use no floating tolerance, line-ending conversion or broad header exclusion.

## Floating-point and source controls

All three compatibility receipts confirm startup x87 control word `0372 -> 0373` and MXCSR `9940 -> 99c0`: only invalid-mask bits 0 and 7, respectively, change. Startup status, tags, other masks, precision, rounding, FTZ and DAZ remain unchanged. Logging guards and end-control checks pass, and all three native exits are zero. Model calculations can legitimately change sticky status flags after startup; the receipts preserve these observations rather than clearing them.

Strict uses its original CLI and links no masking helper. Both profiles retain the original numerical compilation flags, including `-fpe0` and `-fp-model=source`. The compatibility source differs only at the five approved power sites and the previously reviewed CLI/helper connection. Packaging does not add a new scientific or FP-policy change.

The final strict build has 51 executable-code/relocation sections matching the preserved strict reference; the compatibility build has 52 matching the accepted experiment. Fifty of 51 strict whole objects and 51 of 52 compatibility whole objects match exactly. The remaining object contains build-date/time strings and a temporary preprocessor filename. Those original macros remain enabled, so whole-executable byte reproducibility is not claimed.

## Recreating the accepted compiler context

A clean first-pass temperature compilation initially differed from the accepted incremental build despite identical source and command-line options. IFX generated interface modules from later compilation units were present during the accepted temperature recompile. The final compatibility recipe makes an explicit second compilation of the unchanged temperature source after the original 51-unit pass, then links in the original order. It records both commands and the complete generated-interface context. Strict retains its original single pass.

An isolated repeat and the final fresh build reproduced the entire accepted temperature object: SHA256 `9e5b1dfed84823612fa951d48a4213c2a5b5288ef9719426d8c36ec5b76ecf30`. Independent code/relocation review and all six full output regressions passed after this recipe correction. No source expression, compiler option or FP setting was altered to obtain it.

Final executable SHA256 values, identifying these particular dated builds:

- Strict: `9a1406399af907af1249b6f7139da036fed1d1fd198c1365ab595f4a633d126f`
- Compatibility: `515904867cedc354219c4d9ea637dd5da8c954beb4f2e53049d96c39cecc588c`

## Separate Ubuntu 26.04 exploratory reproduction

Execution snapshot: published commit `9c16db8e7697ffaa12f9678f15329fa0ce80d872`, before this documentation-only update. All 142 package-file identities, both profile recipes, the exact IFX 2026.1.1 build 20260724 component/runtime lock, and the accepted output controls were checked. The documentation update changes none of the executed source, tools, inputs, flags, FP policy or reference controls.

Returned preflight, build and per-run observations consistently record actual Ubuntu 26.04 x86-64 VM execution, glibc 2.43, Python 3.14.4, GCC 15.2 and GNU binutils 2.46. The original Debian results were not relabeled. Both clean builds and all six agreed regressions passed with the same profile-specific outcomes, output counts and classifications shown in the table above: **262 output records, 242 raw-hash matches and 20 established clock-only differences**. Strict Detroit still aborts with the expected error 65, native `-6` / wrapper `134`; all three compatibility runs complete with valid invalid-only FP receipts.

The returned records show all 39 unchanged package tests and 22 handover tests passing. Two independent offline reviews reconciled the build/run identities, all 343 receipt-file hashes, full input/output inventories, native statuses and raw FP receipts. Rerunning the frozen collector on the returned receipts reproduced its summary. Actual loaded-runtime observations match the pinned Intel libraries; each observation is one early process-map snapshot, not an inventory of every possible later load.

This is a **receipt-based exploratory qualification**. Full model outputs, compiler files and built executables remain on the execution system and were not transferred in the small return or independently reread remotely during review. Their recorded hashes and execution bindings passed; this is not a hardware-backed execution attestation. The later local Windows comparisons physically rehashed the retained accepted Linux outputs and matched their normalized identities to the VM's returned candidate records.

[Intel's 2026 compiler requirements](https://www.intel.com/content/www/us/en/developer/articles/release-notes/fortran-compiler/2026.html), checked on 2026-10-09, list Ubuntu 22.04 and 24.04 for CPU execution; the separate Ubuntu 26.04 client-GPU row does not establish CPU support. This successful VM reproduction does not assert vendor CPU support, Ubuntu 24.04 qualification, scientific accuracy or production approval.

Content identities for this particular execution return:

- Receipt archive: `475257c332eac59e769c9d37e5f2a37ca99040f123757a3f56d5aa98f4bb5ef2`
- Strict executable, as recorded: `75a58cb9926627d3d3be804e912f462be73096cacfeb19c0dd4f9e947cf45546`
- Compatibility executable, as recorded: `d65e261bb7a7975f80d591583237b29c2f2041d7d8fdcb81e57bbbfe63c87f8d`

## Windows comparison scope and completed reviews

Exact reproduction of the accepted Linux candidate carries forward the following earlier comparisons. Their Windows authority is the supplied official-original executable, SHA256 `0eb294897682d6d3dabfac4ba6dc70fe96cfc29de7ebfdc75ffd6e6500edb163`. Spokane was additionally compared with the controlled IFX 2026.1.1 Windows rebuild, SHA256 `a60ce4691569d39408c39eb2a3e951b4b2c676a9a0932cdfd4d4ad8a80454aef`.

- **Detroit:** all 36 scientific outputs match the official-original Windows return using the earlier audited clocks, line-ending normalization and six explicit habitat-path correspondences. The 37th file is compiler metadata. This includes 378,950 TSR/FLOWBAL values and the complete binary result except its 72-byte clock. The candidate reaches day 365, iteration 129,144, with the same 122 timestep violations and 43 layer-warning records.
- **Spokane:** the complete residual review now accounts for every scientific text difference against both official-original and matched-compiler Windows returns. The seven TSR files, FLOWBAL and warning file match after the existing newline handling; previously compared table and semantic profile values remain matched. The contour ledger has 9,410 differing `9CBODP` values, with maximum absolute difference `2.29246e-321 g/m^3`. The snapshot ledger has 100 scientific balance/reporting differences, including percent fields for `9CBODP` and carried-forward `10CBODP`. The corrected complete maximum percent-error difference is approximately `1.1872750e-7` percentage points; details and the superseded partial bound are below. Spokane is not a whole-output exact Windows match.
- **DeGray:** the 77 previously unreturned outputs were collected from the existing official Windows run and independently compared in full. All 83 expected output names are now available: **81 nonempty scientific/diagnostic files match**, the empty `DiagenesisLogFile.opt` matches exactly, and `W2CodeCompilerVersion.opt` retains its expected compiler metadata difference. The four earlier scientific files were rechecked against the same candidate. No missing or unexplained output difference remains under the established comparison rules. The original results reach iteration 42,365 with zero timestep violations; this collection did not rerun Windows or add a fresh native-exit receipt.

### Spokane: complete residual bounds and reporting mechanism

The contour file has 575,670 lines per platform; 9,410 values differ on 3,776 scientific lines, all labeled `9CBODP`. The Windows values are positive and subnormal-scale; Linux prints zero. Maximum difference: `2.29246e-321 g/m^3`, day 200.4000, branch 1, segment 2, layer 45. The first difference is at day 200.1000, branch 1, segment 2, layer 41. All 9,889 printed `9CBODP` cells across 101 dates are accounted for; 479 agree. No value was removed or set to zero by the comparison.

The complete snapshot parser handles Fortran's omitted-`E` exponent notation. It accounts for all 4,752 constituent-balance fields over 11 snapshots, two branches and 54 constituents. The 100 scientific differences comprise 20 spatial masses, 20 temporal masses and 20 mass errors for `9CBODP`, plus 20 percent fields each for `9CBODP` and `10CBODP`. Maximum absolute mass differences are `7.2855178e-316 g` (spatial), `5.9154658e-315 g` (temporal) and `5.2615860e-315 g` (mass error).

At day 210, branch 2, Linux prints `+0.11872750E-06` percent and each Windows reference prints `-0.35355655-292` percent for the two affected percent fields. Their exact printed-decimal difference is **`1.1872750e-7 + 3.5355655e-293` percentage points**. The previous `4.5967667e-8` bound covered only 72 aligned tokens; the other 28 lines were explicitly outside that earlier alignment rule. Two independent parsers now include those lines. No scientific snapshot line remains unclassified. The other differing snapshot lines are the already excluded 226 run clocks, one termination clock and one CPU-duration line.

The original input already contains subnormal-scale `9CBODP` concentrations. Recorded candidate FTZ/DAZ handling remains unchanged by invalid-only masking. Earlier single-factor experiments on the preserved pre-power-change baseline demonstrated sensitivity of this tiny output class to subnormal handling; they do not prove that toggling the current candidate would make its complete output Windows-identical. No such current-candidate counterfactual was run.

The unchanged snapshot writer updates its percent variable `DLMR` only when spatial mass compares nonzero, then prints it for each constituent. Its denominator includes `NONZERO=1e-20`. Across every one of the 20 noninitial day/branch records, Linux's printed-zero `9CBODP` inherits the preceding `8CBODP` percent, and zero-mass `10CBODP` repeats it. Windows computes a new near-zero percent for tiny nonzero `9CBODP`, which `10CBODP` then repeats. Source and paired output rows support this reporting carry-forward. The percent discrepancy is not itself subnormal and is not evidence of a bulk concentration error. Printed zero does not establish stored mass bits: DAZ can affect comparisons with subnormal operands.

The residuals are now fully bounded, not accepted by a new tolerance. Application-owner acceptance remains pending. Any current-candidate subnormal experiment or reporting fix needs separate approval and all affected case controls; neither is part of this documentation update.

### DeGray: full-file coverage closure

Two independent audits checked all newly returned archive payloads, then all 83 output names. The retained Linux case's 31 inputs and 83 outputs were physically rehashed to the frozen controls. The 949,422,101-byte Windows algae migration CSV matches the accepted 931,840,210-byte Linux file after CRLF-to-LF conversion alone, including every printed number, category and record.

For the 70,665,007-byte W2L file, only the pre-existing **72-byte `TITLE(11)` clock at zero-based offset 724** is excluded. `REAL*4 W2VER` followed by eleven `CHARACTER(72)` titles in `FORM='BINARY'` establishes that location; every other byte and the total length match. Binary scientific values were not separately decoded. Text rules permit newline conversion and only named SNP run/termination/CPU clocks and CPL/PRF model clocks; the returned DeGray CPL has no such clock occurrence. No floating tolerance, subnormal filter, interpolation, token deletion or new timestamp exclusion was added.

The compiler report is deliberately separate: original Windows version `20260000` / build `20260331`, versus Linux IFX 2026.1.1 build 20260724. Source/executable lineage still comes from the earlier 31-input return and official executable file-hash receipt. The new collection adds no Windows process-exit capture, runtime-module inventory or FP-state trace. It is not a matched-compiler OS-only causal experiment, nor a claim that all 83 raw files are byte-identical before normalization.

The numerical experiment supports compatibility for these observations. It does not establish physical accuracy superiority, validate the transient negative hydraulic-radius state, or settle the scientific policy of continuing after invalid results. No retry-geometry repair or default-profile promotion is included.

## Host, tooling and independent review

Initial package-regression host: Debian 13.6 x86-64, glibc 2.41, GCC 14.2.0, GNU ld 2.44 and Python 3.12.14. The compiler is IFX 2026.1.1 build 20260724. The toolchain lock binds 294 regular files and six bounded symlinks; build and run checks bind the exact installed runtime hashes. Final executables are ELF64 x86-64, require GLIBC symbols through 2.34 and have no RPATH/RUNPATH. These dependency checks do not substitute for an Ubuntu run.

The final synthetic suite has **39 passing tests** covering native success/failure/signal exits, missing or malformed FP receipts, scientific-byte and input changes, missing/extra outputs, prohibited normalization, Python-optimization rejection, byte-preserving source export and copy-only binary inspection. A deliberately changed linked object was rejected before any input staging or model launch.

Independent review confirmed source/profile identity, all final executable and relocation sections, build/runtime gates, six output inventories and comparisons, actual native exits and all three FP receipts. The raw evidence remains separate from this source-only tree. Content hashes identify the review without exposing private evidence locations:

- Accepted output controls: `a6628f75d8948d08be1f5cab455ba85d937ed4c163273374dcce1196a7d14784`
- Final pre-model gate: `608952f14bf240d757daa069a16afc82d76d31d9087c7b68f7c0f52afd602d9f`
- Final six-run independent review: `377d61d6ed6a6a261ef320a2da6578c27496312f2933cc952fbd4baffe3fa74f`

Ubuntu 24.04 qualification, broader case/features coverage and application-specific scientific acceptance remain open. The separate Ubuntu 26.04 receipt review and complete DeGray comparison do not approve Spokane residuals, settle the invalid-result continuation policy or promote the compatibility profile. Strict remains the default; public draft review is separate from the application owner's acceptance decision.
