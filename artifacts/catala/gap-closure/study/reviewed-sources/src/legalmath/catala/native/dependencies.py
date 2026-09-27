"""Closed, source-pinned standard library and separately pinned trace compiler."""
import json
from pathlib import Path
import re
from ...canonical import raw_digest
from .contracts import fail

REPO = Path(__file__).resolve().parents[4]
TRACE = REPO / '.localresources/catala-toolchain/native-trace-v1'
TRACE_LOCK = REPO / 'docs/implementation/catala/gap-closure/trace-toolchain.json'


def trace_tools():
    locked = json.loads(TRACE_LOCK.read_bytes())
    files = {'catala': locked['compiler_sha256'], 'java-trace.patch': locked['patch_sha256'],
             **locked['interpreter_plugins']}
    for name, expected in files.items():
        if raw_digest((TRACE / name).read_bytes()) != expected:
            fail('E_HASH_MISMATCH', 'Trace toolchain: ' + name)
    return TRACE / 'catala', locked


def library(task, upstream, locked, staging, command):
    """Return exact transitive sources and Java source names; no ambient includes."""
    if not task.get('imports'):
        return {}, []
    upstream, staging = Path(upstream), Path(staging)
    _, traced = trace_tools()
    sources, java, seen = {}, [], set()

    def checked(name):
        data = (upstream / name).read_bytes()
        if raw_digest(data) != locked['source_files'].get(name):
            fail('E_HASH_MISMATCH', 'Standard library source: ' + name)
        return data

    def visit(module):
        if module in seen:
            return
        if not re.fullmatch(r'(Integer|Decimal|Money|Date|List)_(en|internal)', module):
            fail('E_UNSUPPORTED_PROFILE', 'Undeclared library dependency')
        seen.add(module)
        name = 'stdlib/' + module.lower() + '.catala_en'
        data = checked(name)
        sources[name] = data.decode()
        target = staging / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        for dependency in re.findall(r'^> Using (\w+)', data.decode(), re.M):
            visit(dependency)
        java_name = module + '.java'
        if module.endswith('_internal'):
            text = checked('stdlib/java/' + module.lower() + '.java')
            sources['stdlib/java/' + module.lower() + '.java'] = text.decode()
            (staging / java_name).write_bytes(text)
            plugin = 'stdlib/ocaml/' + module + '.cmxs'
            (staging / plugin).parent.mkdir(parents=True, exist_ok=True)
            (staging / plugin).write_bytes((TRACE / plugin).read_bytes())
        else:
            command([locked['compiler_path_resolved'], 'java', name, '--no-stdlib', '-I', 'stdlib',
                     '--check-invariants', '--output', java_name], staging)
        java.append(java_name)
    for name in task['imports']:
        visit(name)
    return {'sources': sources, 'source_hashes': {n: raw_digest(t.encode()) for n,t in sources.items()},
            'interpreter_plugins': {n: h for n,h in traced['interpreter_plugins'].items()
                                    if n.split('/')[-1].removesuffix('.cmxs') in seen}}, java


def interpreter_library(manifest, directory, staging):
    dependencies = manifest.get('dependencies', {})
    if not dependencies:
        return []
    for name, text in dependencies['sources'].items():
        if raw_digest(text.encode()) != dependencies['source_hashes'].get(name):
            fail('E_HASH_MISMATCH')
        p = Path(staging) / name
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
    for name, expected in dependencies['interpreter_plugins'].items():
        data = (Path(directory) / name).read_bytes()
        if raw_digest(data) != expected:
            fail('E_HASH_MISMATCH')
        p = Path(staging) / name
        p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    return ['-I', 'stdlib', '--whole-program']
