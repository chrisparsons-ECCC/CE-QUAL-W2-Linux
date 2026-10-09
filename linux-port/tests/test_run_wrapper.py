"""Launcher/receipt tests: synthetic files only; never executes the solver."""
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import run as launcher

def receipt(end=True):
    def line(label,cw,mx):
        raw=bytearray(32);raw[:2]=cw.to_bytes(2,'little');raw[24:28]=mx.to_bytes(4,'little');raw[28:32]=(0x2ffff).to_bytes(4,'little')
        return f'{label} fcw={cw:04x} fsw=0000 ftw=00 mxcsr={mx:08x} mxcsr_mask=0002ffff raw32={raw.hex()}'
    rows=['W2_INVALID_MASK_DIAGNOSTIC 1 candidate=1']
    rows += [line(k,0x372,0x9940) for k in ('BEGIN_ENTRY','BEGIN_BEFORE')]
    rows += [line(k,0x373,0x99c0) for k in ('BEGIN_AFTER','BEGIN_LOG_AFTER')]
    rows += ['BEGIN_GUARD_PASS']
    if end:rows += [line(k,0x373,0x99c0) for k in ('END_BEFORE','END_LOG_AFTER')]+['END_PRE_CLOSE_GUARD_PASS']
    return '\n'.join(rows)+'\n'

class CompletionTests(unittest.TestCase):
    def test_optimized_python_refused_before_launch(self):
        q=subprocess.run([sys.executable,'-O',str(ROOT/'tools/run.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(q.returncode,2);self.assertIn('optimization',q.stderr)
    def check(self,rc,text,expected,valid,changed=()):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'capture.json').write_text(json.dumps({'exit_code':rc}))
            (p/'invocation.json').write_text(json.dumps({'only_authorized_mask_action':True}))
            if text is not None:(p/'invalid-mask-receipt.txt').write_text(text)
            fp,errors,out=launcher.verify_completion(p,rc,True,list(changed))
            self.assertEqual(out,expected)
            self.assertEqual(fp is not None,valid)
            if fp:self.assertEqual(fp['normal_return_and_post_close_guard_confirmed_by_zero_exit'],rc==0)
            return errors
    def test_normal_zero(self):self.assertFalse(self.check(0,receipt(),0,True))
    def test_nonzero_ordinary_return(self):self.assertFalse(self.check(1,receipt(),1,True))
    def test_signal_abort(self):self.assertFalse(self.check(-6,receipt(False),134,True))
    def test_missing_receipt_preserves_failure(self):self.assertTrue(self.check(86,None,86,False))
    def test_partial_receipt_preserves_failure(self):self.assertTrue(self.check(86,'FAIL BAD\n',86,False))
    def test_missing_receipt_never_promotes_success(self):self.assertTrue(self.check(0,None,86,False))
    def test_begin_only_never_promotes_success(self):self.assertTrue(self.check(0,receipt(False),86,False))
    def test_input_change_blocks_success(self):self.assertTrue(self.check(0,receipt(),86,True,['w2_con.npt']))
    def test_input_change_preserves_native_failure(self):self.assertTrue(self.check(1,receipt(),1,True,['w2_con.npt']))
    def test_unrelated_fp_bit_rejected(self):self.assertTrue(self.check(0,receipt().replace('fcw=0373','fcw=0773'),86,False))
    def test_strict_does_not_require_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(launcher.verify_completion(Path(tmp),0,False,[]),(None,[],0))
            self.assertEqual(launcher.verify_completion(Path(tmp),-6,False,[]),(None,[],134))

class InputTests(unittest.TestCase):
    def test_original_and_staged_names_preserve_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'original.npt').write_bytes(b'unchanged\r\n');(p/'w2_con.npt').write_bytes(b'unchanged\r\n')
            row={'source':'original.npt','staged':'w2_con.npt',**launcher.digest(p/'original.npt')}
            for layout,name in [('original','original.npt'),('staged','w2_con.npt')]:
                source,plan=launcher.safe_inputs({'inputs':[row]},p,layout)
                self.assertEqual(plan,[(p/name,'original.npt')])
            (p/'w2_con.npt').write_bytes(b'changed')
            with self.assertRaises(ValueError):launcher.safe_inputs({'inputs':[row]},p,'staged')
    def test_symlinked_input_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'real').write_bytes(b'x');(p/'alias').symlink_to('real')
            with self.assertRaises(ValueError):launcher.safe_inputs({'inputs':[]},p,'original')

if __name__=='__main__':unittest.main()
