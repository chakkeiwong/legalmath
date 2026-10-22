"""Explicit optional source-product execution over declared sealed native files."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

from . import sealed_runtime

_ACTIVE = ContextVar('prospectus_sealed_source_runtime', default=None)


class SourceRuntime:
    def __init__(self, folder, manifest_sha256, *, evidence_directory=None, native_text_max_stream=None):
        self.folder = Path(folder).resolve(strict=True)
        self.manifest = sealed_runtime.validate(json.loads((self.folder / 'manifest.json').read_text()))
        if sealed_runtime.digest(self.manifest) != manifest_sha256:
            raise ValueError('Source runtime manifest identity mismatch')
        self.manifest_sha256 = manifest_sha256
        self.receipts = []
        self.native_text_max_stream = sealed_runtime.stream_bound(native_text_max_stream)
        self.evidence_directory = Path(evidence_directory) if evidence_directory is not None else None
        if self.evidence_directory is not None:
            self.evidence_directory.mkdir(parents=True, exist_ok=False)

    def execute(self, argv, stdin, required_files, *, max_stream=None):
        if sealed_runtime.digest(self.manifest) != self.manifest_sha256:
            raise ValueError('Source runtime manifest changed')
        rows = {r['path']: r for r in self.manifest['files']}
        if not isinstance(required_files, dict) or not required_files:
            raise ValueError('Source execution requires explicit input bindings')
        for name, expected in required_files.items():
            sealed_runtime.destination(name)
            if name not in rows or rows[name]['sha256'] != expected:
                raise ValueError('Required native input absent or different: ' + name)
        if argv[0] not in required_files:
            raise ValueError('Source executable must be bound to its current bytes')
        result = sealed_runtime.run(self.folder, self.manifest, argv, stdin, timeout=60, max_stream=max_stream)
        receipt = result['receipt']
        sealed_runtime.verify_receipt(receipt, self.manifest, argv, stdin, result['stdout'], result['stderr'])
        if self.evidence_directory is not None:
            evidence = self.evidence_directory / str(len(self.receipts))
            evidence.mkdir()
            for name, data in {'stdin': stdin, 'stdout': result['stdout'], 'stderr': result['stderr'],
                               'receipt.json': json.dumps(receipt, indent=2).encode()}.items():
                with (evidence / name).open('xb') as stream:
                    stream.write(data)
        self.receipts.append(deepcopy(receipt))
        if result['returncode']:
            raise subprocess.CalledProcessError(result['returncode'], argv, result['stdout'], result['stderr'])
        return result


@contextmanager
def selected(runtime):
    if not isinstance(runtime, SourceRuntime):
        raise ValueError('Explicit SourceRuntime required')
    if _ACTIVE.get() is not None:
        raise ValueError('Nested source runtime selection is ambiguous')
    token = _ACTIVE.set(runtime)
    try:
        yield runtime
    finally:
        _ACTIVE.reset(token)


def current():
    return _ACTIVE.get()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def worker_inputs(interpreter, worker, spec, profile):
    return {str(interpreter): file_digest(interpreter), str(worker): file_digest(worker),
            str(Path(worker).with_name('native_inputs.py')): file_digest(Path(worker).with_name('native_inputs.py')),
            spec['source']: spec.get('source_sha256', file_digest(spec['source'])),
            **{str(Path(spec['tessdata']) / (lang + '.traineddata')): hashed
               for lang, hashed in profile['models'].items()}}


def source_product(request, root, runtime):
    """All supported native source calls use this runtime; no fallback on failure."""
    from . import service
    with selected(runtime):
        return service.source_product(request, root)
