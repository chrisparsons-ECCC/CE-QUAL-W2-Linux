# CE-QUAL-W2 4.5.5 Linux compatibility candidate

This source-only package preserves the native Linux port and adds an explicit, separately selected Windows-comparison profile. **Strict remains the default.** The compatibility profile contains the five previously reviewed real-power calls plus invalid-exception-only masking. It is a review candidate, not a production or physical-accuracy endorsement.

Development and controlled case runs were performed on Debian 13 x86-64. Ubuntu Server 24.04 x86-64 is the intended target and still requires on-target qualification. See [validation results](docs/VALIDATION_RESULTS.md), [validation policy](docs/VALIDATION_POLICY.md), [provenance](docs/PROVENANCE.md), and [notices](notices/README.md).

## Prerequisites

- Linux x86-64. ARM64 is not supported by the reviewed FP helper.
- Python 3.11 or newer, GCC/C development tools, GNU assembler/linker, `readelf` and `ldd` available under the normal system paths. No third-party Python packages are required.
- An already installed Intel IFX **2026.1.1, build 20260724**, matching `config/toolchain-lock.json`, including its Fortran interfaces and runtime libraries. The build tool checks the pinned component hashes, not just version text. It never installs software, accepts an agreement or downloads a compiler.
- Original pinned Spokane, Detroit and DeGray example inputs for the documented case runner. Inputs and large outputs are not part of this repository. Each case manifest verifies every input byte before launch.
- Space outside this source tree for builds and run evidence. Each DeGray run produces approximately 1 GB of output; keep at least several GB free when qualifying both profiles.

Intel lists Ubuntu 24.04 in its [2026 compiler requirements](https://www.intel.com/content/www/us/en/developer/articles/release-notes/fortran-compiler/2026.html). That compiler support does not establish this package's target validation. Ubuntu's [glibc package](https://packages.ubuntu.com/noble/libc6) is in the 2.39 series; the preserved development binaries' GLIBC symbol requirements reached 2.34, a prerequisite check only.

## Build without changing the default

Run commands from this package directory. Replace `/path/to/oneapi/compiler/2026.1/bin/ifx` with the exact installed compiler. Build directories must be fresh and outside the source package.

Plan the strict build without invoking any compiler:

```sh
python3 tools/build.py --ifx /path/to/oneapi/compiler/2026.1/bin/ifx --output ../build-strict
```

Build strict explicitly:

```sh
python3 tools/build.py --profile strict --ifx /path/to/oneapi/compiler/2026.1/bin/ifx --output ../build-strict --execute
```

Build the opt-in candidate:

```sh
python3 tools/build.py --profile windows-compatible-invalid-only --ifx /path/to/oneapi/compiler/2026.1/bin/ifx --output ../build-compatible --execute
```

The build records source hashes, compiler/system-tool identities, all commands, object/module hashes, actual runtime resolution and executable hash in `build.json`. Runtime files remain in the installed compiler tree; they are not copied into this package. If a check or compiler command fails, preserve that build directory and choose a fresh directory after resolving the cause.

The original numerical flags, including `-fpe0` and `-fp-model=source`, remain unchanged in both profiles. The `strict` name means the preserved baseline profile. The compatibility helper masks only invalid exceptions after Fortran runtime initialization. It preserves the other masks, precision, rounding, FTZ/DAZ and status bits. The compatibility recipe must recreate the accepted complete generated-interface context for the final temperature compilation; this is documented in the build profile and validation evidence. Build-date/time macros remain intact, so byte-identical whole executables are not promised.

## Run and validate the pinned examples

For inputs taken from the previously staged reference kit, use the default `--input-layout staged`. For the original example filenames, add `--input-layout original`. The runner makes a private byte-identical fixture, stages the required Linux filename aliases, and runs only in a fresh directory. Do not pre-create output subdirectories or overwrite an earlier run.

```sh
python3 tools/run.py --profile windows-compatible-invalid-only --build ../build-compatible --case spokane --inputs /path/to/inputs/spokane --run-dir ../runs/compatible-spokane-001
python3 tools/validate.py --profile windows-compatible-invalid-only --run-dir ../runs/compatible-spokane-001 --report ../runs/compatible-spokane-001-validation.json
```

Repeat with `--case detroit` and `--case degray`, their respective input directories, and fresh run/report names. To test strict, select `--profile strict` and `--build ../build-strict` in both commands.

The compatibility runner automatically creates the FP receipt path; no diagnostic environment-variable setup is required. The receipt remains a required control, and its directory must be writable. Strict uses the untouched strict CLI and has no mask helper or FP receipt dependency. Both profiles capture stdout/stderr, the actual native exit, input/output hashes and a bounded runtime-library observation.

The original strict Detroit case is expected to stop with floating-invalid error 65 before finishing. The wrapper reports native exit `-6` and returns shell status `134`; a separate strict validation pass means that known partial failure was reproduced, not that Detroit completed. Other nonzero native exits remain failures even if an FP receipt exists. A native success with invalid verification evidence returns a failing wrapper status.

Validation compares every generated output against the selected pinned Linux reference, allowing only previously audited run/build clocks and CPU-duration fields. It introduces no floating tolerance or line-ending conversion. A pass on an actual Ubuntu 24.04 run would provide new target evidence; the development host's pass must not be relabeled as Ubuntu testing.

## Scope and remaining limits

The accepted numerical experiment completed Detroit and matched all 36 official-original Windows scientific outputs. Spokane retained known tiny differences in the constituent named `9CBODP`; DeGray matched all four returned Windows scientific files, while 77 wider counterparts remain unavailable. Package qualification must reproduce that accepted Linux candidate before those observations are carried forward. See the current results record for completed gates.

Invalid masking allows transient invalid results to continue. The observed Detroit path stored NaNs and then the same finite turbulence floors as Windows. Compatibility does not establish that the negative-radius state, retry restoration or physical policy is correct. No geometry repair or broader numerical change is included.

The runner currently qualifies the three hash-pinned example cases. General case migration, live coupled COPY behavior, arbitrary Windows path conventions and production deployment are separate work. The original Linux boundary port rejects unsupported live COPY paths clearly.

## Review and version control

Run synthetic launcher/validator/publication tests without running the model:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Follow [Git workflow](docs/GIT_WORKFLOW.md) and [change control](docs/CHANGE_CONTROL.md). Preserve source line endings with the supplied `.gitattributes`. Keep compiler payloads, binaries, model inputs/outputs, private evidence locations, credentials and old repository metadata out of commits. Public draft review is separate from production acceptance and deployment.
