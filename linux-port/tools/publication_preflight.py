#!/usr/bin/env python3
"""Read-only, bounded publication-content preflight; no remote or Git mutation.

Only explicitly allowlisted text files are opened. Rejected/unknown paths,
including raw logs, are reported by name without opening their contents.
The index mode scans actual staged blobs, not worktree substitutes. This is
not a scan of historical commits and cannot grant publication permission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

POLICY = "config/publication-allowlist.json"
MAX_POLICY_BYTES = 64 * 1024
DENIED_PARTS = {".aws", ".ssh", ".git", ".env", "intel", "oneapi", "runtime",
                "runs", "outputs", "build", "builds", "vendor", "__pycache__"}
DENIED_SUFFIX = re.compile(r"(?:\.(?:log|stdout|stderr|o|obj|mod|smod|a|lib|dll|exe|pdb|zip|gz|xz|tar|csv|npt|pyc|pem|key|p12|pfx|kdbx)|\.so(?:\.[0-9.]+)?)$", re.I)
SECRET_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")),
    ("github_credential", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,})\b")),
    ("openai_credential", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{25,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("credential_assignment", re.compile(r"(?im)\b(?:password|access_token|api_key|secret_key)\s*[:=]\s*[\"']?[A-Za-z0-9_+/=-]{20,}")),
    ("credential_in_url", re.compile(r"https?://[^\s/@:]+:[^\s/@]+@", re.I)),
    ("private_library_reference", re.compile(r"\b(?:library_file_[A-Za-z0-9_-]{8,}|sediment://file_[A-Za-z0-9_-]+)\b")),
    ("private_storage_url", re.compile(r"https?://[^\s\"'<>]*(?:oaiusercontent\.com|blob\.core\.windows\.net|s3\.[^/]+\.amazonaws\.com)(?:/[^\s\"'<>]*)?", re.I)),
    ("private_chatgpt_file_url", re.compile(r"https?://chatgpt\.com/(?:backend-api/|library/|files/)[^\s\"'<>]*", re.I)),
    ("private_workspace_path", re.compile(r"/(?:workspace|home/agent|root)/[A-Za-z0-9_. /-]+")),
]


def safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("invalid relative allowlist path")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in {"", ".", ".."} for x in value.split("/")):
        raise ValueError("invalid relative allowlist path")
    return str(p)


def denied_path(path: str) -> bool:
    p = PurePosixPath(path)
    return (any(x.lower() in DENIED_PARTS for x in p.parts)
            or p.name.lower().startswith(".env")
            or bool(DENIED_SUFFIX.search(path)))


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


class Worktree:
    def __init__(self, root: Path):
        self.root = root
        self.entries: dict[str, tuple[str, int]] = {}
        for current, dirs, files in os.walk(root, followlinks=False):
            for name in list(dirs):
                p = Path(current) / name
                rel = p.relative_to(root).as_posix()
                if rel == ".git":
                    dirs.remove(name)  # Do not inspect metadata or historical objects.
                elif p.is_symlink():
                    self.entries[rel] = ("symlink", 0)
                    dirs.remove(name)
            for name in files:
                p = Path(current) / name
                rel = p.relative_to(root).as_posix()
                if rel == ".git":
                    continue
                st = p.lstat()
                kind = "regular" if stat.S_ISREG(st.st_mode) else "nonregular"
                self.entries[rel] = (kind, st.st_size)

    def read(self, path: str, limit: int) -> bytes:
        if self.entries.get(path, (None, 0))[0] != "regular":
            raise ValueError("file is missing or not regular")
        if self.entries[path][1] > limit:
            raise ValueError("file exceeds size limit")
        # O_NOFOLLOW protects the final component; verify parents too.
        p = self.root / path
        for parent in p.parents:
            if parent == self.root:
                break
            if parent.is_symlink():
                raise ValueError("symlink parent")
        fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                raise ValueError("file is not regular")
            data = f.read(limit + 1)
        if len(data) > limit:
            raise ValueError("file exceeds size limit")
        return data


class Index:
    def __init__(self, root: Path, repo_root: Path | None = None):
        repository = (repo_root or root).resolve()
        if not (repository / ".git").exists():
            raise ValueError("index mode requires an explicit repository root")
        prefix = root.relative_to(repository).as_posix()
        prefix = "" if prefix == "." else prefix + "/"
        top = Path(os.fsdecode(git(repository, "rev-parse", "--show-toplevel").strip())).resolve()
        if top != repository:
            raise ValueError("refusing an enclosing or different Git repository")
        self.root = repository
        self.package_prefix = prefix
        self.entries: dict[str, tuple[str, int]] = {}
        self.blobs: dict[str, str] = {}
        selection = ("--", prefix) if prefix else ()
        for record in git(repository, "ls-files", "--stage", "-z", *selection).split(b"\0"):
            if not record:
                continue
            header, path_bytes = record.split(b"\t", 1)
            mode, oid, stage = header.decode("ascii").split()
            full_path = safe_path(os.fsdecode(path_bytes))
            if prefix and not full_path.startswith(prefix):
                raise ValueError("Git returned a path outside the package scope")
            path = safe_path(full_path[len(prefix):])
            regular = mode in {"100644", "100755"} and stage == "0"
            kind = "regular" if regular else "nonregular_or_unmerged"
            self.blobs[path] = oid
            # Obtain a size, never a denied path's contents.
            size = int(git(repository, "cat-file", "-s", oid)) if regular else 0
            self.entries[path] = (kind, size)

    def read(self, path: str, limit: int) -> bytes:
        if self.entries.get(path, (None, 0))[0] != "regular":
            raise ValueError("file is missing or not regular")
        if self.entries[path][1] > limit:
            raise ValueError("file exceeds size limit")
        return git(self.root, "cat-file", "blob", self.blobs[path])


def audit(reader) -> dict:
    problems = []
    def problem(path, kind, **extra):
        problems.append({"path": path, "kind": kind, **extra})
    policy = json.loads(reader.read(POLICY, MAX_POLICY_BYTES))
    if policy.get("format") != "cequal-publication-allowlist-v1":
        raise ValueError("unsupported publication allowlist")
    limit = policy.get("maximum_file_bytes", 2 * 1024 * 1024)
    if not isinstance(limit, int) or not 1 <= limit <= 2 * 1024 * 1024:
        raise ValueError("invalid maximum file size")
    allowed = {safe_path(p) for p in policy["files"]}
    required = {safe_path(p) for p in policy["required_files"]}
    required.add(POLICY)
    allowed.add(POLICY)
    expected_hashes = {}
    for rel in policy["source_manifests"]:
        rel = safe_path(rel)
        if rel not in allowed or denied_path(rel):
            raise ValueError("source manifest is not safely allowlisted")
        manifest = json.loads(reader.read(rel, limit))
        base = safe_path(manifest["directory"])
        if not base.startswith("source/"):
            raise ValueError("source manifest directory is outside source")
        for name, digest in manifest["files"].items():
            path = safe_path(base + "/" + safe_path(name))
            if not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("invalid source hash")
            expected_hashes[path] = digest
            allowed.add(path)
            required.add(path)
    for path, digest in policy.get("additional_pinned_files", {}).items():
        path = safe_path(path)
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("invalid pinned-file hash")
        expected_hashes[path] = digest
        allowed.add(path)
        required.add(path)
    if not required <= allowed:
        raise ValueError("required file is not allowlisted")
    for path in sorted(required - reader.entries.keys()):
        problem(path, "missing_required_file")
    checked = []
    total = 0
    for path, (kind, size) in sorted(reader.entries.items()):
        if denied_path(path):
            problem(path, "prohibited_path_not_read")
            continue
        if path not in allowed:
            problem(path, "not_allowlisted_not_read")
            continue
        if kind != "regular":
            problem(path, "nonregular_path_not_read")
            continue
        if size > limit:
            problem(path, "oversized_file_not_read", bytes=size)
            continue
        data = reader.read(path, limit)
        total += len(data)
        digest = hashlib.sha256(data).hexdigest()
        if path in expected_hashes and digest != expected_hashes[path]:
            problem(path, "pinned_hash_mismatch")
        if b"\x00" in data or data.startswith((b"\x7fELF", b"MZ", b"PK\x03\x04", b"\x1f\x8b")):
            problem(path, "binary_payload")
            continue
        content = data.decode("utf-8", errors="replace")
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(content):
                # Never include a matching token or line of text in a report.
                problem(path, label, line=content.count("\n", 0, match.start()) + 1)
        checked.append({"path": path, "bytes": len(data), "sha256": digest})
    if total > policy.get("maximum_total_bytes", 32 * 1024 * 1024):
        problem(".", "package_exceeds_total_size")
    return {"format": "cequal-publication-preflight-v1",
            "status": "PASS_CONTENT_CHECKS" if not problems else "FAIL_CONTENT_CHECKS",
            "publication_authorized": False,
            "history_scanned": False,
            "limitations": "Bounded content checks only; not exhaustive secret detection, rights clearance, target validation, or approval to publish.",
            "checked_files": len(checked), "checked_bytes": total,
            "problems": problems, "file_manifest": checked}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--git-index", action="store_true", help="inspect actual staged package blobs")
    parser.add_argument("--repo-root", type=Path, help="explicit Git root when the package is a nested subtree; never scans other repository content")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if args.repo_root and not args.git_index:
            raise ValueError("--repo-root requires --git-index")
        result = audit(Index(root, args.repo_root) if args.git_index else Worktree(root))
        result["scope"] = "git_index_package_subtree" if args.git_index else "worktree_package_subtree"
        result["scope_limit"] = "Only this package is scanned, not other repository paths or historical commits."
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not result["problems"] else 1
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        # Exceptions may contain private paths or subprocess diagnostics.
        print(json.dumps({"status": "PREFLIGHT_ERROR", "error_type": type(exc).__name__,
                          "message": "Unable to inspect the selected package safely; check the allowlist, required files, and Git-index prerequisites."}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
