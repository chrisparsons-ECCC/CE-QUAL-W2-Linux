# General-case and ensemble tooling (experimental)

This additive tooling change supplies `tools/run_case.py`, `tools/ensemble.py`,
and a small `tools/exec_solver.py` process-launch shim. The existing
`tools/run.py` remains the **unchanged, three-case qualification harness**.
Neither a general-case success nor a green CI badge establishes numerical
compatibility, scientific acceptance, or production readiness.

## Preserved boundary

The solver sources, floating-point settings, default profile, build recipes,
compiler/runtime lock, example inputs/manifests, accepted output controls and
existing regression tests are unchanged from commit
`5814786ef46b68e2bd735082a4b1b8d5c2ab778f`. The only existing configuration
changed is the **publication file allowlist**, which adds the explicitly named
new text files; no limits, secret-detection rules or numerical identities are
relaxed. Package `VERSION` stays unchanged; this tooling revision is identified
by its new Git commit, not a release tag or a production promotion.

The general runner calls the existing `run.load_build` gate. It requires the
same qualified build-directory layout, runtime installation and exact profile
identities. There is no CLI option to bypass this gate or supply an arbitrary
executable. Tests inject a synthetic build adapter in-process and execute
small fake solver processes; that test seam is not a supported runtime mode.
No additional Python packages or GNU Parallel installation are needed.

## Supported starting point

Use an already prepared, **Linux-ready, self-contained case**. Prepare each
scenario's input bytes outside this repository. This tool neither edits model
parameters nor automatically converts Windows filenames/control-file syntax.
List every input, including secondary control and boundary-condition files.
Do not list previous outputs as inputs.

Example layout (all execution and input directories outside the package):

```text
study/
  base.json
  lower-level.json
  scenarios.json
  base-inputs/
    w2_con.csv
    bathymetry.csv
    inflow.csv
  lower-level-inputs/
    ...
```

A case manifest is a UTF-8 JSON object. This is a **schema illustration**, not a
claim that these example filenames or header rows match your application:

```json
{
  "schema": 1,
  "description": "Baseline reservoir scenario",
  "input_dir": "base-inputs",
  "input_files": ["w2_con.csv", "bathymetry.csv", "inflow.csv"],
  "path_files": ["w2_con.csv"],
  "output_dirs": [],
  "required_outputs": ["timeseries.csv", "flowbalance.csv"],
  "completion": {
    "file": "timeseries.csv",
    "column": 0,
    "skip_rows": 3,
    "delimiter": ",",
    "end_time": 365.0,
    "tolerance": 0.0
  },
  "reject_text": [
    {"file": "warning.opt", "contains": ["FATAL"]}
  ]
}
```

`input_dir` is relative to the manifest (an absolute input directory is also
allowed). File names inside it must be relative POSIX paths. List exactly one
root `w2_con.csv` or `w2_con.npt`. `path_files` defaults to that control file;
explicitly add **every secondary text file containing input/output paths**.
The runner rejects symlinks, unsafe declared relative paths, and backslashes
or obvious absolute/parent-path references in the declared path-bearing text
files. It separately refuses a `debug.log` basename (case-insensitive) in JSON
manifest/receipt paths, declared file lists and generated inventories before
reading that excluded vendor-log file. It does not silently rewrite
paths, change case or create Windows literal-backslash aliases. `output_dirs`
creates only explicitly named, relative directories in the private model copy.

This lint is deliberately conservative and is **not a complete Fortran input
parser or an operating-system sandbox**. It cannot prove that an omitted
secondary control file lacks external references. Use trusted inputs and
inspect all path-bearing controls; live coupled COPY remains unsupported.
There is no arbitrary shell command, parameter-evaluation expression, or
executable hook in the manifest.

All required outputs must be newly generated, regular and nonempty; inputs
cannot double as declared outputs. Completion checks stream one selected
time-series file, skip exactly `skip_rows` physical header lines, parse the
zero-based `column`, reject malformed/nonfinite or decreasing times, and
compare its final time with `end_time` using the **explicitly supplied**
`tolerance`. Set `delimiter` to `null` for whitespace-separated data. Ordinary
E, D and Fortran omitted-E numeric exponents are supported. Select a suitable
monotonic time-series output: a repeatedly sectioned report may not qualify.
Ensure its output schedule actually includes the intended final time. This is
an execution-completion criterion, **not a tolerance for scientific agreement**.

`reject_text` checks case-insensitive literal strings line-by-line. Missing
optional diagnostic files are permitted; list a diagnostic in
`required_outputs` when its existence is mandatory. No scientific warning or
mass-balance tolerance is invented by the runner.

## Run a single case

From the package directory, first check inputs and the reviewed build without
creating a run directory or launching the solver:

```sh
python3 tools/run_case.py --manifest /path/to/study/base.json \
  --build /path/to/build-strict --profile strict --check-only
```

Then select a fresh directory:

```sh
python3 tools/run_case.py --manifest /path/to/study/base.json \
  --build /path/to/build-strict --profile strict \
  --run-dir /path/to/results/base-001 --timeout 7200
```

For the compatibility candidate, explicitly choose
`--profile windows-compatible-invalid-only` and the matching reviewed build.
The existing FP-receipt verifier is required; a missing/invalid receipt fails
closed. Strict retains its existing FP behaviour: a strict Detroit abort is a
**failed general-case execution**, not a successful simulation.

Inputs are byte-copied into `model/`, never symlinked or edited in place. Every
attempt records the recipe/fingerprint, build and executable identities,
input hashes, command/cwd, selected relevant environment, stdout/stderr,
native exit, elapsed time and execution checks. Successful attempts also hash
the complete model-file inventory and auxiliary receipts. Scientific
acceptance is always recorded as `NOT ASSESSED`.

The complete build/input/tooling fingerprint is checked again after staging,
immediately before launch, and after a zero native exit. This detects changes
between preflight and execution; it is not protection against a malicious
concurrent writer or a filesystem security sandbox. JSON manifests/receipts
must be regular non-symlink files, so FIFOs do not block before the timeout.

Every successful attempt also requires `observed-runtime.json`. The observer
waits within the normal launch/timeout loop until `/proc/<pid>/exe` identifies
the reviewed executable rather than the Python shim, then takes one bounded
maps snapshot using the existing capture routine. An observed pinned-library
path/hash mismatch fails execution checks. Missing libraries, observation
errors or a process too short to observe remain explicit gaps; an unavailable
observation is never reported as runtime verification. A success can therefore
have `runtime_pins_observed: false`. The receipt does not inventory every later
load or independently qualify a new case/platform. Keep these raw receipts
private: they contain local paths, selected environment and host details.

The runner uses a separate process session and an exec shim to disable core
dumps without using `preexec_fn` in worker threads. A timeout or graceful
cancellation sends TERM and then KILL to the solver process group, including
ordinary descendants. Processes deliberately escaping their session are
outside this guarantee. Timeout is in seconds from process launch (not
preflight or staging); the default is 86400 seconds. Single-case CLI exits:
0 for checked success, 1 for failure, 2 for preflight/usage failure, 124 for
timeout and 130 for cancellation. The native exit is retained separately,
including negative signal exits.

## Run an ensemble

`scenarios.json` references the case manifests, not model input directories:

```json
{
  "schema": 1,
  "cases": [
    {"id": "baseline", "manifest": "base.json"},
    {"id": "lower-level", "manifest": "lower-level.json"}
  ]
}
```

```sh
python3 tools/ensemble.py --manifest /path/to/study/scenarios.json \
  --build /path/to/build-strict --profile strict \
  --run-root /path/to/results/ensemble-001 --jobs 4 --timeout 7200 --retries 1
```

Concurrency defaults to one; choose an appropriate bound for available CPU,
RAM and storage. There are no hard CPU, RAM, disk-space or output-size quotas;
`--jobs` bounds concurrent cases, the timeout bounds elapsed execution, and
core dumps are disabled. `--retries 1` means **one additional attempt per case during
this invocation**, with a fresh `case-id/attempt-000002/` directory. A successful
retry stops further attempts. Failed files are preserved; no attempt directory
is overwritten. The summary is atomically updated in `ensemble-result.json`.

Repeat the command with `--resume` to skip only cases whose latest successful
attempt still passes all completion, input, output and receipt hash checks.
The exact profile-specific receipt set, capture exit, invocation profile and
runtime-observation status are rechecked; a success label or an empty receipt
index is insufficient.
A corrupted/missing output on a recorded successful run causes a fresh attempt,
not silent reuse or overwriting. Changed manifests, input bytes, reviewed
builds, relevant environment or tooling identities require a **new workspace**.
Jobs, timeout and retry count can change without changing model identity.

Ctrl-C or SIGTERM stops active solver groups, marks cancelled attempts and
prevents queued cases from launching. Resume restarts incomplete cases from
the beginning; it does **not** implement numerical checkpoint/restart.
A hard-killed launcher, machine failure or malformed/missing terminal receipt
is different: the tool refuses automatic recovery of that abandoned attempt.
Verify that no old worker remains, then use a fresh workspace. It does not
assume a stale timestamp proves a process has stopped.

One launcher holds an advisory `flock` on the workspace. Its filename remains
after exit; the kernel releases the lock. Never delete a live lock file to
bypass it. This first implementation targets a **single Linux host and local
filesystem**, not distributed/network-filesystem scheduling. Ensemble CLI
exits 0 only when all cases are successful or hash-verified skips, 1 when any
case fails, 2 for preflight/workspace errors, and 130 on cancellation.

## Lightweight CI and evidence limits

`.github/workflows/linux-tooling.yml` runs the existing and new synthetic
unittest suites on GitHub-hosted Ubuntu 24.04 with Python 3.11 and 3.14. It
pins the official checkout/setup actions by commit, uses read-only contents
permission, does not retain Git credentials, downloads no model inputs or
Intel compiler, and uses no repository secrets or self-hosted runner.
A diff guard checks the frozen scientific/build/regression boundary. The PR
trigger includes both `v4.5` (the current draft PR base) and `linux-port`; the
push trigger covers `linux-port` and `tooling/**`.

The workflow's Ubuntu label is only the **tooling-test host**; it does not
qualify the solver on Ubuntu 24.04 or 26.04. Existing documented model
comparisons are carried forward, not rerun by this change. Real-model
completion-column configuration, arbitrary case migration, numerical
comparison, performance measurement, scientific acceptance and production
promotion remain application-specific work. This change has only synthetic
launcher coverage: native serial and concurrent real-model checks on the Ubuntu 26.04 execution system remain pending. The prior model qualification applies to
the unchanged pinned harness, not to these new launchers.

Run the new tests locally with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_workflow_tools.py -v
```

Run the complete lightweight suite with `python3 -m unittest discover -s tests
-v`. Do not use Python optimization (`-O` or `PYTHONOPTIMIZE`) for execution or
verification: the frozen FP checks deliberately reject it.
