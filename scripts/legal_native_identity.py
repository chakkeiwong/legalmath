"""Content identities of the selected installed native adapter dependencies.

These identify the inspected executable/source/library trees, not an operating
system attestation. Cache files and repository administration are not inputs.
"""
from hashlib import sha256
from pathlib import Path


def content_identity(paths):
    rows = []
    for root in sorted({Path(p).absolute() for p in paths}):
        if not root.exists():
            raise ValueError('Native dependency absent: ' + str(root))
        members = sorted(p for p in root.rglob('*') if p.is_file()) if root.is_dir() else [root]
        files = []
        for member in members:
            relative = member.relative_to(root).as_posix() if root.is_dir() else member.name
            if {'__pycache__', '.git', '.pytest_cache'} & set(Path(relative).parts):
                continue
            files.append({'path': relative, 'sha256': sha256(member.read_bytes()).hexdigest(),
                          'symlink_target': str(member.resolve()) if member.is_symlink() else None})
        if not files:
            raise ValueError('Native dependency tree empty: ' + str(root))
        import json
        rows.append({'path': str(root), 'file_count': len(files),
                     'content_sha256': sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()})
    return {'profile': 'native-selected-content.v1', 'trees': rows,
            'excluded': ['__pycache__', '.git', '.pytest_cache'],
            'scope': 'Selected package/source/schema/native trees; OS loader and service remain separate.'}


def selected_content(tools, resource, repository):
    resource, repository = Path(resource), Path(repository)
    site = resource / 'venv/lib/python3.11/site-packages'
    paths = [resource / 'venv/pyvenv.cfg']
    def installed(base, package):
        matches = [p for p in base.iterdir() if p.name == package or p.name == package + '.py'
                   or p.name == package + '.libs' or
                   (p.name.startswith(package + '-') and p.name.endswith('.dist-info'))]
        if not matches: raise ValueError('Required distribution absent: ' + package)
        paths.extend(matches)
    if 'bm25' in tools:
        for package in ('rank_bm25', 'numpy'): installed(site, package)
    if 'legalruleml' in tools:
        installed(site, 'lxml')
        paths += [resource / 'legalruleml-source/xsd-schema', resource / 'xml.xsd']
    if 'pyarg' in tools:
        paths.append(resource / 'pyarg-source')
        installed(site, 'networkx')
    if 'clingo' in tools:
        clingo_site = repository / '.localresources/assurance-tools/venv/lib/python3.11/site-packages'
        for package in ('clingo', 'cffi', 'pycparser'): installed(clingo_site, package)
        paths.extend(clingo_site.glob('_cffi_backend*.so'))
    if 'logical-english' in tools:
        from scripts.legal_mission_logical_english import PARSER
        paths += [PARSER, resource / 'swipl/usr/lib']
    # Carneades is a compiled Go binary already bound by ProductToolBackend;
    # its source tree is not a runtime dependency.
    return content_identity(paths)
