"""Preflight unit tests use synthetic data; no model run, Git init or network."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "publication_preflight.py"
spec = importlib.util.spec_from_file_location("publication_preflight", MODULE_PATH)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class FakeReader:
    def __init__(self, extra=None, allowed=None, required=None, manifests=None, pins=None):
        self.data = dict(extra or {})
        policy = {"format": "cequal-publication-allowlist-v1",
                  "files": list(allowed or []), "required_files": list(required or []),
                  "source_manifests": list(manifests or []),
                  "additional_pinned_files": pins or {}}
        self.data[preflight.POLICY] = json.dumps(policy).encode()
        self.entries = {p: ("regular", len(b)) for p, b in self.data.items()}
        self.reads = []

    def read(self, path, limit):
        self.reads.append(path)
        if self.entries[path][0] != "regular" or len(self.data[path]) > limit:
            raise ValueError("test refused unsafe read")
        return self.data[path]


def kinds(result):
    return {x["kind"] for x in result["problems"]}


class PublicationPreflightTests(unittest.TestCase):
    def test_clean_small_text(self):
        reader = FakeReader({"README.md": b"A source-only candidate.\n"}, ["README.md"], ["README.md"])
        result = preflight.audit(reader)
        self.assertEqual(result["status"], "PASS_CONTENT_CHECKS")
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["history_scanned"])

    def test_debug_log_and_unknown_are_never_opened(self):
        reader = FakeReader({"debug.log": b"do not open", "unknown.txt": b"do not open"})
        result = preflight.audit(reader)
        self.assertNotIn("debug.log", reader.reads)
        self.assertNotIn("unknown.txt", reader.reads)
        self.assertIn("prohibited_path_not_read", kinds(result))
        self.assertIn("not_allowlisted_not_read", kinds(result))

    def test_even_allowlisted_raw_logs_are_never_opened(self):
        reader = FakeReader({"debug.log": b"do not open"}, ["debug.log"])
        self.assertIn("prohibited_path_not_read", kinds(preflight.audit(reader)))
        self.assertNotIn("debug.log", reader.reads)

    def test_prohibited_manifest_is_not_opened(self):
        reader = FakeReader({"debug.log": b"do not open"}, ["debug.log"], manifests=["debug.log"])
        with self.assertRaises(ValueError):
            preflight.audit(reader)
        self.assertNotIn("debug.log", reader.reads)

    def test_pinned_source_bytes_and_mismatch(self):
        raw = b"PROGRAM A\r\nEND\r\n"
        digest = hashlib.sha256(raw).hexdigest()
        manifest = {"directory": "source/strict", "files": {"a.f90": digest}}
        reader = FakeReader({"config/sources.json": json.dumps(manifest).encode(), "source/strict/a.f90": raw},
                            ["config/sources.json"], manifests=["config/sources.json"])
        self.assertEqual(preflight.audit(reader)["status"], "PASS_CONTENT_CHECKS")
        reader.data["source/strict/a.f90"] = raw.replace(b"\r\n", b"\n")
        self.assertIn("pinned_hash_mismatch", kinds(preflight.audit(reader)))

    def test_missing_required(self):
        result = preflight.audit(FakeReader(allowed=["README.md"], required=["README.md"]))
        self.assertIn("missing_required_file", kinds(result))

    def test_symlink_not_opened(self):
        reader = FakeReader({"README.md": b"unread"}, ["README.md"])
        reader.entries["README.md"] = ("symlink", 6)
        self.assertIn("nonregular_path_not_read", kinds(preflight.audit(reader)))
        self.assertNotIn("README.md", reader.reads)

    def test_binary_rejected(self):
        result = preflight.audit(FakeReader({"README.md": b"\x7fELF\x00payload"}, ["README.md"]))
        self.assertIn("binary_payload", kinds(result))

    def test_secret_redaction(self):
        synthetic = "gh" + "p_" + "A" * 36
        result = preflight.audit(FakeReader({"README.md": synthetic.encode()}, ["README.md"]))
        self.assertIn("github_credential", kinds(result))
        self.assertNotIn(synthetic, json.dumps(result))

    def test_private_workspace_path(self):
        synthetic = "/" + "workspace" + "/private/data"
        result = preflight.audit(FakeReader({"README.md": synthetic.encode()}, ["README.md"]))
        self.assertIn("private_workspace_path", kinds(result))
        self.assertNotIn(synthetic, json.dumps(result))

    def test_private_storage_url(self):
        synthetic = "https://unit." + "blob.core.windows.net" + "/secret?sig=value"
        result = preflight.audit(FakeReader({"README.md": synthetic.encode()}, ["README.md"]))
        self.assertIn("private_storage_url", kinds(result))
        self.assertNotIn(synthetic, json.dumps(result))

    def test_oversized_file_not_read(self):
        reader = FakeReader({"README.md": b"x"}, ["README.md"])
        reader.entries["README.md"] = ("regular", 3 * 1024 * 1024)
        self.assertIn("oversized_file_not_read", kinds(preflight.audit(reader)))
        self.assertNotIn("README.md", reader.reads)

    def test_manifest_cannot_escape_root(self):
        manifest = {"directory": "source/strict", "files": {"../../outside": "0" * 64}}
        reader = FakeReader({"config/sources.json": json.dumps(manifest).encode()},
                            ["config/sources.json"], manifests=["config/sources.json"])
        with self.assertRaises(ValueError):
            preflight.audit(reader)

    def test_no_index_fallback_to_enclosing_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                preflight.Index(Path(tmp))

    def test_index_reads_staged_blob_instead_of_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()  # Empty test sentinel; never a Git init.
            (root / "README.md").write_bytes(b"worktree bytes")
            oid = "a" * 40
            def fake_git(_root, *args):
                if args == ("rev-parse", "--show-toplevel"):
                    return str(root).encode() + b"\n"
                if args == ("ls-files", "--stage", "-z"):
                    return f"100644 {oid} 0\tREADME.md\0".encode()
                if args == ("cat-file", "-s", oid):
                    return b"12\n"
                if args == ("cat-file", "blob", oid):
                    return b"staged bytes"
                raise AssertionError(args)
            with mock.patch.object(preflight, "git", side_effect=fake_git):
                reader = preflight.Index(root)
                self.assertEqual(reader.read("README.md", 100), b"staged bytes")

    def test_nested_index_scope_does_not_read_existing_repo_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = Path(tmp)
            (repository / ".git").mkdir()
            package = repository / "linux-port"
            package.mkdir()
            oid = "b" * 40
            calls = []
            def fake_git(_root, *args):
                calls.append(args)
                self.assertEqual(_root, repository)
                if args == ("rev-parse", "--show-toplevel"):
                    return str(repository).encode() + b"\n"
                if args == ("ls-files", "--stage", "-z", "--", "linux-port/"):
                    return f"100644 {oid} 0\tlinux-port/README.md\0".encode()
                if args == ("cat-file", "-s", oid):
                    return b"12\n"
                if args == ("cat-file", "blob", oid):
                    return b"staged bytes"
                raise AssertionError(args)
            with mock.patch.object(preflight, "git", side_effect=fake_git):
                reader = preflight.Index(package, repository)
                self.assertEqual(set(reader.entries), {"README.md"})
                self.assertEqual(reader.read("README.md", 100), b"staged bytes")
            self.assertTrue(all("debug.log" not in call for call in calls))

    def test_real_symlink_parent_is_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "package"
            root.mkdir()
            outside = Path(tmp) / "outside"
            outside.mkdir()
            (outside / "private.txt").write_bytes(b"not read")
            (root / "docs").symlink_to(outside, target_is_directory=True)
            reader = preflight.Worktree(root)
            self.assertIn("docs", reader.entries)
            self.assertNotIn("docs/private.txt", reader.entries)


if __name__ == "__main__":
    unittest.main()
