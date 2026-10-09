#!/usr/bin/env python3
"""Inspect an isolated copy, with an unchanged-original hash guard."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def inspect(source,destination,operation,section='.text'):
    source=Path(source).absolute();destination=Path(destination).absolute()
    if source.is_symlink() or not source.is_file() or source.name.lower()=='debug.log':
        raise ValueError('Expected an explicitly selected regular binary file')
    if destination.exists():raise ValueError('Inspection directory must be fresh')
    if not section.startswith('.') or any(c not in '._abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in section):
        raise ValueError('Unsupported ELF section name')
    before=sha(source);destination.mkdir(parents=True)
    copy=destination/'inspection-copy.bin';shutil.copyfile(source,copy)
    if sha(copy)!=before:raise ValueError('Inspection copy checksum mismatch')
    if operation=='sections':command=['readelf','-W','-S',str(copy)]
    elif operation=='disassembly':command=['objdump','-drw','-Mintel',str(copy)]
    elif operation=='dump-section':
        command=['objcopy','--dump-section',section+'='+str(destination/'section.bin'),str(copy),str(destination/'rewritten-copy.bin')]
    else:raise ValueError('Unsupported inspection operation')
    report={'operation':operation,'source':str(source),'source_sha256_before':before,
            'inspection_copy':str(copy),'argv':command,'tool_never_receives_original_path':str(source) not in command}
    try:
        completed=subprocess.run(command,capture_output=True)
        (destination/'stdout.txt').write_bytes(completed.stdout)
        (destination/'stderr.txt').write_bytes(completed.stderr)
        report['tool_returncode']=completed.returncode
    finally:
        report['source_sha256_after']=sha(source)
        report['source_preserved']=report['source_sha256_after']==before
        (destination/'inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['source_preserved']:raise ValueError('Original binary changed during inspection')
    if report['tool_returncode']:raise ValueError('Inspection tool failed; preserve its directory')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--operation',choices=('sections','disassembly','dump-section'),required=True)
    p.add_argument('--section',default='.text');a=p.parse_args()
    print(json.dumps(inspect(a.source,a.output,a.operation,a.section),indent=2))

if __name__=='__main__':
    try:main()
    except (OSError,ValueError) as error:print('INSPECTION STOPPED: '+str(error),file=sys.stderr);sys.exit(2)
