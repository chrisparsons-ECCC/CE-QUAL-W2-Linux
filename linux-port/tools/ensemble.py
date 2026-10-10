#!/usr/bin/env python3
"""Bounded, resumable case ensembles; restart cases, never simulation timesteps."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import threading
import time

import run_case as case


@contextlib.contextmanager
def workspace_lock(root: Path):
    """Local-filesystem advisory lock; its persistent filename is not a stale lock."""
    path = root / ".ensemble.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            case.fail("Another launcher holds this ensemble workspace")
        yield
    finally:
        os.close(fd)


def load_ensemble(path: Path):
    path = case.clean_path(path)
    spec = case.read_json(path)
    if set(spec) != {"schema", "cases"} or type(spec["schema"]) is not int or spec["schema"] != 1:
        case.fail("Ensemble requires schema: 1 and cases")
    if not isinstance(spec["cases"], list) or not spec["cases"]:
        case.fail("cases must be a nonempty list")
    result = []
    seen = set()
    for row in spec["cases"]:
        if not isinstance(row, dict) or set(row) != {"id", "manifest"}:
            case.fail("Each case requires id and manifest")
        name = row["id"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", name):
            case.fail("Case IDs must be simple ASCII names, at most 80 characters")
        if name in {"ensemble.json", "ensemble-result.json"}:
            case.fail(f"Case ID collides with a workspace receipt: {name}")
        if name in seen:
            case.fail(f"Duplicate case ID: {name}")
        seen.add(name)
        relative = case.relative_name(row["manifest"])
        result.append((name, case.clean_path(path.parent / relative)))
    return result


def prior_attempts(folder: Path):
    found = []
    if folder.exists():
        for path in folder.iterdir():
            case.clean_path(path)
            match = re.fullmatch(r"attempt-(\d{6})", path.name)
            if not match or not path.is_dir():
                case.fail(f"Unexpected entry in case attempt directory: {path.name}")
            result_file = path / "run-result.json"
            if not result_file.exists():
                case.fail(f"Incomplete attempt {path}; verify no worker remains and use a fresh workspace")
            result = case.read_json(case.clean_path(result_file))
            if result.get("status") not in {"success", "failed", "timed_out", "cancelled"}:
                case.fail(f"Unfinished attempt {path}; verify no worker remains and use a fresh workspace")
            found.append((int(match[1]), path))
    return sorted(found)


def execute(manifest: Path, build: Path, profile: str, root: Path,
            jobs=1, retries=0, timeout=86400, resume=False, cancel=None):
    case.integer(jobs, "jobs", 1)
    case.integer(retries, "retries", 0)
    case.number(timeout, "timeout", 0.001)
    cancel = cancel or threading.Event()
    entries = load_ensemble(manifest)
    plans = {name: case.prepare(path, build, profile) for name, path in entries}
    root = case.clean_path(root)
    for plan in plans.values():
        for other in (Path(plan["recipe"]["source"]), Path(plan["recipe"]["build"]["build"]), case.ROOT):
            if not case.disjoint(root, other):
                case.fail("Workspace must be outside all input, build, and package trees")
    envelope = {"schema": 1, "manifest": str(case.clean_path(manifest)),
                "manifest_digest": case.digest(manifest),
                "ensemble_tool": case.digest(Path(__file__)),
                "cases": {name: plan["fingerprint"] for name, plan in plans.items()}}
    if resume:
        if not root.is_dir():
            case.fail("--resume requires an existing ensemble workspace")
    else:
        root.mkdir(parents=True, mode=0o700, exist_ok=False)
    with workspace_lock(root):
        receipt = root / "ensemble.json"
        if resume:
            if case.read_json(case.clean_path(receipt)) != envelope:
                case.fail("Manifest, inputs, build, environment, or tooling changed; choose a new workspace")
        else:
            case.write_json(receipt, envelope)
        # Refuse abandoned/in-progress attempts before launching any new work.
        attempts = {name: prior_attempts(case.clean_path(root / name)) for name in plans}
        started = time.monotonic()
        summary = {"schema": 1, "jobs": jobs, "retries_per_case": retries,
                   "cases": {name: {"status": "pending"} for name in plans},
                   "scientific_acceptance": "NOT ASSESSED"}
        case.write_json(root / "ensemble-result.json", summary)

        def worker(name, path):
            plan = plans[name]
            previous = attempts[name]
            if previous and case.verified_success(previous[-1][1], plan):
                return {"status": "skipped_verified", "attempt": str(previous[-1][1]), "new_attempts": 0}
            next_number = previous[-1][0] + 1 if previous else 1
            folder = root / name
            folder.mkdir(mode=0o700, exist_ok=True)
            for retry in range(retries + 1):
                if cancel.is_set():
                    return {"status": "cancelled", "new_attempts": retry}
                # Pin source/build identities again immediately before every attempt.
                current = case.prepare(path, build, profile)
                if current["fingerprint"] != plan["fingerprint"]:
                    case.fail(f"Inputs or build changed after preflight: {name}")
                number = next_number + retry
                if number > 999999:
                    case.fail("Attempt numbering exhausted; choose a new workspace")
                destination = folder / f"attempt-{number:06d}"
                result = case.run_prepared(current, destination, timeout, cancel)
                row = {"status": result["status"], "attempt": str(destination),
                       "new_attempts": retry + 1, "native_exit": result["native_exit"],
                       "errors": result["errors"]}
                if result["status"] in ("success", "cancelled"):
                    return row
            return row

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(worker, name, path): name for name, path in entries}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    summary["cases"][name] = future.result()
                except Exception as error:
                    summary["cases"][name] = {"status": "failed", "errors": [str(error)]}
                summary["elapsed_seconds"] = time.monotonic() - started
                case.write_json(root / "ensemble-result.json", summary)
        summary["all_execution_checks_passed"] = all(
            row["status"] in ("success", "skipped_verified") for row in summary["cases"].values())
        summary["cancelled"] = cancel.is_set()
        case.write_json(root / "ensemble-result.json", summary)
        return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--profile", required=True, choices=case.PROFILES)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=86400)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    event = threading.Event()
    with case.cancellation_signals(event):
        summary = execute(args.manifest, args.build, args.profile, args.run_root,
                          args.jobs, args.retries, args.timeout, args.resume, event)
    print(json.dumps(summary, indent=2))
    return 130 if summary["cancelled"] else (0 if summary["all_execution_checks_passed"] else 1)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, AssertionError) as error:
        print(f"ENSEMBLE STOPPED: {error}", file=sys.stderr)
        sys.exit(2)
