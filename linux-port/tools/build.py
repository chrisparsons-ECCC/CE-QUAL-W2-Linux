#!/usr/bin/env python3
"""Plan, or explicitly execute, a clean pinned CE-QUAL-W2 source build.

This script never launches the resulting model. No runtime files are copied.
Only Python's standard library is needed. The installed IFX compiler and system
C compiler, assembler, linker, readelf, and ldd remain external prerequisites.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("strict", "windows-compatible-invalid-only")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def file_record(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": sha256(path), "bytes": path.stat().st_size}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def verify_sources(directory: Path, expected: dict) -> dict:
    actual = {}
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Source directory contains a non-regular file: {path}")
        actual[path.name] = sha256(path)
    if actual != expected or len(actual) != 52:
        changed = sorted(k for k in set(actual) | set(expected) if actual.get(k) != expected.get(k))
        raise ValueError(f"The exact 52-file source manifest does not match: {changed}")
    return actual


def resolve_program(value: str) -> Path:
    found = shutil.which(value)
    if found is None:
        raise ValueError(f"Required program not found or not executable: {value}")
    return Path(found).resolve(strict=True)


def verify_toolchain(compiler: Path, lock: dict) -> tuple[Path, dict, dict]:
    compiler_root = compiler.parent.parent
    if compiler != compiler_root / lock["compiler_relative_path"]:
        raise ValueError("--ifx must resolve to the installed compiler root's bin/ifx")
    verified = {}
    for relative, expected in lock["expected_sha256"].items():
        path = compiler_root / relative
        if path.is_symlink() or not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Pinned compiler component is missing or differs: {relative}")
        verified[relative] = file_record(path)
    for relative, expected in lock["expected_symlinks"].items():
        path = compiler_root / relative
        if not path.is_symlink():
            raise ValueError(f"Pinned compiler symlink is missing: {relative}")
        target = os.readlink(path)
        if (target != expected["target"] or
                hashlib.sha256(os.fsencode(target)).hexdigest() != expected["target_text_sha256"] or
                not path.is_file() or compiler_root not in path.resolve().parents):
            raise ValueError(f"Pinned compiler symlink is changed or unbounded: {relative}")
        verified[relative] = {"path": str(path), **expected, "resolved": file_record(path)}
    library_dir = compiler_root / lock["runtime_relative_directory"]
    runtime = {"library_dir": str(library_dir), "libraries": {}}
    for name, expected in lock["runtime_libraries"].items():
        record = file_record(library_dir / name)
        if record["sha256"] != expected:
            raise ValueError(f"Pinned installed runtime differs: {name}")
        runtime["libraries"][name] = record
    return compiler_root, verified, runtime


def build_environment(library_dir: str) -> dict[str, str]:
    # An allowlist prevents ambient FP switches, search paths, compiler overrides,
    # LD_PRELOAD/LD_AUDIT, and W2_* controls from changing the recorded build.
    return {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
            "LD_LIBRARY_PATH": library_dir}


def prepare_plan(args: argparse.Namespace) -> tuple[dict, dict, dict]:
    config = read_json(ROOT / "config/build-profiles.json")
    lock = read_json(ROOT / "config/toolchain-lock.json")
    profile = config["profiles"][args.profile]
    manifest_path = ROOT / profile["source_manifest"]
    manifest = read_json(manifest_path)
    if manifest["profile"] != args.profile or config["default_profile"] != "strict":
        raise ValueError("Profile manifest identity mismatch")
    source = ROOT / manifest["directory"]
    source_hashes = verify_sources(source, manifest["files"])
    units = config["compile_units"]
    if len(units) != 51 or len({u["source"] for u in units}) != 51:
        raise ValueError("Exactly 51 distinct compile units are required")
    if set(u["source"] for u in units) != set(source_hashes) - {"Resource.fd"}:
        raise ValueError("Compile units must match the 52-file source map excluding Resource.fd")
    if [u["object"] for u in units] != config["fortran_link_order"]:
        raise ValueError("Frozen compile and link object orders differ")
    output = Path(args.output).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(f"Output must be a new directory: {output}")
    if output == ROOT or ROOT in output.resolve().parents:
        raise ValueError("Keep build output outside the source-only package")
    compiler = resolve_program(args.ifx)
    compiler_root, verified, runtime = verify_toolchain(compiler, lock)
    cc = resolve_program(args.cc) if profile["invalid_mask_helper"] else None
    target_source = output / "source"
    objects = output / "objects"
    commands = []
    helper = config["helper"]
    if profile["invalid_mask_helper"]:
        if sha256(ROOT / helper["source"]) != helper["sha256"]:
            raise ValueError("Frozen compatibility helper checksum mismatch")
        commands.append({"label": "helper", "kind": "compile-c",
                         "argv": [str(cc), *helper["flags"], "-c", str(output / "helper/w2_invalid_mask.c"),
                                  "-o", str(objects / helper["object"])], "cwd": str(objects)})
    for unit in units:
        commands.append({"label": Path(unit["object"]).stem, "kind": "compile-fortran", "source": unit["source"],
                         "argv": [str(compiler), *config["common_flags"],
                                  *config["per_file_flags"].get(unit["source"], []),
                                  config["cli_definition"], "-I" + str(target_source), "-c",
                                  str(target_source / unit["source"]), "-o", str(objects / unit["object"])],
                         "cwd": str(objects)})
    repeat_units = profile["post_interface_recompile_units"]
    if repeat_units != (["temperature.F90"] if profile["invalid_mask_helper"] else []):
        raise ValueError("Only the compatibility profile's reviewed temperature interface pass is allowed")
    for source_name in repeat_units:
        original = next(c for c in commands if c.get("source") == source_name)
        commands.append({**original, "label": original["label"] + "-complete-interfaces",
                         "kind": "recompile-fortran", "argv": list(original["argv"])})
    order = list(config["fortran_link_order"])
    if profile["invalid_mask_helper"]:
        order.append(helper["object"])
    commands.append({"label": "link", "kind": "link", "argv": [str(compiler), *config["common_flags"],
                     *[str(objects / name) for name in order], "-Wl,-Map=" + str(output / "w2.map"),
                     "-o", str(output / "w2")], "cwd": str(objects)})
    os_release = Path("/etc/os-release")
    plan = {"format": "cequal-build-plan-v1", "profile": args.profile, "status": "planned",
            "output": str(output), "package_root": str(ROOT), "source_directory": str(source),
            "source_sha256": source_hashes, "source_manifest": file_record(manifest_path),
            "config": file_record(ROOT / "config/build-profiles.json"),
            "toolchain_lock": file_record(ROOT / "config/toolchain-lock.json"),
            "build_script": file_record(Path(__file__).resolve()),
            "host": {"platform": platform.platform(), "machine": platform.machine(), "system": platform.system(),
                     "os_release": os_release.read_text() if os_release.exists() else None,
                     "python": sys.version},
            "compiler": {"path": str(compiler), "root": str(compiler_root), "sha256": sha256(compiler),
                         "expected_version": lock["compiler_version"], "verified_components": verified},
            "cc": file_record(cc) if cc else None,
            "runtime": runtime, "environment": build_environment(runtime["library_dir"]),
            "compile_units": units, "link_object_order": order, "commands": commands,
            "post_interface_recompile_units": repeat_units,
            "common_flags": config["common_flags"], "per_file_flags": config["per_file_flags"],
            "model_executed": False, "runtime_copied": False, "binary_reproducibility": config["binary_reproducibility"]}
    if profile["invalid_mask_helper"]:
        plan["helper_sha256"] = helper["sha256"]
        plan["helper_flags"] = helper["flags"]
    return plan, config, lock


def execute(plan: dict, config: dict, lock: dict) -> dict:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("This reviewed build recipe supports Linux x86_64 only")
    output = Path(plan["output"])
    # mkdir is exclusive. Interrupted and failed outputs are retained for review;
    # there is deliberately no reuse/overwrite/resume path.
    output.mkdir(parents=True, exist_ok=False)
    for name in ("source", "objects", "logs", "tmp"):
        (output / name).mkdir()
    env = dict(plan["environment"], TMPDIR=str(output / "tmp"))
    report = dict(plan, format="cequal-build-record-v1", status="building", created_utc=utc_now(),
                  commands=[], environment=env)
    write_json(output / "build-plan.json", plan)
    write_json(output / "build.json", report)

    def invoke(argv: list[str], label: str, cwd: Path, kind: str) -> dict:
        start = utc_now()
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = output / "logs" / (label + ".stdout")
        stderr = output / "logs" / (label + ".stderr")
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        command = {"argv": argv, "cwd": str(cwd), "kind": kind, "started_utc": start, "finished_utc": utc_now(),
                   "returncode": result.returncode, "stdout": str(stdout.relative_to(output)),
                   "stderr": str(stderr.relative_to(output)), "stdout_sha256": sha256(stdout), "stderr_sha256": sha256(stderr)}
        report["commands"].append(command)
        write_json(output / "build.json", report)
        if result.returncode:
            raise RuntimeError(f"{label} failed with exit code {result.returncode}; see {stderr}")
        return {"stdout": result.stdout.decode("utf-8", errors="replace"),
                "stderr": result.stderr.decode("utf-8", errors="replace")}

    def inspect_executable(tool: str, options: list[str], label: str) -> dict:
        # Inspection tools only receive a disposable copy. Hash guards make an
        # accidental modification explicit even when a tool reports success.
        original = output / "w2"
        before = file_record(original)
        workspace = output / "inspection" / label
        workspace.mkdir(parents=True, exist_ok=False)
        copied = workspace / "w2"
        shutil.copy2(original, copied)
        copy_before = file_record(copied)
        if copy_before["sha256"] != before["sha256"]:
            raise ValueError("Executable inspection copy differs from its original")
        receipt = {"label": label, "original_before": before,
                   "copy_before": copy_before, "original_preserved": False}
        report.setdefault("binary_inspections", []).append(receipt)
        try:
            return invoke([report["system_tools"][tool]["path"], *options, str(copied)],
                          label, workspace, "artifact-inspection")
        finally:
            receipt["original_after"] = file_record(original)
            receipt["copy_after"] = file_record(copied)
            receipt["original_preserved"] = receipt["original_after"] == before
            receipt["copy_preserved"] = receipt["copy_after"] == copy_before
            write_json(output / "build.json", report)
            if not receipt["original_preserved"]:
                raise ValueError(f"Original executable changed during {label}; preserve and review all artifacts")
            if not receipt["copy_preserved"]:
                raise ValueError(f"Inspection copy changed during read-only {label}; preserve and review artifacts")

    try:
        for name in plan["source_sha256"]:
            shutil.copyfile(Path(plan["source_directory"]) / name, output / "source" / name)
        verify_sources(output / "source", plan["source_sha256"])
        if "helper_sha256" in plan:
            (output / "helper").mkdir()
            shutil.copyfile(ROOT / config["helper"]["source"], output / "helper/w2_invalid_mask.c")
            if sha256(output / "helper/w2_invalid_mask.c") != plan["helper_sha256"]:
                raise ValueError("Copied compatibility helper checksum mismatch")
        version = invoke([plan["compiler"]["path"], "--version"], "ifx-version", output, "tool-identity")
        if lock["compiler_version"] not in version["stdout"].splitlines():
            raise ValueError("IFX version/build string does not match the accepted compiler")
        report["compiler"]["actual_version"] = version
        if plan["cc"]:
            report["cc"]["version"] = invoke([plan["cc"]["path"], "--version"], "cc-version", output, "tool-identity")
        report["system_tools"] = {}
        for tool in ("gcc", "as", "ld", "readelf", "ldd"):
            path = resolve_program("/usr/bin/" + tool)
            report["system_tools"][tool] = dict(file_record(path), version=invoke([str(path), "--version"], tool + "-version", output, "tool-identity"))
        for command in plan["commands"]:
            repeated = None
            if command["kind"] == "recompile-fortran":
                object_path = Path(command["argv"][-1])
                preserved = output / "passes" / "initial" / object_path.name
                preserved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(object_path, preserved)
                repeated = {"source": command["source"], "initial_object": file_record(preserved),
                            "module_sha256_before": {p.name: sha256(p) for p in sorted((output / "objects").glob("*.mod"))},
                            "argv": command["argv"], "cwd": command["cwd"]}
                report.setdefault("interface_recompilations", []).append(repeated)
            invoke(command["argv"], command["label"], Path(command["cwd"]), command["kind"])
            if repeated is not None:
                repeated["final_object"] = file_record(object_path)
            print(f"{plan['profile']}: {command['label']} complete", file=sys.stderr, flush=True)
        verify_sources(output / "source", plan["source_sha256"])
        verify_sources(Path(plan["source_directory"]), plan["source_sha256"])
        verify_toolchain(Path(plan["compiler"]["path"]), lock)
        report["objects"] = {name: file_record(output / "objects" / name) for name in plan["link_object_order"]}
        report["executable"] = file_record(output / "w2")
        report["link_map"] = file_record(output / "w2.map")
        report["module_files"] = {p.name: file_record(p) for p in sorted((output / "objects").glob("*.mod"))}
        # Record actual external static archives, shared libraries and startup
        # objects selected by the linker, including system files not pinned here.
        linked_files = {}
        for line in (output / "w2.map").read_text(errors="replace").splitlines():
            if line.startswith("LOAD "):
                path = Path(line[5:].strip())
                if path.is_file() and output not in path.resolve().parents:
                    linked_files[str(path)] = file_record(path)
        report["linked_external_files"] = linked_files
        elf = inspect_executable("readelf", ["-d"], "elf-dynamic")
        report["elf_dynamic"] = elf["stdout"]
        deps = inspect_executable("ldd", [], "runtime-resolution")
        if "not found" in deps["stdout"]:
            raise ValueError("A runtime library could not be resolved")
        resolved = {}
        for line in deps["stdout"].splitlines():
            match = re.match(r"\s*(\S+)\s+=>\s+(/\S+)\s+\(", line)
            if match:
                resolved[match.group(1)] = file_record(Path(match.group(2)))
            else:
                match = re.match(r"\s*(/\S+)\s+\(", line)
                if match:
                    resolved[Path(match.group(1)).name] = file_record(Path(match.group(1)))
        for name, expected in report["runtime"]["libraries"].items():
            if resolved.get(name) != expected:
                raise ValueError(f"Runtime binding does not resolve to the pinned installed library: {name}")
        report["resolved_runtime_libraries"] = resolved
        report["status"] = "complete"
        report["finished_utc"] = utc_now()
        report["full_clean_build"] = True
        report["fortran_units_compiled"] = 51
        report["fortran_compile_invocations"] = sum(c["kind"] in ("compile-fortran", "recompile-fortran")
                                                     for c in report["commands"])
        write_json(output / "build.json", report)
        return report
    except BaseException as error:
        report["status"] = "failed"
        report["finished_utc"] = utc_now()
        report["error"] = str(error)
        write_json(output / "build.json", report)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="strict")
    parser.add_argument("--ifx", required=True, help="Installed IFX 2026.1.1 build 20260724 bin/ifx path")
    parser.add_argument("--cc", default="cc", help="C compiler for the compatibility helper (default: cc)")
    parser.add_argument("--output", required=True, help="Fresh build directory outside the source package")
    parser.add_argument("--execute", action="store_true", help="Execute the reviewed plan; otherwise only print it")
    args = parser.parse_args(argv)
    try:
        plan, config, lock = prepare_plan(args)
        if args.execute:
            result = execute(plan, config, lock)
            print(json.dumps({"status": result["status"], "profile": result["profile"],
                              "build_record": str(Path(plan["output"]) / "build.json"),
                              "executable": result["executable"], "model_executed": False}, indent=2))
        else:
            print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"Build refused or failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
