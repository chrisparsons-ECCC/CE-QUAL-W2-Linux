#!/usr/bin/env python3
"""Fresh, byte-pinned case staging and run evidence. No scientific input editing."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import shutil
import subprocess
import sys
import time

ENV_KEYS = ('OMP_NUM_THREADS', 'OMP_DYNAMIC', 'OMP_SCHEDULE', 'KMP_DETERMINISTIC_REDUCTION',
            'KMP_AFFINITY', 'MKL_NUM_THREADS', 'MKL_DYNAMIC', 'GFORTRAN_UNBUFFERED_ALL')
WINDOWS_REFERENCE_SHA256 = '0eb294897682d6d3dabfac4ba6dc70fe96cfc29de7ebfdc75ffd6e6500edb163'


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return {'bytes': Path(path).stat().st_size, 'sha256': h.hexdigest()}


def write_new(path, data):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def safe_relative_name(name):
    """Manifests use explicit portable / components, never traversal or OS devices."""
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name or
            any(ord(c) < 32 for c in name)):
        raise ValueError('Unsafe relative path in case manifest')
    parts = name.split('/')
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) or PureWindowsPath(p).is_reserved() for p in parts):
        raise ValueError('Unsafe relative path in case manifest')
    return name


def files(root):
    result = {}
    for p in sorted(Path(root).rglob('*')):
        if p.is_symlink():
            raise ValueError('Symlinks are not accepted: ' + str(p))
        if p.is_file():
            result[p.relative_to(root).as_posix()] = digest(p)
    return result


def stage(manifest_path, source, run, linux_literal_path_aliases=False):
    manifest_path, source, run = map(Path, (manifest_path, source, run))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if run.exists():
        raise ValueError('Run directory already exists; use a new directory')
    if source.resolve() in run.resolve().parents:
        raise ValueError('Run directory must be outside the original source example')
    sources, destinations = set(), set()
    source_entries = list(source.rglob('*'))
    if any(p.is_symlink() for p in source_entries):
        raise ValueError('Symlinks are not accepted in source cases')
    folded = [p.relative_to(source).as_posix().casefold() for p in source_entries]
    if len(folded) != len(set(folded)):
        raise ValueError('Ambiguous case-fold collision in source directory')
    for item in manifest['inputs']:
        src, dst = safe_relative_name(item['source']), safe_relative_name(item['staged'])
        if src.casefold() in sources or dst.casefold() in destinations:
            raise ValueError('Duplicate or case-fold colliding manifest entry')
        sources.add(src.casefold()); destinations.add(dst.casefold())
        p = source / src
        if p.is_symlink() or not p.is_file() or digest(p) != {k: item[k] for k in ('bytes', 'sha256')}:
            raise ValueError('Source input missing, symlinked or hash changed: ' + src)
    plan = list(manifest['inputs'])
    aliases = []
    if linux_literal_path_aliases:
        if platform.system() != 'Linux':
            raise ValueError('Literal-backslash compatibility aliases are Linux-only')
        allowed = {i['source']: i for i in manifest['inputs']}
        for item in manifest.get('linux_literal_path_aliases', []):
            src, dst = safe_relative_name(item['source']), item['staged']
            if src not in allowed or not isinstance(dst, str) or '/' in dst or not dst.startswith('.\\'):
                raise ValueError('Literal alias must map an allowlisted source with exact .\\ prefix')
            normalized = safe_relative_name(dst[2:].replace('\\', '/'))
            if normalized.casefold() != src.casefold():
                raise ValueError('Literal alias path does not match its allowlisted source')
            if any(item[k] != allowed[src][k] for k in ('bytes', 'sha256')):
                raise ValueError('Literal alias hash differs from its allowlisted source')
            if dst.casefold() in destinations:
                raise ValueError('Duplicate or case-fold colliding literal alias')
            destinations.add(dst.casefold()); aliases.append(item)
        if not aliases:
            raise ValueError('Linux literal aliases requested but none declared in manifest')
        plan += aliases
    for name in destinations:
        if any('/'.join(name.split('/')[:n]) in destinations for n in range(1, len(name.split('/')))):
            raise ValueError('Manifest destination file conflicts with a parent directory')
    run.mkdir(parents=True)
    model = run / 'model'; model.mkdir()
    for item in plan:
        target = model / item['staged']; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / item['source'], target)
    staged = files(model)
    expected = {i['staged']: {k: i[k] for k in ('bytes', 'sha256')} for i in plan}
    if staged != expected:
        raise ValueError('Staged input verification failed')
    write_new(run / 'staging.json', {'schema': 1, 'created_utc': utc(), 'case': manifest,
              'source_directory': str(source.resolve()), 'manifest': digest(manifest_path),
              'inputs': staged, 'enabled_linux_literal_path_aliases': aliases,
              'excluded_source_names': sorted(p.relative_to(source).as_posix() for p in source_entries
                  if p.is_file() and p.relative_to(source).as_posix().casefold() not in sources)})
    return {'run_directory': str(run.resolve()), 'input_files': len(staged),
            'case_id': manifest['case_id'], 'status': 'staged; not run'}


def begin(run, executable, kind, build_metadata, runtime_files=()):
    run, executable = Path(run).resolve(), Path(executable).resolve()
    staging = json.loads((run / 'staging.json').read_text())
    if files(run / 'model') != staging['inputs']:
        raise ValueError('Model directory is not pristine staged inputs')
    exe = digest(executable)
    if kind == 'official-windows-gui':
        if platform.system() != 'Windows':
            raise ValueError('Official reference capture requires actual Windows')
        if exe['sha256'] != WINDOWS_REFERENCE_SHA256:
            raise ValueError('Executable differs from pinned official reference')
    # Read only the explicitly supplied build record, never sweep source/IDE logs.
    build = json.loads(Path(build_metadata).read_text(encoding='utf-8'))
    result = {'schema': 1, 'started_utc': utc(), 'kind': kind, 'working_directory': str(run / 'model'),
              'executable': dict(exe, path=str(executable)), 'build_metadata': build,
              'build_metadata_file': digest(build_metadata), 'platform': platform.platform(),
              'machine': platform.machine(), 'processor': platform.processor(),
              'python': platform.python_version(), 'capture_tool': digest(__file__), 'environment_allowlist': {k: os.environ.get(k) for k in ENV_KEYS},
              'runtime_files': {str(Path(p).resolve()): digest(p) for p in runtime_files},
              'runtime_inventory_complete': False,
              'input_files': staging['inputs'], 'staging_record': digest(run / 'staging.json')}
    write_new(run / 'run-start.json', result)
    return result


def finish(run, exit_code=None, completion_note='Not independently verified'):
    run = Path(run)
    start = json.loads((run / 'run-start.json').read_text())
    actual = files(run / 'model')
    changed = [p for p, h in start['input_files'].items() if actual.get(p) != h]
    outputs = {p: h for p, h in actual.items() if p not in start['input_files']}
    staging = json.loads((run / 'staging.json').read_text())
    required = staging['case']['parsed_outputs']
    result = {'schema': 1, 'finished_utc': utc(), 'exit_code': exit_code,
              'completion_note': completion_note, 'scientific_acceptance': 'not assessed',
              'changed_or_missing_inputs': changed, 'outputs': outputs,
              'missing_expected_parsed_outputs': sorted(set(required) - set(outputs)),
              'run_start_record': digest(run / 'run-start.json'),
              'execution_records': {name: digest(run / name) for name in
                  ('invocation.json', 'stdout.txt', 'stderr.txt', 'observed-runtime.json') if (run / name).is_file()},
              'output_coverage': 'Hashes cover all generated regular files; numerical parsing is separate'}
    write_new(run / 'capture.json', result)
    return result


def observe_linux_runtime(pid):
    """One bounded read of our own child's mapped libraries; never its environment."""
    record = {'observed_utc': utc(), 'scope': 'One /proc maps snapshot; later loads may be absent',
              'libraries': [], 'observation_errors': []}
    try:
        paths = set()
        for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
            parts = line.split(maxsplit=5)
            if len(parts) == 6 and parts[5].startswith('/') and '.so' in parts[5]:
                paths.add(parts[5])
        for path in sorted(paths):
            try: record['libraries'].append(dict(path=path, **digest(path)))
            except OSError as exc: record['observation_errors'].append(str(exc))
    except OSError as exc:
        record['observation_errors'].append(str(exc))
    try:
        record['cpu_model_names'] = sorted(set(line.split(':', 1)[1].strip()
            for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')))
        record['os_release'] = Path('/etc/os-release').read_text()
    except OSError as exc:
        record['observation_errors'].append(str(exc))
    return record


def run_linux(args):
    if platform.system() != 'Linux':
        raise ValueError('run-linux requires Linux; use the genuine Windows GUI capture route for references')
    run = Path(args.run_dir).resolve()
    begin(run, args.executable, 'linux-cli', args.build_metadata, args.runtime)
    command = [str(Path(args.executable).resolve()), str(run / 'model')]
    write_new(run / 'invocation.json', {'argv': command, 'cwd': str(run / 'model')})
    with (run / 'stdout.txt').open('xb') as out, (run / 'stderr.txt').open('xb') as err:
        try:
            with subprocess.Popen(command, cwd=run / 'model', stdout=out, stderr=err) as process:
                time.sleep(0.05)
                write_new(run / 'observed-runtime.json', observe_linux_runtime(process.pid))
                returncode = process.wait()
        except OSError as exc:
            err.write((str(exc) + '\n').encode())
            return finish(run, None, 'Failed to launch; see stderr.txt')
    return finish(run, returncode, 'Process exited; solver completion must be checked against outputs/logs')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('stage')
    s.add_argument('--manifest', required=True); s.add_argument('--source-dir', required=True)
    s.add_argument('--run-dir', required=True)
    s.add_argument('--linux-literal-path-aliases', action='store_true')
    for name in ('begin', 'run-linux'):
        s = sub.add_parser(name)
        s.add_argument('--run-dir', required=True); s.add_argument('--executable', required=True)
        s.add_argument('--build-metadata', required=True); s.add_argument('--runtime', action='append', default=[])
        if name == 'begin':
            s.add_argument('--kind', choices=['official-windows-gui', 'linux-cli'], required=True)
    s = sub.add_parser('finish')
    s.add_argument('--run-dir', required=True); s.add_argument('--exit-code', type=int)
    s.add_argument('--completion-note', default='Not independently verified')
    args = p.parse_args()
    try:
        if args.command == 'stage': result = stage(args.manifest, args.source_dir, args.run_dir, args.linux_literal_path_aliases)
        elif args.command == 'begin': result = begin(args.run_dir, args.executable, args.kind, args.build_metadata, args.runtime)
        elif args.command == 'finish': result = finish(args.run_dir, args.exit_code, args.completion_note)
        else: result = run_linux(args)
    except (ValueError, OSError, KeyError) as exc:
        p.exit(2, str(exc) + '\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    if args.command in ('finish', 'run-linux'):
        return int(bool(result['changed_or_missing_inputs'] or result['missing_expected_parsed_outputs'] or
                        result['exit_code'] not in (None, 0)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
