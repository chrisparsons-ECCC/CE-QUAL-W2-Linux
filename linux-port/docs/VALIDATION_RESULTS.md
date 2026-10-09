# Validation results: 0.1.0-dev.20261009

The final packaged source, build recipe and runner passed six controlled Linux regressions on 2026-10-09. Across **262 generated files**, **242 were byte-identical** to their profile-specific controls and **20 differed only in previously audited clock fields**. There were no unexplained changes, missing outputs or extra scientific outputs. These are Debian-host results; native Ubuntu 24.04 qualification remains open.

## Final package runs

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

## Inherited Windows comparison scope

Exact reproduction of the accepted Linux candidate carries forward the following earlier comparisons. Their Windows authority is the supplied official-original executable, SHA256 `0eb294897682d6d3dabfac4ba6dc70fe96cfc29de7ebfdc75ffd6e6500edb163`. Spokane was additionally compared with the controlled IFX 2026.1.1 Windows rebuild, SHA256 `a60ce4691569d39408c39eb2a3e951b4b2c676a9a0932cdfd4d4ad8a80454aef`.

- **Detroit:** all 36 scientific outputs match the official-original Windows return using the earlier audited clocks, line-ending normalization and six explicit habitat-path correspondences. The 37th file is compiler metadata. This includes 378,950 TSR/FLOWBAL values and the complete binary result except its 72-byte clock. The candidate reaches day 365, iteration 129,144, with the same 122 timestep violations and 43 layer-warning records.
- **Spokane:** 71,418 table values and 104,631 semantic SNP fields match. Remaining differences concern the constituent named `9CBODP`: 9,410 aligned CPL tokens differ with maximum absolute difference `2.29246e-321`; 72 aligned nonprofile SNP tokens differ with maximum `4.5967667e-8` percentage points. That percent-error difference is not subnormal. Twenty-eight SNP lines retain explicit raw differences without supported field alignment. Spokane is not a whole-output exact Windows match.
- **DeGray:** all four available official Windows files, TSR, FLOWBAL, SNP and PRF, match under the earlier recorded comparisons. The run reaches iteration 42,365 with zero timestep violations. Seventy-seven wider Windows output counterparts remain unavailable; a whole-case Windows equality claim would exceed the evidence.

The numerical experiment supports compatibility for these observations. It does not establish physical accuracy superiority, validate the transient negative hydraulic-radius state, or settle the scientific policy of continuing after invalid results. No retry-geometry repair or default-profile promotion is included.

## Host, tooling and independent review

Actual qualification host: Debian 13.6 x86-64, glibc 2.41, GCC 14.2.0, GNU ld 2.44 and Python 3.12.14. The compiler is IFX 2026.1.1 build 20260724. The toolchain lock binds 294 regular files and six bounded symlinks; build and run checks bind the exact installed runtime hashes. Final executables are ELF64 x86-64, require GLIBC symbols through 2.34 and have no RPATH/RUNPATH. These dependency checks do not substitute for an Ubuntu run.

The final synthetic suite has **39 passing tests** covering native success/failure/signal exits, missing or malformed FP receipts, scientific-byte and input changes, missing/extra outputs, prohibited normalization, Python-optimization rejection, byte-preserving source export and copy-only binary inspection. A deliberately changed linked object was rejected before any input staging or model launch.

Independent review confirmed source/profile identity, all final executable and relocation sections, build/runtime gates, six output inventories and comparisons, actual native exits and all three FP receipts. The raw evidence remains separate from this source-only tree. Content hashes identify the review without exposing private evidence locations:

- Accepted output controls: `a6628f75d8948d08be1f5cab455ba85d937ed4c163273374dcce1196a7d14784`
- Final pre-model gate: `608952f14bf240d757daa069a16afc82d76d31d9087c7b68f7c0f52afd602d9f`
- Final six-run independent review: `377d61d6ed6a6a261ef320a2da6578c27496312f2933cc952fbd4baffe3fa74f`

Native Ubuntu qualification, broader case/features coverage and application-specific scientific acceptance remain open. Public draft review does not change those limits.
