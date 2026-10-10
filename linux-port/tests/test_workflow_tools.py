"""Synthetic orchestration tests. No IFX installation or scientific model execution."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import run_case as case
import ensemble


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        (self.inputs / "w2_con.csv").write_text("title,synthetic test\n")
        self.exe = self.root / "fake_solver"
        self.solver("from pathlib import Path\nPath('result.csv').write_text('day,value\\n0,1\\n10,2\\n')\n")
        self.build = self.root / "build"
        self.build.mkdir()
        self.spec = {"schema": 1, "input_dir": "inputs", "input_files": ["w2_con.csv"],
                     "required_outputs": ["result.csv"], "completion": {
                         "file": "result.csv", "column": 0, "skip_rows": 1,
                         "delimiter": ",", "end_time": 10, "tolerance": 0}}
        self.manifest = self.root / "case.json"
        self.save()
        gate = patch.object(case, "reviewed_build", side_effect=self.fake_build)
        gate.start()
        self.addCleanup(gate.stop)

    def fake_build(self, directory, profile):
        return {"exe": self.exe, "env": dict(os.environ),
                "provenance": {"build": str(directory), "profile": profile,
                               "executable": case.digest(self.exe), "synthetic_test_only": True}}

    def solver(self, text):
        self.exe.write_text(f"#!{sys.executable}\n" + text)
        self.exe.chmod(0o700)

    def save(self):
        self.manifest.write_text(json.dumps(self.spec))

    def plan(self, profile="strict"):
        return case.prepare(self.manifest, self.build, profile)

    def launch(self, timeout=3, profile="strict", name="run", cancel=None):
        return case.run_prepared(self.plan(profile), self.root / name, timeout, cancel)

    def ensemble_manifest(self, count=2):
        path = self.root / "ensemble.json"
        path.write_text(json.dumps({"schema": 1, "cases": [
            {"id": f"case-{i}", "manifest": "case.json"} for i in range(count)]}))
        return path

    def batch(self, count=2, **kwargs):
        manifest = self.root / "ensemble.json"
        if not manifest.exists():
            manifest = self.ensemble_manifest(count)
        return ensemble.execute(manifest, self.build, "strict", self.root / "batch", **kwargs)

    def test_success_and_verified_resume(self):
        result = self.launch()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["scientific_acceptance"], "NOT ASSESSED")
        self.assertTrue(case.verified_success(self.root / "run", self.plan()))

    def test_nonzero_exit_is_preserved(self):
        self.solver("raise SystemExit(17)\n")
        result = self.launch()
        self.assertEqual((result["status"], result["native_exit"]), ("failed", 17))

    def test_signal_exit_is_preserved(self):
        self.solver("import os,signal\nos.kill(os.getpid(), signal.SIGABRT)\n")
        result = self.launch()
        self.assertEqual((result["status"], result["native_exit"]), ("failed", -signal.SIGABRT))
        self.assertFalse(list((self.root / "run").rglob("core*")))

    def test_timeout(self):
        self.solver("import time\ntime.sleep(30)\n")
        result = self.launch(timeout=0.15)
        self.assertEqual(result["status"], "timed_out")
        self.assertLess(result["elapsed_seconds"], 3)

    def test_timeout_kills_term_ignoring_descendant(self):
        self.solver("import subprocess,sys,time\nfrom pathlib import Path\n"
                    "p=subprocess.Popen([sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(30)'])\n"
                    "Path('child.pid').write_text(str(p.pid))\ntime.sleep(30)\n")
        self.assertEqual(self.launch(timeout=3)["status"], "timed_out")
        pid = int((self.root / "run/model/child.pid").read_text())
        state = Path(f"/proc/{pid}/stat")
        deadline = time.monotonic() + 1
        while state.exists() and state.read_text().split()[2] != "Z" and time.monotonic() < deadline:
            time.sleep(0.02)
        if state.exists():
            self.assertEqual(state.read_text().split()[2], "Z")

    def test_cancel_active_run(self):
        self.solver("import time\ntime.sleep(30)\n")
        event = threading.Event()
        timer = threading.Timer(0.2, event.set)
        timer.start()
        try:
            self.assertEqual(self.launch(cancel=event)["status"], "cancelled")
        finally:
            timer.cancel()

    def test_native_zero_without_outputs_fails(self):
        self.solver("pass\n")
        self.assertEqual(self.launch()["status"], "failed")

    def test_early_final_time_fails(self):
        self.spec["completion"]["end_time"] = 20
        self.save()
        self.assertEqual(self.launch()["status"], "failed")

    def test_late_final_time_fails(self):
        self.spec["completion"]["end_time"] = 9
        self.save()
        self.assertEqual(self.launch()["status"], "failed")

    def test_nonfinite_and_malformed_final_time_fail(self):
        for index, token in enumerate(("nan", "inf", "broken", "")):
            with self.subTest(token=token):
                self.solver(f"from pathlib import Path\nPath('result.csv').write_text('day,value\\n{token},2\\n')\n")
                self.assertEqual(self.launch(name=f"run-{index}")["status"], "failed")

    def test_modified_input_fails(self):
        self.solver("from pathlib import Path\nPath('w2_con.csv').write_text('changed')\nPath('result.csv').write_text('day,value\\n10,2\\n')\n")
        self.assertEqual(self.launch()["status"], "failed")
        self.assertEqual((self.inputs / "w2_con.csv").read_text(), "title,synthetic test\n")

    def test_staging_change_detected(self):
        plan = self.plan()
        (self.inputs / "w2_con.csv").write_text("new bytes")
        self.assertEqual(case.run_prepared(plan, self.root / "run", 3)["status"], "failed")
        self.assertFalse((self.root / "run/invocation.json").exists())

    def test_required_outputs_nonempty(self):
        self.solver("from pathlib import Path\nPath('result.csv').touch()\n")
        self.assertEqual(self.launch()["status"], "failed")

    def test_diagnostic_rejection(self):
        self.spec["reject_text"] = [{"file": "warning.txt", "contains": ["FATAL"]}]
        self.save()
        self.solver("from pathlib import Path\nPath('result.csv').write_text('day,value\\n10,2\\n')\nPath('warning.txt').write_text('fatal error')\n")
        self.assertEqual(self.launch()["status"], "failed")

    def test_symlink_input_rejected(self):
        target = self.inputs / "w2_con.csv"
        target.unlink()
        target.symlink_to(self.manifest)
        with self.assertRaises(ValueError):
            self.plan()

    def test_traversal_rejected(self):
        for name in ("../outside", "/tmp/out", "a/../../b", "C:\\test", "a\\b", "a//b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                case.relative_name(name)

    def test_unsafe_control_paths_rejected(self):
        for text in ('file,/tmp/out.csv', 'file,"../out.csv"', 'file,C:\\out.csv'):
            (self.inputs / "w2_con.csv").write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.plan()

    def test_unknown_key_rejected(self):
        self.spec["compltion"] = {}
        self.save()
        with self.assertRaises(ValueError):
            self.plan()

    def test_duplicate_json_key_rejected(self):
        self.manifest.write_text('{"schema":1,"schema":1}')
        with self.assertRaises(ValueError):
            case.read_json(self.manifest)

    def test_nonfinite_json_rejected(self):
        self.manifest.write_text('{"x":NaN}')
        with self.assertRaises(ValueError):
            case.read_json(self.manifest)

    def test_fortran_numbers(self):
        self.assertEqual(case.parse_number("1.00000+001"), 10)
        self.assertEqual(case.parse_number("1d1"), 10)

    def test_missing_fp_receipt_fails_closed(self):
        with patch.object(case, "verify_fp", side_effect=ValueError("missing FP receipt")):
            self.assertEqual(self.launch(profile="windows-compatible-invalid-only")["status"], "failed")

    def test_compatible_native_failure_not_hidden_by_fp(self):
        self.solver("raise SystemExit(9)\n")
        with patch.object(case, "verify_fp") as verify:
            result = self.launch(profile="windows-compatible-invalid-only")
            self.assertEqual(result["native_exit"], 9)
            verify.assert_not_called()

    def test_existing_run_directory_refused(self):
        self.launch()
        with self.assertRaises(FileExistsError):
            self.launch()

    def test_run_inside_inputs_refused(self):
        with self.assertRaises(ValueError):
            case.run_prepared(self.plan(), self.inputs / "run", 3)

    def test_tampered_output_is_not_verified(self):
        self.launch()
        (self.root / "run/model/result.csv").write_text("day,value\n10,999\n")
        self.assertFalse(case.verified_success(self.root / "run", self.plan()))

    def test_tampered_diagnostic_receipt_is_not_verified(self):
        self.launch()
        (self.root / "run/capture.json").write_text('{"exit_code": 17}')
        self.assertFalse(case.verified_success(self.root / "run", self.plan()))

    def test_deleted_receipt_is_not_verified(self):
        self.launch()
        (self.root / "run/invocation.json").unlink()
        self.assertFalse(case.verified_success(self.root / "run", self.plan()))

    def test_extra_output_is_not_verified(self):
        self.launch()
        (self.root / "run/model/extra.txt").write_text("extra")
        self.assertFalse(case.verified_success(self.root / "run", self.plan()))

    def test_symlink_output_fails(self):
        self.solver(f"from pathlib import Path\nPath('result.csv').symlink_to({str(self.manifest)!r})\n")
        self.assertEqual(self.launch()["status"], "failed")

    def test_independent_parallel_outputs(self):
        summary = self.batch(jobs=2)
        self.assertTrue(summary["all_execution_checks_passed"])
        paths = [Path(v["attempt"]) / "model/result.csv" for v in summary["cases"].values()]
        self.assertNotEqual(paths[0].stat().st_ino, paths[1].stat().st_ino)

    def test_resume_skips_verified(self):
        self.batch()
        summary = self.batch(resume=True)
        self.assertTrue(all(v["status"] == "skipped_verified" for v in summary["cases"].values()))

    def test_resume_reruns_corrupted_result_without_overwrite(self):
        self.batch(count=1)
        old = self.root / "batch/case-0/attempt-000001/model/result.csv"
        old.write_text("corrupted")
        summary = self.batch(resume=True)
        self.assertEqual(summary["cases"]["case-0"]["status"], "success")
        self.assertEqual(old.read_text(), "corrupted")
        self.assertTrue((self.root / "batch/case-0/attempt-000002").exists())

    def test_resume_rejects_changed_inputs(self):
        self.batch(count=1)
        (self.inputs / "w2_con.csv").write_text("new input bytes")
        with self.assertRaises(ValueError):
            self.batch(resume=True)

    def test_bounded_retries(self):
        self.solver("raise SystemExit(8)\n")
        result = self.batch(count=1, retries=2)
        self.assertEqual(result["cases"]["case-0"]["new_attempts"], 3)
        self.assertEqual(len(list((self.root / "batch/case-0").iterdir())), 3)

    def test_retry_stops_after_success_and_preserves_failure(self):
        self.solver("from pathlib import Path\n"
                    "if Path.cwd().parent.name == 'attempt-000001': raise SystemExit(7)\n"
                    "Path('result.csv').write_text('day,value\\n10,2\\n')\n")
        result = self.batch(count=1, retries=3)
        self.assertEqual(result["cases"]["case-0"]["new_attempts"], 2)
        self.assertTrue(result["all_execution_checks_passed"])
        old = case.read_json(self.root / "batch/case-0/attempt-000001/run-result.json")
        self.assertEqual(old["native_exit"], 7)

    def test_native_zero_with_live_descendant_fails_and_cleans_up(self):
        self.solver("import subprocess,sys\nfrom pathlib import Path\n"
                    "subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])\n"
                    "Path('result.csv').write_text('day,value\\n10,2\\n')\n")
        result = self.launch()
        self.assertEqual(result["status"], "failed")
        self.assertIn("descendant", " ".join(result["errors"]))

    def test_abandoned_attempt_is_not_automatically_retried(self):
        self.batch(count=1)
        receipt = self.root / "batch/case-0/attempt-000001/run-result.json"
        receipt.unlink()
        with self.assertRaises(ValueError):
            self.batch(resume=True)
        self.assertFalse((self.root / "batch/case-0/attempt-000002").exists())

    def test_workspace_lock_refuses_second_launcher(self):
        folder = self.root / "lock"
        folder.mkdir()
        with ensemble.workspace_lock(folder):
            with self.assertRaises(ValueError):
                with ensemble.workspace_lock(folder):
                    self.fail("Acquired duplicate lock")
        with ensemble.workspace_lock(folder):
            pass

    def test_duplicate_case_ids_rejected(self):
        manifest = self.ensemble_manifest()
        spec = case.read_json(manifest)
        spec["cases"][1]["id"] = spec["cases"][0]["id"]
        manifest.write_text(json.dumps(spec))
        with self.assertRaises(ValueError):
            ensemble.load_ensemble(manifest)

    def test_concurrency_bound(self):
        active = 0
        maximum = 0
        lock = threading.Lock()
        original = case.run_prepared
        def counted(*args, **kwargs):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            try:
                time.sleep(0.1)
                return original(*args, **kwargs)
            finally:
                with lock:
                    active -= 1
        with patch.object(case, "run_prepared", side_effect=counted):
            summary = self.batch(count=5, jobs=2)
        self.assertTrue(summary["all_execution_checks_passed"])
        self.assertEqual(maximum, 2)

    def test_cancelled_ensemble_does_not_launch_pending_cases(self):
        event = threading.Event()
        event.set()
        result = self.batch(count=3, cancel=event)
        self.assertTrue(result["cancelled"])
        self.assertFalse(list((self.root / "batch").rglob("invocation.json")))

    def test_excluded_vendor_input_is_rejected_before_digest(self):
        self.spec['input_files'].append('nested/DeBuG.LoG')
        self.save()
        with patch.object(case, 'digest', side_effect=AssertionError('must not hash')):
            with self.assertRaisesRegex(ValueError, 'vendor-log'):
                self.plan()

    def test_excluded_vendor_output_stops_before_any_output_digest(self):
        folder = self.root / 'inventory'
        folder.mkdir()
        (folder / 'aaa.csv').write_text('ordinary')
        (folder / 'DEBUG.LOG').touch()
        with patch.object(case, 'digest', side_effect=AssertionError('must not hash')):
            with self.assertRaisesRegex(ValueError, 'vendor-log'):
                case.inventory(folder)

    def test_bare_parent_tokens_rejected_but_embedded_dots_allowed(self):
        control = self.inputs / 'w2_con.csv'
        for text in ('dir,".."', 'dir,..,next', "dir,'..'"):
            control.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                case.lint_paths(control)
        control.write_text('file,series..csv\n')
        case.lint_paths(control)

    def test_vendor_log_manifest_rejected_before_read(self):
        path = self.root / 'DeBuG.LoG'
        path.touch()
        with patch.object(Path, 'read_text', side_effect=AssertionError('must not read vendor log')):
            with self.assertRaisesRegex(ValueError, 'vendor-log'):
                case.read_json(path)

    def test_fifo_json_rejected_before_read(self):
        fifo = self.root / 'case.fifo'
        os.mkfifo(fifo)
        with patch.object(Path, 'read_text', side_effect=AssertionError('must not read FIFO')):
            with self.assertRaisesRegex(ValueError, 'regular'):
                case.read_json(fifo)

    def test_symlinked_input_ancestor_rejected(self):
        (self.root / 'linked-inputs').symlink_to(self.inputs, target_is_directory=True)
        self.spec['input_dir'] = 'linked-inputs'
        self.save()
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            self.plan()

    def test_hard_linked_result_rejected(self):
        folder = self.root / 'hardlinks'
        folder.mkdir()
        (folder / 'first.csv').write_text('value')
        os.link(folder / 'first.csv', folder / 'second.csv')
        with self.assertRaisesRegex(ValueError, 'hard-linked'):
            case.inventory(folder)

    def test_changed_executable_after_prepare_cannot_launch(self):
        plan = self.plan()
        self.solver("raise SystemExit(0)\n")
        result = case.run_prepared(plan, self.root / 'run', 3)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('changed during staging', ' '.join(result['errors']))
        self.assertFalse((self.root / 'run/invocation.json').exists())

    def test_executable_changed_during_run_cannot_succeed(self):
        self.solver("from pathlib import Path\nPath(__file__).write_text('changed')\nPath('result.csv').write_text('day,value\\n10,2\\n')\n")
        result = self.launch()
        self.assertEqual(result['native_exit'], 0)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('changed during execution', ' '.join(result['errors']))

    def test_empty_or_malformed_receipt_index_is_not_verified(self):
        self.launch()
        path = self.root / 'run/run-result.json'
        result = case.read_json(path)
        for index in ({}, []):
            result['receipt_inventory'] = index
            path.write_text(json.dumps(result))
            with self.subTest(index=index):
                self.assertFalse(case.verified_success(self.root / 'run', self.plan()))

    def test_capture_exit_reconciled_even_if_index_is_rewritten(self):
        self.launch()
        attempt = self.root / 'run'
        (attempt / 'capture.json').write_text('{"exit_code":17}')
        path = attempt / 'run-result.json'
        result = case.read_json(path)
        result['receipt_inventory']['capture.json'] = case.digest(attempt / 'capture.json')
        path.write_text(json.dumps(result))
        self.assertFalse(case.verified_success(attempt, self.plan()))

    def test_invocation_profile_reconciled_even_if_index_is_rewritten(self):
        self.launch()
        attempt = self.root / 'run'
        path = attempt / 'invocation.json'
        invocation = case.read_json(path)
        invocation['profile'] = 'windows-compatible-invalid-only'
        path.write_text(json.dumps(invocation))
        result_path = attempt / 'run-result.json'
        result = case.read_json(result_path)
        result['receipt_inventory']['invocation.json'] = case.digest(path)
        result_path.write_text(json.dumps(result))
        self.assertFalse(case.verified_success(attempt, self.plan()))

    def test_cancel_during_completion_takes_precedence(self):
        event = threading.Event()
        original = case.check_completion
        def completion(*args):
            result = original(*args)
            event.set()
            return result
        with patch.object(case, 'check_completion', side_effect=completion):
            self.assertEqual(self.launch(cancel=event)['status'], 'cancelled')

    def test_reserved_ensemble_ids_rejected_before_workspace_creation(self):
        for name in ('ensemble.json', 'ensemble-result.json'):
            path = self.root / 'ensemble.json'
            path.write_text(json.dumps({'schema': 1, 'cases': [{'id': name, 'manifest': 'case.json'}]}))
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'collides'):
                self.batch()
            self.assertFalse((self.root / 'batch').exists())

    def test_missing_runtime_observation_is_explicit_and_required(self):
        with patch.object(case, 'observe_runtime', return_value=None):
            result = self.launch()
        self.assertEqual(result['status'], 'success')
        self.assertFalse(result['runtime_pins_observed'])
        receipt = self.root / 'run/observed-runtime.json'
        self.assertEqual(case.read_json(receipt)['status'], 'unavailable')
        receipt.unlink()
        self.assertFalse(case.verified_success(self.root / 'run', self.plan()))

    def test_observed_runtime_mismatch_fails_and_stops_solver(self):
        self.solver('import time\ntime.sleep(30)\n')
        observation = {'status': 'observed', 'pinned_runtime_verified': False,
                       'pinned_runtime_errors': ['Observed pinned runtime mismatch: libimf.so']}
        with patch.object(case, 'observe_runtime', return_value=observation):
            result = self.launch()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('runtime mismatch', ' '.join(result['errors']))
        self.assertLess(result['elapsed_seconds'], 3)

    def test_runtime_observer_waits_for_exec_shim(self):
        import run as pinned
        original = Path.resolve
        def resolved(path, *args, **kwargs):
            return Path('/fake/python-shim') if str(path) == '/proc/123/exe' else original(path, *args, **kwargs)
        with patch.object(Path, 'resolve', autospec=True, side_effect=resolved), patch.object(pinned.capture, 'observe_linux_runtime') as observe:
            self.assertIsNone(case.observe_runtime(123, self.fake_build(self.build, 'strict')))
            observe.assert_not_called()

    def test_runtime_observer_matches_pins_and_records_gaps(self):
        import run as pinned
        original = Path.resolve
        def resolved(path, *args, **kwargs):
            return self.exe if str(path) == '/proc/123/exe' else original(path, *args, **kwargs)
        runtime = self.fake_build(self.build, 'strict')
        expected = {'bytes': 12, 'sha256': 'abc'}
        runtime['provenance']['runtime'] = {'/fake/libimf.so': expected, '/fake/libintlc.so.5': expected}
        for paths, verified in ((['/fake/libimf.so'], False), (['/fake/libimf.so', '/fake/libintlc.so.5'], True)):
            record = {'libraries': [dict(path=x, **expected) for x in paths], 'observation_errors': []}
            with patch.object(Path, 'resolve', autospec=True, side_effect=resolved), patch.object(pinned.capture, 'observe_linux_runtime', return_value=record):
                result = case.observe_runtime(123, runtime)
            self.assertEqual(result['pinned_runtime_verified'], verified)
            self.assertEqual(result['pinned_runtime_errors'], [])

    def test_runtime_observer_detects_wrong_library_hash(self):
        import run as pinned
        original = Path.resolve
        def resolved(path, *args, **kwargs):
            return self.exe if str(path) == '/proc/123/exe' else original(path, *args, **kwargs)
        runtime = self.fake_build(self.build, 'strict')
        runtime['provenance']['runtime'] = {'/fake/libimf.so': {'bytes': 12, 'sha256': 'abc'}}
        record = {'libraries': [{'path': '/fake/libimf.so', 'bytes': 12, 'sha256': 'different'}], 'observation_errors': []}
        with patch.object(Path, 'resolve', autospec=True, side_effect=resolved), patch.object(pinned.capture, 'observe_linux_runtime', return_value=record):
            result = case.observe_runtime(123, runtime)
        self.assertFalse(result['pinned_runtime_verified'])
        self.assertIn('mismatch', result['pinned_runtime_errors'][0])

    def test_cli_help(self):
        for script in ("run_case.py", "ensemble.py"):
            result = subprocess.run([sys.executable, str(TOOLS / script), "--help"], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_optimized_python_rejected(self):
        result = subprocess.run([sys.executable, "-O", str(TOOLS / "run_case.py"),
                                 "--manifest", str(self.manifest), "--build", str(self.build),
                                 "--profile", "strict", "--check-only"], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"forbidden", result.stderr)


if __name__ == "__main__":
    unittest.main()
