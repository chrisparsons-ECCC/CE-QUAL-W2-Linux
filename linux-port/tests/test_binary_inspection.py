"""Prevent section-dump inspection from rewriting evidence binaries."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import inspect_binary

class InspectionTests(unittest.TestCase):
    def test_dump_section_uses_copy_and_distinct_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);source=r/'original.o';source.write_bytes(b'preserved binary')
            def fake(command,**kwargs):
                self.assertNotIn(str(source),command)
                self.assertNotEqual(command[-1],command[-2])
                Path(command[-2]).write_bytes(b'tool rewrites input copy')
                Path(command[-1]).write_bytes(b'tool output')
                return subprocess.CompletedProcess(command,0,b'',b'')
            with patch.object(inspect_binary.subprocess,'run',fake):
                result=inspect_binary.inspect(source,r/'inspection','dump-section')
            self.assertTrue(result['source_preserved']);self.assertEqual(source.read_bytes(),b'preserved binary')
    def test_every_read_tool_uses_copy(self):
        for operation in ('sections','disassembly'):
            with self.subTest(operation=operation),tempfile.TemporaryDirectory() as tmp:
                r=Path(tmp);source=r/'original.o';source.write_bytes(b'original')
                def fake(command,**kwargs):
                    self.assertNotIn(str(source),command);self.assertEqual(Path(command[-1]).name,'inspection-copy.bin')
                    return subprocess.CompletedProcess(command,0,b'',b'')
                with patch.object(inspect_binary.subprocess,'run',fake):
                    self.assertTrue(inspect_binary.inspect(source,r/'inspection',operation)['source_preserved'])
    def test_original_hash_change_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);source=r/'original.o';source.write_bytes(b'original')
            def fake(command,**kwargs):
                source.write_bytes(b'unexpected concurrent change')
                return subprocess.CompletedProcess(command,0,b'',b'')
            with patch.object(inspect_binary.subprocess,'run',fake),self.assertRaises(ValueError):
                inspect_binary.inspect(source,r/'inspection','sections')
            self.assertIn('false',(r/'inspection/inspection.json').read_text())

if __name__=='__main__':unittest.main()
