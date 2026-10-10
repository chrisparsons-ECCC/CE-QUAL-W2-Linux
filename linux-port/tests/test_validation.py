"""Negative controls for narrow output normalization, no solver execution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import validate

class NormalizeTests(unittest.TestCase):
    def pair(self,name,a,b):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'a').write_bytes(a);(p/'b').write_bytes(b)
            return [validate.canonical(p/x,name) for x in ('a','b')]
    def test_clock_change_is_narrow(self):
        a=b'Model run at 01:02:03 on 10/09/26\nTemperature=12.5\n'
        b=a.replace(b'01:02:03',b'04:05:06')
        x,y=self.pair('snp.opt',a,b)
        self.assertNotEqual(x['raw'],y['raw']);self.assertEqual(x['normalized'],y['normalized'])
        x,y=self.pair('snp.opt',a,b.replace(b'12.5',b'12.6'))
        self.assertNotEqual(x['normalized'],y['normalized'])
    def test_csv_and_line_endings_not_excluded(self):
        a=b'Model run at 01:02:03 on 10/09/26\n'
        for name,b in [('table.csv',a.replace(b'01:02:03',b'04:05:06')),('snp.opt',a.replace(b'\n',b'\r\n'))]:
            x,y=self.pair(name,a,b);self.assertNotEqual(x['normalized'],y['normalized'])
    def test_binary_clock_only(self):
        a=b'x'*724+b'Model run at 01:02:03 on 10/09/26'.ljust(72)+b'scientific tail'
        b=a.replace(b'01:02:03',b'04:05:06')
        x,y=self.pair('Detroit.w2l',a,b);self.assertEqual(x['normalized'],y['normalized'])
        x,y=self.pair('Detroit.w2l',a,b[:-1]+b'X');self.assertNotEqual(x['normalized'],y['normalized'])
        with self.assertRaises(ValueError):self.pair('Detroit.w2l',b'x'*800,a)
    def test_compile_timestamp_only(self):
        a=b'IFX 2026.1.1\nCE-QUAL-W2 Version compile date:Oct  9 2026 01:02:03\n'
        x,y=self.pair('W2CodeCompilerVersion.opt',a,a.replace(b'01:02:03',b'04:05:06'))
        self.assertEqual(x['normalized'],y['normalized'])
        x,y=self.pair('W2CodeCompilerVersion.opt',a,a.replace(b'2026.1.1',b'2026.2.0'))
        self.assertNotEqual(x['normalized'],y['normalized'])

class InventoryTests(unittest.TestCase):
    def fixture(self,root):
        package=root/'package';(package/'config').mkdir(parents=True)
        run=root/'run';case=run/'case';model=case/'model';model.mkdir(parents=True)
        (model/'input.npt').write_bytes(b'input');(model/'output.csv').write_bytes(b'1,2,3\n')
        inputs={'input.npt':validate.digest(model/'input.npt')}
        out=validate.canonical(model/'output.csv','output.csv')
        expected={'exit_code':0,'inputs':inputs,'outputs':{'output.csv':out},'evidence':'synthetic fixture'}
        (package/'config/accepted-output-controls.json').write_text(json.dumps({'profiles':{'strict':{'spokane':expected}}}))
        (case/'staging.json').write_text(json.dumps({'inputs':inputs}))
        (case/'run-start.json').write_text('{}\n')
        (case/'capture.json').write_text(json.dumps({'exit_code':0,'changed_or_missing_inputs':[],
            'run_start_record':validate.digest(case/'run-start.json'),'execution_records':{},'outputs':{'output.csv':out['raw']}}))
        (run/'run-result.json').write_text(json.dumps({'profile':'strict','case':'spokane','actual_model_exit':0,'wrapper_exit':0,'verification_errors':[]}))
        return package,run,model
    def test_changed_missing_extra_input_or_output_rejected(self):
        for mutation in ('none','science','missing','extra','input'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                package,run,model=self.fixture(Path(tmp));old=validate.ROOT;validate.ROOT=package
                try:
                    if mutation=='science':(model/'output.csv').write_bytes(b'1,2,4\n')
                    elif mutation=='missing':(model/'output.csv').unlink()
                    elif mutation=='extra':(model/'extra.csv').write_bytes(b'1\n')
                    elif mutation=='input':(model/'input.npt').write_bytes(b'changed')
                    self.assertEqual(validate.verify(run,'strict')['pass'],mutation=='none')
                finally:validate.ROOT=old

if __name__=='__main__':unittest.main()
