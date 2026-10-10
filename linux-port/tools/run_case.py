#!/usr/bin/env python3
"""Run an explicitly described, already Linux-ready case; no numerical acceptance."""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
PROFILES = ("strict", "windows-compatible-invalid-only")
SCHEMA = 1


def fail(message):
    raise ValueError(message)


def digest(path: Path) -> dict:
    path = Path(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        fail(f"Not a regular, non-symlink file: {path}")
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
            size += len(block)
    return {"bytes": size, "sha256": h.hexdigest()}


def identity(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode()).hexdigest()


def read_json(path: Path) -> dict:
    if Path(path).name.casefold() == "debug.log":
        fail("Excluded vendor-log name is not a JSON manifest or receipt")
    if not stat.S_ISREG(Path(path).lstat().st_mode):
        fail(f"Expected a regular, non-symlink JSON file: {path}")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    result = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                        parse_constant=lambda x: fail(f"Non-finite JSON value: {x}"))
    if not isinstance(result, dict):
        fail("Expected a JSON object")
    return result


def write_json(path: Path, value) -> None:
    """Atomically replace a status file in a runner-owned directory."""
    path = Path(path)
    if path.is_symlink():
        fail(f"Refusing symlinked status file: {path}")
    fd, tmp = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def clean_path(path: Path) -> Path:
    """Reject symlinks in every existing component, including the final one."""
    path = Path(os.path.abspath(path))
    for component in (path, *path.parents):
        if component.is_symlink():
            fail(f"Symlinked path is not supported: {component}")
    return path


def relative_name(value) -> str:
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        fail("Expected a nonempty relative file name")
    if "\\" in value or ":" in value:
        fail(f"Windows/backslash/colon path is unsupported: {value}")
    p = PurePosixPath(value)
    if p.name.casefold() == "debug.log":
        fail("Excluded vendor-log name is not a model input or output")
    if p.is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        fail(f"Unsafe relative path: {value}")
    return value


def names(value, label, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        fail(f"{label} must be {'a nonempty' if nonempty else 'a'} list")
    result = [relative_name(x) for x in value]
    if len(set(result)) != len(result):
        fail(f"Duplicate {label}")
    return result


def number(value, label, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(f"{label} must be finite")
    if minimum is not None and value < minimum:
        fail(f"{label} must be >= {minimum}")
    return float(value)


def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        fail(f"{label} must be an integer >= {minimum}")
    return value


def disjoint(a: Path, b: Path) -> bool:
    return a != b and a not in b.parents and b not in a.parents


def validate_spec(spec: dict) -> dict:
    allowed = {"schema", "input_dir", "input_files", "path_files", "output_dirs",
               "required_outputs", "completion", "reject_text", "description"}
    if set(spec) - allowed:
        fail(f"Unknown case keys: {sorted(set(spec) - allowed)}")
    if spec.get("schema") != SCHEMA or type(spec.get("schema")) is not int:
        fail("Case schema must be 1")
    if not isinstance(spec.get("input_dir"), str) or not spec["input_dir"]:
        fail("input_dir must be a nonempty path")
    inputs = names(spec.get("input_files"), "input_files", True)
    controls = set(inputs) & {"w2_con.csv", "w2_con.npt"}
    if len(controls) != 1:
        fail("List exactly one root control file: w2_con.csv or w2_con.npt")
    paths = names(spec.get("path_files", list(controls)), "path_files", True)
    if not controls.issubset(paths) or not set(paths).issubset(inputs):
        fail("path_files must include the control file and be listed inputs")
    dirs = names(spec.get("output_dirs", []), "output_dirs")
    outputs = names(spec.get("required_outputs"), "required_outputs", True)
    if set(inputs) & set(outputs):
        fail("An expected output cannot also be an input")
    comp = spec.get("completion")
    if not isinstance(comp, dict) or set(comp) != {"file", "column", "skip_rows", "delimiter", "end_time", "tolerance"}:
        fail("completion requires file, column, skip_rows, delimiter, end_time, tolerance")
    if relative_name(comp["file"]) not in outputs:
        fail("Completion file must be a required output")
    integer(comp["column"], "completion.column")
    integer(comp["skip_rows"], "completion.skip_rows")
    if comp["delimiter"] is not None and (not isinstance(comp["delimiter"], str)
            or len(comp["delimiter"]) != 1 or comp["delimiter"] in "\r\n\x00"):
        fail("delimiter must be one character or null for whitespace")
    number(comp["end_time"], "completion.end_time")
    number(comp["tolerance"], "completion.tolerance", 0)
    rejects = spec.get("reject_text", [])
    if not isinstance(rejects, list):
        fail("reject_text must be a list")
    for rule in rejects:
        if not isinstance(rule, dict) or set(rule) != {"file", "contains"}:
            fail("Each reject_text rule requires file and contains")
        relative_name(rule["file"])
        if (not isinstance(rule["contains"], list) or not rule["contains"]
                or any(not isinstance(x, str) or not x for x in rule["contains"])):
            fail("reject_text.contains must contain nonempty literal strings")
    return dict(spec, input_files=inputs, path_files=paths, output_dirs=dirs,
                required_outputs=outputs, reject_text=rejects)


def lint_paths(path: Path) -> None:
    """Conservative lexical lint, NOT a full control-file parser or sandbox."""
    unsafe = re.compile(r"(?:^|[\s,\"'=])(?:/|[A-Za-z]:[\\/])|(?:^|[\s,\"'=\/])\.\.(?=[\/\s,\"']|$)")
    with path.open(encoding="utf-8-sig", errors="strict") as stream:
        for line_no, line in enumerate(stream, 1):
            text = line.strip()
            if text.startswith(("!", "#")):
                continue
            if "\\" in text or unsafe.search(text):
                fail(f"Non-local/Windows path syntax in {path.name}:{line_no}; migrate explicitly")


def reviewed_build(directory: Path, profile: str) -> dict:
    """Reuse the frozen gate; there is deliberately no arbitrary-executable CLI."""
    if sys.flags.optimize:
        fail("Python -O/PYTHONOPTIMIZE is forbidden")
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        fail("The reviewed build requires Linux x86-64")
    import run as pinned
    meta_path, meta, exe, libraries, library_dir = pinned.load_build(directory, profile)
    env = dict(os.environ)
    for key in pinned.REMOVED_ENV:
        env.pop(key, None)
    env["LD_LIBRARY_PATH"] = str(library_dir)
    relevant = {k: v for k, v in env.items() if k.startswith(("OMP_", "KMP_", "MKL_", "W2_"))
                or k in ("LD_LIBRARY_PATH", "LC_ALL", "LC_NUMERIC", "LANG")}
    tools = ["run_case.py", "exec_solver.py", "run.py", "verify_fp_receipt.py", "support/case_capture.py"]
    provenance = {"build": str(directory), "build_receipt": digest(meta_path),
                  "profile": profile, "executable": digest(exe),
                  "runtime": {str(x): digest(x) for x in libraries},
                  "tools": {x: digest(TOOLS / x) for x in tools}, "environment": relevant}
    return {"exe": exe, "env": env, "provenance": provenance}


def prepare(manifest: Path, build: Path, profile: str) -> dict:
    if sys.flags.optimize:
        fail("Python -O/PYTHONOPTIMIZE is forbidden")
    if profile not in PROFILES:
        fail("An explicit reviewed profile is required")
    manifest = clean_path(manifest)
    spec = validate_spec(read_json(manifest))
    source = clean_path(manifest.parent / spec["input_dir"])
    build = clean_path(build)
    if not source.is_dir():
        fail("input_dir is not a directory")
    inventory = {}
    for name in spec["input_files"]:
        inventory[name] = digest(clean_path(source / name))
    for name in spec["path_files"]:
        lint_paths(source / name)
    runtime = reviewed_build(build, profile)
    recipe = {"schema": SCHEMA, "manifest": str(manifest), "manifest_digest": digest(manifest),
              "spec": spec, "source": str(source), "inputs": inventory,
              "build": runtime["provenance"]}
    return {"recipe": recipe, "fingerprint": identity(recipe), "runtime": runtime}


def inventory(directory: Path) -> dict:
    result = {}
    paths = sorted(directory.rglob("*"))
    if any(path.name.casefold() == "debug.log" for path in paths):
        fail("Unexpected excluded vendor-log name; no output sweep performed")
    for path in paths:
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode) or path.stat().st_nlink != 1:
            fail(f"Symlink, special file, or hard-linked result: {path}")
        result[path.relative_to(directory).as_posix()] = digest(path)
    return result


def parse_number(token: str) -> float:
    token = token.strip().replace("D", "E").replace("d", "e")
    if "e" not in token.lower():
        token = re.sub(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))([+-]\d{2,})$", r"\1E\2", token)
    result = float(token)
    if not math.isfinite(result):
        fail("Non-finite completion time")
    return result


def check_completion(model: Path, spec: dict) -> dict:
    for name in spec["required_outputs"]:
        if digest(clean_path(model / name))["bytes"] == 0:
            fail(f"Empty required output: {name}")
    comp = spec["completion"]
    last = None
    count = 0
    with (model / comp["file"]).open(encoding="utf-8-sig", errors="strict", newline="") as stream:
        for _ in range(comp["skip_rows"]):
            if not stream.readline():
                fail("Completion file ended in its declared header")
        rows = csv.reader(stream, delimiter=comp["delimiter"], skipinitialspace=True) if comp["delimiter"] else (line.split() for line in stream)
        for row in rows:
            if not row or all(not x.strip() for x in row):
                continue
            if len(row) <= comp["column"]:
                fail("Truncated completion row")
            current = parse_number(row[comp["column"]])
            if last is not None and current < last:
                fail("Completion times are not nondecreasing")
            last = current
            count += 1
    if last is None or abs(last - comp["end_time"]) > comp["tolerance"]:
        fail(f"Final time {last!r} does not match {comp['end_time']} within {comp['tolerance']}")
    for rule in spec["reject_text"]:
        path = clean_path(model / rule["file"])
        if path.exists():
            with path.open(encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    if any(token.casefold() in line.casefold() for token in rule["contains"]):
                        fail(f"Rejected diagnostic text in {rule['file']}")
    return {"final_time": last, "data_rows": count, "execution_checks_passed": True,
            "scientific_acceptance": "NOT ASSESSED"}


def stop_group(proc: subprocess.Popen) -> None:
    """Terminate the solver session, including ordinary descendants."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        pass
    # Kill remaining descendants even when their parent responded to TERM.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def verify_fp(attempt: Path) -> dict:
    from verify_fp_receipt import verify
    return verify(attempt)


def observe_runtime(pid: int, runtime: dict):
    """One maps snapshot after the exec shim becomes the reviewed executable."""
    try:
        if Path(f"/proc/{pid}/exe").resolve(strict=True) != Path(runtime["exe"]).resolve(strict=True):
            return None  # Still in the Python exec shim; never attribute its maps to the solver.
    except (OSError, RuntimeError):
        return None
    import run as pinned
    record = pinned.capture.observe_linux_runtime(pid)
    expected = runtime["provenance"].get("runtime", {})
    by_name = {Path(path).name: (path, row) for path, row in expected.items()}
    matched, errors = set(), []
    for row in record["libraries"]:
        name = Path(row["path"]).name
        if name in by_name:
            path, wanted = by_name[name]
            if row["path"] != path or {k: row[k] for k in ("bytes", "sha256")} != wanted:
                errors.append(f"Observed pinned runtime mismatch: {name}")
            else:
                matched.add(name)
    record.update(status="observed", pinned_runtime_verified=bool(by_name) and matched == set(by_name) and not errors,
                  missing_pinned_libraries=sorted(set(by_name) - matched), pinned_runtime_errors=errors)
    return record


def receipt_names(profile: str):
    names = {"recipe.json", "invocation.json", "capture.json", "stdout.txt", "stderr.txt", "observed-runtime.json"}
    if profile == "windows-compatible-invalid-only":
        names |= {"invalid-mask-receipt.txt", "fp-verification.json"}
    return names


def receipt_inventory(attempt: Path, profile: str):
    entries = list(attempt.iterdir())
    files = {p.name for p in entries if p.name != "run-result.json" and p.name != "model"}
    if files != receipt_names(profile):
        fail("Attempt receipt set differs from the required profile schema")
    return {name: digest(clean_path(attempt / name)) for name in sorted(files)}


def run_prepared(plan: dict, run_dir: Path, timeout: float, cancel=None) -> dict:
    timeout = number(timeout, "timeout", 0.001)
    cancel = cancel or threading.Event()
    run_dir = clean_path(run_dir)
    recipe, runtime = plan["recipe"], plan["runtime"]
    source, build = Path(recipe["source"]), Path(recipe["build"]["build"])
    for other in (source, build, ROOT):
        if not disjoint(run_dir, other):
            fail("Run directory must be outside the source, build, and package trees")
    if cancel.is_set():
        fail("Cancelled before staging")
    run_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    model = run_dir / "model"
    model.mkdir(mode=0o700)
    start = time.monotonic()
    result = {"schema": SCHEMA, "fingerprint": plan["fingerprint"], "status": "running",
              "started_utc": datetime.now(timezone.utc).isoformat(), "native_exit": None,
              "scientific_acceptance": "NOT ASSESSED", "errors": []}
    write_json(run_dir / "recipe.json", recipe)
    write_json(run_dir / "run-result.json", result)
    proc = None
    try:
        for name, expected in recipe["inputs"].items():
            target = model / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with clean_path(source / name).open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            if digest(target) != expected:
                fail(f"Input changed during staging: {name}")
        for name in recipe["spec"]["output_dirs"]:
            (model / name).mkdir(parents=True, exist_ok=True)
        current = prepare(Path(recipe["manifest"]), build, recipe["build"]["profile"])
        if current["fingerprint"] != plan["fingerprint"]:
            fail("Inputs, build, environment, or tooling changed during staging")
        runtime = current["runtime"]
        env = dict(runtime["env"])
        compatible = recipe["build"]["profile"] == "windows-compatible-invalid-only"
        if compatible:
            env["W2_INVALID_MASK_LOG"] = str(run_dir / "invalid-mask-receipt.txt")
        command = [sys.executable, str(TOOLS / "exec_solver.py"), str(runtime["exe"]), str(model)]
        write_json(run_dir / "invocation.json", {"argv": command, "cwd": str(model),
                   "only_authorized_mask_action": compatible, "timeout_seconds": timeout,
                   "core_dump_limit": 0, "profile": recipe["build"]["profile"]})
        if cancel.is_set():
            result["status"] = "cancelled"
            return result
        with (run_dir / "stdout.txt").open("xb") as stdout, (run_dir / "stderr.txt").open("xb") as stderr:
            proc = subprocess.Popen(command, cwd=model, env=env, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr, start_new_session=True)
            launched = time.monotonic()
            result["pid"] = proc.pid
            write_json(run_dir / "run-result.json", result)
            observation = None
            while proc.poll() is None:
                if observation is None:
                    observation = observe_runtime(proc.pid, runtime)
                    if observation is not None:
                        write_json(run_dir / "observed-runtime.json", observation)
                        if observation["pinned_runtime_errors"]:
                            fail("; ".join(observation["pinned_runtime_errors"]))
                if cancel.is_set() or time.monotonic() - launched >= timeout:
                    result["status"] = "cancelled" if cancel.is_set() else "timed_out"
                    stop_group(proc)
                    break
                time.sleep(0.05)
            result["native_exit"] = proc.wait()
            if observation is None:
                observation = {"status": "unavailable", "pinned_runtime_verified": False,
                               "reason": "No reviewed-executable maps snapshot before process exit or stop",
                               "scope": "One bounded best-effort observation; short processes may finish first"}
                write_json(run_dir / "observed-runtime.json", observation)
            result["runtime_pins_observed"] = observation["pinned_runtime_verified"]
        if result["status"] == "running":
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                pass
            else:
                stop_group(proc)
                fail("Solver left descendant processes in its session")
        write_json(run_dir / "capture.json", {"exit_code": result["native_exit"],
                   "scope": "General-case execution; not the pinned-example capture schema"})
        if result["status"] == "running":
            if result["native_exit"] != 0:
                fail(f"Native solver exit {result['native_exit']}")
            if prepare(Path(recipe["manifest"]), build, recipe["build"]["profile"])["fingerprint"] != plan["fingerprint"]:
                fail("Inputs, build, environment, or tooling changed during execution")
            if compatible:
                fp = verify_fp(run_dir)
                write_json(run_dir / "fp-verification.json", fp)
                result["fp_receipt_sha256"] = digest(run_dir / "invalid-mask-receipt.txt")["sha256"]
            observed = inventory(model)
            if any(observed.get(name) != row for name, row in recipe["inputs"].items()):
                fail("Staged inputs changed or disappeared during execution")
            result["completion"] = check_completion(model, recipe["spec"])
            result["model_inventory"] = observed
            result["receipt_inventory"] = receipt_inventory(run_dir, recipe["build"]["profile"])
            result["status"] = "cancelled" if cancel.is_set() else "success"
    except (OSError, ValueError, KeyError, AssertionError, csv.Error, subprocess.SubprocessError) as error:
        if proc is not None and proc.poll() is None:
            stop_group(proc)
        if proc is not None:
            result["native_exit"] = proc.returncode
        result["status"] = "failed"
        result["errors"].append(str(error))
    finally:
        if proc is not None and proc.poll() is None:
            stop_group(proc)
        result["elapsed_seconds"] = time.monotonic() - start
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(run_dir / "run-result.json", result)
    return result


def verified_success(attempt: Path, plan: dict) -> bool:
    """Never trust an old 'success' label without rechecking current file bytes."""
    try:
        result = read_json(clean_path(attempt / "run-result.json"))
        if result.get("status") != "success" or result.get("native_exit") != 0:
            return False
        if result.get("fingerprint") != plan["fingerprint"]:
            return False
        if read_json(clean_path(attempt / "recipe.json")) != plan["recipe"]:
            return False
        profile = plan["recipe"]["build"]["profile"]
        if not isinstance(result.get("receipt_inventory"), dict) or result["receipt_inventory"] != receipt_inventory(attempt, profile):
            return False
        capture = read_json(clean_path(attempt / "capture.json"))
        invocation = read_json(clean_path(attempt / "invocation.json"))
        observation = read_json(clean_path(attempt / "observed-runtime.json"))
        if (capture.get("exit_code") != 0 or invocation.get("profile") != profile
                or invocation.get("only_authorized_mask_action") is not (profile == "windows-compatible-invalid-only")
                or invocation.get("cwd") != str(attempt / "model")
                or invocation.get("argv") != [sys.executable, str(TOOLS / "exec_solver.py"), str(plan["runtime"]["exe"]), str(attempt / "model")]
                or observation.get("status") not in ("observed", "unavailable")
                or observation.get("pinned_runtime_errors")
                or type(observation.get("pinned_runtime_verified")) is not bool
                or result.get("runtime_pins_observed") != observation["pinned_runtime_verified"]):
            return False
        if inventory(clean_path(attempt / "model")) != result["model_inventory"]:
            return False
        if any(result["model_inventory"].get(k) != v for k, v in plan["recipe"]["inputs"].items()):
            return False
        if plan["recipe"]["build"]["profile"] == "windows-compatible-invalid-only":
            verify_fp(attempt)
            if digest(attempt / "invalid-mask-receipt.txt")["sha256"] != result["fp_receipt_sha256"]:
                return False
        check_completion(attempt / "model", plan["recipe"]["spec"])
        return True
    except (OSError, ValueError, KeyError, AssertionError, csv.Error):
        return False


@contextlib.contextmanager
def cancellation_signals(event):
    previous = {sig: signal.signal(sig, lambda *_: event.set()) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--timeout", type=float, default=86400)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.check_only and args.run_dir is None:
        parser.error("--run-dir is required unless --check-only")
    plan = prepare(args.manifest, args.build, args.profile)
    if args.check_only:
        print(json.dumps({"preflight": "passed", "fingerprint": plan["fingerprint"],
                          "scientific_acceptance": "NOT ASSESSED"}, indent=2))
        return 0
    event = threading.Event()
    with cancellation_signals(event):
        result = run_prepared(plan, args.run_dir, args.timeout, event)
    print(json.dumps(result, indent=2))
    return {"success": 0, "timed_out": 124, "cancelled": 130}.get(result["status"], 1)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, AssertionError) as error:
        print(f"CASE STOPPED: {error}", file=sys.stderr)
        sys.exit(2)
