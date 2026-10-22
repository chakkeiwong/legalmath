"""Finite source accounting for review preparation; never certify independence."""
from collections import defaultdict
from pathlib import Path
import json
from .anchors import fields
from .contracts import digest


def _file(root, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Nonempty source path required')
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Source path escapes worktree')
    return path


def _evidence(root, evidence):
    fields(evidence, {'path', 'sha256', 'quote'}, {'path', 'sha256', 'quote'})
    path = _file(root, evidence['path'])
    if not path.is_file() or digest(path.read_bytes()) != evidence['sha256']:
        raise ValueError('Preparation evidence bytes changed or unavailable')
    quote = evidence['quote']
    if not isinstance(quote, str) or not quote.strip() or quote not in path.read_text():
        raise ValueError('Preparation evidence quote changed')
    return dict(evidence)


def _documents(data):
    if not isinstance(data, dict):
        raise ValueError('Manifest object required')
    docs = data.get('documents')
    if docs is None:
        if not any(k in data for k in ('original', 'path', 'file')):
            raise ValueError('Explicit manifest document inventory required')
        docs = [data]
    if isinstance(docs, dict):
        rows = []
        for key, row in docs.items():
            if not isinstance(row, dict) or row.get('id', key) != key:
                raise ValueError('Manifest document key/identity mismatch')
            rows.append({**row, 'id': key})
        return rows
    if not isinstance(docs, list) or any(not isinstance(r, dict) for r in docs):
        raise ValueError('Manifest document list required')
    return docs


def _source(root, manifest, row):
    declarations = {key: row[key] for key in ('file', 'original', 'path') if key in row}
    if not declarations:
        raise ValueError('No declared original-file path')
    resolved = []
    for key, name in declarations.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Nonempty declared source path required')
        candidates = {(manifest.parent / name).resolve()}
        if key != 'file':
            candidates.add((root / name).resolve())
        if any(not p.is_relative_to(root) for p in candidates):
            raise ValueError('Declared source path escapes worktree')
        available = [p for p in candidates if p.is_file()]
        if len(available) != 1:
            raise ValueError('Declared source is missing or path resolution is ambiguous')
        resolved.append(available[0])
    if len(set(resolved)) != 1:
        raise ValueError('Conflicting source path fields')
    path = resolved[0]
    actual = digest(path.read_bytes())
    expected = [row[k] for k in ('sha256', 'source_sha256') if k in row]
    if not expected or any(h != actual for h in expected):
        raise ValueError('Declared source hash missing or mismatched')
    return {'source': str(path.relative_to(root)), 'sha256': actual,
            'bytes': path.stat().st_size, 'path_declarations': declarations}


def build(root, manifests, family_assignments, development_evidence):
    """Account for each declared entry; supplied family evidence only excludes."""
    root = Path(root).resolve()
    if not isinstance(manifests, list) or not manifests or len(set(manifests)) != len(manifests):
        raise ValueError('Distinct nonempty frozen manifest denominator required')
    if not isinstance(family_assignments, dict) or not isinstance(development_evidence, dict):
        raise ValueError('Explicit family and development-evidence mappings required')
    rows, bindings = [], {}
    for name in manifests:
        path = _file(root, name)
        if not path.is_file():
            raise ValueError('Frozen manifest unavailable')
        binding = digest(path.read_bytes());bindings[name] = binding
        docs = _documents(json.loads(path.read_text()));seen = set()
        for index, doc in enumerate(docs):
            identity = doc.get('id') or doc.get('document_id')
            if isinstance(identity, str) and identity in seen:
                raise ValueError('Duplicate document identity within manifest')
            key = name + '#' + (identity if isinstance(identity, str) and identity else '@' + str(index))
            row = {'entry': key, 'manifest': name, 'manifest_sha256': binding,
                   'index': index, 'id': identity, 'issues': [], 'eligible_as_unexposed': False}
            if not isinstance(identity, str) or not identity.strip() or identity in seen:
                row['issues'].append('Missing or duplicate document identity within manifest')
            if isinstance(identity, str):seen.add(identity)
            try:
                row.update(_source(root, path, doc))
            except ValueError as exc:
                row['issues'].append(str(exc))
            assignment = family_assignments.get(key)
            if assignment is not None:
                fields(assignment, {'family', 'reason', 'evidence'}, {'family', 'reason', 'evidence'})
                if (not isinstance(assignment['family'], str) or not assignment['family'].strip() or
                    not isinstance(assignment['reason'], str) or not assignment['reason'].strip() or
                    not isinstance(assignment['evidence'], list) or not assignment['evidence']):
                    raise ValueError('Explicit reviewed family assignment and evidence required')
                row['family'] = assignment['family']
                row['family_assignment'] = {**assignment, 'evidence': [_evidence(root, e) for e in assignment['evidence']]}
            else:
                row['family'] = None
            evidence = development_evidence.get(key, [])
            if not isinstance(evidence, list):
                raise ValueError('Development evidence list required')
            row['direct_development_evidence'] = [_evidence(root, e) for e in evidence]
            if doc.get('data_role') == 'development':
                row['direct_development_evidence'].append({'manifest': name, 'sha256': binding,
                    'entry': key, 'data_role': 'development'})
            rows.append(row)
    keys = {r['entry'] for r in rows}
    if set(family_assignments) - keys or set(development_evidence) - keys:
        raise ValueError('Review metadata names entries outside the frozen denominator')
    exposed = {r['entry'] for r in rows if r['direct_development_evidence']}
    # A duplicate source can bridge two supplied family aliases. Iterate to a
    # finite fixed point so every connected exposed document remains excluded.
    while True:
        hashes = {r['sha256'] for r in rows if r['entry'] in exposed and 'sha256' in r}
        families = {r['family'] for r in rows if r['entry'] in exposed and r['family'] is not None}
        extra = {r['entry'] for r in rows if r.get('sha256') in hashes or
                 (r['family'] is not None and r['family'] in families)}
        if extra <= exposed:break
        exposed |= extra
    aliases = defaultdict(list)
    for r in rows:
        if 'sha256' in r:aliases[r['sha256']].append(r['entry'])
    for row in rows:
        row['exposure'] = 'CONFIRMED_DEVELOPMENT' if row['entry'] in exposed else 'NOT_ESTABLISHED'
        row['source_aliases'] = sorted(aliases.get(row.get('sha256'), []))
        row['exposure_basis_entries'] = sorted(r['entry'] for r in rows if r['entry'] in exposed and
            ((row.get('sha256') is not None and row.get('sha256') == r.get('sha256')) or
             (row['family'] is not None and row['family'] == r['family'])))
    body = {'version': 'review-preparation-inventory.v2', 'manifests': bindings, 'documents': rows,
            'document_count': len(rows), 'source_issue_count': sum(bool(r['issues']) for r in rows),
            'scope': 'Only the explicitly frozen manifest entries; other repository sources are outside this accounting',
            'unexposed_cohort_established': False, 'complete_family_alias_inventory': False,
            'independent_legal_acceptance': False}
    return {**body, 'sha256': digest(body)}


def preflight(inventory, entries):
    """Return exclusions and unknowns; this preparation never admits a cohort."""
    if inventory.get('sha256') != digest({k:v for k,v in inventory.items() if k != 'sha256'}):
        raise ValueError('Preparation inventory changed')
    if not isinstance(entries, list) or not entries or len(set(entries)) != len(entries):
        raise ValueError('Distinct explicit candidate entries required')
    by_key = {r['entry']:r for r in inventory['documents']}
    if set(entries) - set(by_key):raise ValueError('Candidate outside frozen inventory')
    reasons = []
    for key in entries:
        row = by_key[key]
        reason = 'SOURCE_INTEGRITY_UNRESOLVED' if row['issues'] else (
            'EXPOSED_DEVELOPMENT_SOURCE_OR_FAMILY' if row['exposure'] == 'CONFIRMED_DEVELOPMENT' else
            'UNEXPOSED_STATUS_NOT_ESTABLISHED')
        reasons.append({'entry': key, 'reason': reason})
    return {'status': 'BLOCKED_INDEPENDENT_COHORT', 'inventory_sha256': inventory['sha256'],
            'candidates': reasons, 'eligible': False, 'independent_legal_acceptance': False,
            'next_requirement': 'Actual administrator evidence of a complete unexposed cohort and authenticated independent assignments/readings'}
