#!/usr/bin/env python3
"""Run one pinned example in a fresh folder using an explicitly selected profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent/'support'))
import case_capture as capture
from verify_fp_receipt import verify as verify_fp

PROFILES=('strict','windows-compatible-invalid-only')
REMOVED_ENV=('LD_PRELOAD','LD_AUDIT','W2_FP_MODE','W2_FP_LOG',
             'W2_OBSERVER_TRACE','W2_TEMPERATURE_TRACE','W2_RADIUS_TRACE',
             'W2_INVALID_MASK_LOG')

def digest(p):
    p=Path(p)
    if p.is_symlink() or not p.is_file():
        raise ValueError('Expected a regular, non-symlink file: '+str(p))
    return capture.digest(p)

def safe_inputs(manifest,source,layout):
    source=source.resolve(strict=True)
    if not source.is_dir():raise ValueError('Input source must be a directory')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Symlinked input entries are not accepted')
    plan=[]
    for row in manifest['inputs']:
        name=capture.safe_relative_name(row['source'] if layout=='original' else row['staged'])
        p=source/name
        if p.name.lower()=='debug.log':raise ValueError('Vendor log is not a model input')
        if digest(p)!={k:row[k] for k in ('bytes','sha256')}:
            raise ValueError('Pinned input hash mismatch: '+name)
        plan.append((p,capture.safe_relative_name(row['source'])))
    return source,plan

def load_build(directory,profile):
    directory=directory.resolve(strict=True)
    meta_path=directory/'build.json'
    meta=json.loads(meta_path.read_text())
    if meta.get('status')!='complete' or meta.get('profile')!=profile:
        raise ValueError('Build is incomplete or profile differs from explicit run selection')
    config_path=ROOT/'config/build-profiles.json';config=json.loads(config_path.read_text())
    lock_path=ROOT/'config/toolchain-lock.json';lock=json.loads(lock_path.read_text())
    if meta['config']['sha256']!=digest(config_path)['sha256'] or meta['toolchain_lock']['sha256']!=digest(lock_path)['sha256']:
        raise ValueError('Build profile/toolchain configuration differs from current reviewed package')
    if meta['compiler']['sha256']!=lock['expected_sha256']['bin/ifx']:
        raise ValueError('Build compiler identity differs from accepted toolchain')
    if meta['common_flags']!=config['common_flags'] or meta['per_file_flags']!=config['per_file_flags'] or meta['compile_units']!=config['compile_units']:
        raise ValueError('Build options or unit order differ from reviewed profile')
    order=list(config['fortran_link_order'])
    if profile=='windows-compatible-invalid-only':
        helper=config['helper'];order.append(helper['object'])
        if meta.get('helper_sha256')!=helper['sha256'] or meta.get('helper_flags')!=helper['flags']:
            raise ValueError('Compatibility helper identity/options differ')
        for path in (ROOT/helper['source'],directory/'helper/w2_invalid_mask.c'):
            if digest(path)['sha256']!=helper['sha256']:raise ValueError('Compatibility helper source changed')
    elif 'helper_sha256' in meta:
        raise ValueError('Strict profile must not contain compatibility helper')
    if meta['link_object_order']!=order or set(meta['objects'])!=set(order):
        raise ValueError('Build object inventory or link order differs')
    for name in order:
        if digest(directory/'objects'/name)!={k:meta['objects'][name][k] for k in ('bytes','sha256')}:
            raise ValueError('Linked object changed: '+name)
    pinned=json.loads((ROOT/'config'/('sources-'+profile+'.json')).read_text())['files']
    if meta.get('source_sha256')!=pinned:
        raise ValueError('Build source identity differs from selected reviewed profile')
    observed={x.name:digest(x)['sha256'] for x in (directory/'source').iterdir() if x.is_file()}
    if observed!=pinned:raise ValueError('Copied build source changed or inventory differs')
    exe=directory/'w2'
    if digest(exe)['sha256']!=meta['executable']['sha256']:
        raise ValueError('Executable changed since build')
    runtime=meta['runtime'];library_dir=Path(runtime['library_dir']).resolve(strict=True)
    if {name:row['sha256'] for name,row in runtime['libraries'].items()}!=lock['runtime_libraries']:
        raise ValueError('Build runtime identities differ from accepted toolchain')
    libraries=[]
    for name,row in sorted(runtime['libraries'].items()):
        path=Path(row['path']).resolve(strict=True)
        if path.parent!=library_dir or path.name!=name:
            raise ValueError('Runtime path does not match the pinned library directory')
        if digest(path)!={k:row[k] for k in ('bytes','sha256')}:
            raise ValueError('Installed runtime changed since build: '+name)
        libraries.append(path)
    if set(runtime['libraries'])!={'libimf.so','libintlc.so.5'}:
        raise ValueError('Unexpected runtime library inventory')
    return meta_path,meta,exe,libraries,library_dir

def verify_completion(case_run,model_rc,compatibility,changed_inputs):
    fp=None;errors=[]
    if changed_inputs:errors.append('Input bytes changed during model run')
    if compatibility:
        try:
            fp=verify_fp(case_run)
            capture.write_new(case_run/'fp-verification.json',fp)
        except (OSError,ValueError,KeyError,AssertionError) as error:
            errors.append('FP receipt verification failed: '+str(error))
    # Preserve the actual model failure even if its receipt is missing/partial.
    # A native success with failed verification must never become wrapper success.
    wrapper_rc=(model_rc if model_rc>=0 else 128-model_rc) if model_rc else (86 if errors else 0)
    return fp,errors,wrapper_rc

def main(argv=None):
    if sys.flags.optimize:raise ValueError('Python optimization (-O/PYTHONOPTIMIZE) is not allowed for validated runs')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',choices=PROFILES,default='strict',
        help='Default strict preserves the original port; compatibility explicitly masks invalid exceptions only.')
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--case',choices=('spokane','detroit','degray'),required=True)
    p.add_argument('--inputs',type=Path,required=True,help='Directory containing the pinned original example or staged kit inputs.')
    p.add_argument('--input-layout',choices=('original','staged'),default='staged')
    p.add_argument('--run-dir',type=Path,required=True,help='Fresh directory outside the input directory; existing folders are refused.')
    a=p.parse_args(argv)
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','AMD64'):
        raise ValueError('This reviewed package requires Linux x86-64')
    run=a.run_dir.resolve()
    if run.exists():raise ValueError('Run directory already exists; choose a new directory')
    manifest_path=ROOT/'cases'/(a.case+'.json');manifest=json.loads(manifest_path.read_text())
    source,plan=safe_inputs(manifest,a.inputs,a.input_layout)
    if source==run or source in run.parents:
        raise ValueError('Run directory must be outside the source input directory')
    build_path,build,exe,libraries,library_dir=load_build(a.build,a.profile)
    # A private source-name fixture changes filenames only, never input bytes.
    # It supports both the original examples and the staged Windows reference kit.
    run.mkdir(parents=True,mode=0o700)
    fixture=run/'input-fixture';fixture.mkdir(mode=0o700)
    for src,name in plan:
        target=fixture/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,target)
    case_run=run/'case'
    capture.stage(manifest_path,fixture,case_run,a.case=='detroit')
    capture.write_new(run/'input-origin.json',{'directory':str(source),'layout':a.input_layout,
        'manifest':digest(manifest_path),'input_count':len(plan),
        'note':'Private source-name fixture; no input-content edit.'})
    env=dict(os.environ)
    for key in REMOVED_ENV:env.pop(key,None)
    env['LD_LIBRARY_PATH']=str(library_dir)
    compatibility=a.profile=='windows-compatible-invalid-only'
    if compatibility:env['W2_INVALID_MASK_LOG']=str(case_run/'invalid-mask-receipt.txt')
    capture.begin(case_run,exe,'linux-cli',build_path,libraries)
    command=[str(exe),str(case_run/'model')]
    capture.write_new(case_run/'invocation.json',{'argv':command,'cwd':str(case_run/'model'),
        'profile':a.profile,'case':a.case,'wrapper_sha256':digest(__file__)['sha256'],
        'explicit_environment':{key:env.get(key) for key in ('LD_LIBRARY_PATH',*REMOVED_ENV)},
        'only_authorized_mask_action':compatibility,'core_dump_limit':0,
        'target':'Ubuntu 24.04 x86-64; this receipt records the actual host, not assumed target validation'})
    def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    start=time.monotonic()
    with (case_run/'stdout.txt').open('xb') as stdout,(case_run/'stderr.txt').open('xb') as stderr:
        with subprocess.Popen(command,cwd=case_run/'model',env=env,
                stdout=stdout,stderr=stderr,preexec_fn=no_core) as proc:
            time.sleep(.05)
            capture.write_new(case_run/'observed-runtime.json',capture.observe_linux_runtime(proc.pid))
            model_rc=proc.wait()
    if any(x.name.lower()=='debug.log' for x in (case_run/'model').rglob('*')):
        raise ValueError('Unexpected excluded vendor-log name; no output sweep performed')
    result=capture.finish(case_run,model_rc,'Actual native exit and full output inventory; numerical acceptance is a separate comparison.')
    fp,errors,wrapper_rc=verify_completion(case_run,model_rc,compatibility,result['changed_or_missing_inputs'])
    summary={'profile':a.profile,'case':a.case,'actual_model_exit':model_rc,
        'elapsed_seconds':time.monotonic()-start,'outputs':len(result['outputs']),
        'run':str(run),'case_run':str(case_run),'fp_receipt_valid':fp['FP_receipt_valid'] if fp else None,
        'verification_errors':errors,
        'scientific_acceptance':'Not assessed by the launcher. Compare full captured outputs to the accepted reference.',
        'wrapper_exit':wrapper_rc}
    capture.write_new(run/'run-result.json',summary)
    print(json.dumps(summary,indent=2))
    return summary['wrapper_exit']

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,AssertionError) as error:
        print('RUN STOPPED: '+str(error),file=sys.stderr);sys.exit(2)
