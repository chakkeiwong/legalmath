"""Current criterion evidence survives scheduling changes, never changed proof."""
from pathlib import Path

VERSION = 'criterion-evidence.v1'
SCOPE = ('id', 'handler', 'stream', 'obligations', 'acceptance', 'depends_on', 'budget_key')


def contracts(task, program):
    value = task.get('build_criterion_lineage', {})
    rows = program.get('build_contract', {}).get('criteria', {}).get(task['id'], [])
    eligible = {r['id'] for r in rows if r['basis'] == 'NAMED_CONDITIONAL_CHECK'}
    if not isinstance(value, dict) or set(value) - eligible:
        raise ValueError('Criterion lineage requires an existing conditional criterion')
    for contract in value.values():
        if (not isinstance(contract, dict) or set(contract) != {'version', 'files', 'trees'}
                or contract['version'] != VERSION):
            raise ValueError('Invalid criterion evidence contract')
        for key in ('files', 'trees'):
            paths = contract[key]
            if (not isinstance(paths, list) or not paths or
                    any(not isinstance(n, str) or not n or Path(n).is_absolute()
                        or '..' in Path(n).parts for n in paths) or
                    paths != sorted(set(paths))):
                raise ValueError('Criterion evidence paths must be unique relative paths')
        if not set(contract['files']) <= set(task['inputs']):
            raise ValueError('Criterion evidence files must be admitted inputs')
    return value


def snapshot(authority, contract):
    from .execution_authority import CODE, file_hash
    names = set(CODE) | set(contract['files']) | {
        'src/legalmath/prospectus/criterion_evidence.py'}
    for tree in contract['trees']:
        directory = authority.path(tree)
        if not directory.is_dir():
            raise ValueError('Criterion production tree missing')
        names.update(str(p.relative_to(authority.root)) for p in directory.rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts
                     and p.suffix not in {'.pyc', '.pyo'})
    return {n: file_hash(authority.path(n)) for n in sorted(names)}


def receipt(authority, task, row, contract):
    from .execution_authority import digest
    return {'version': VERSION, 'criterion_sha256': digest(row),
            'task_scope_sha256': digest({k: task[k] for k in SCOPE}),
            'contract': contract, 'files': snapshot(authority, contract)}


def issue(authority, admission, task, program, passed):
    """Called only after registered substantive validators return success."""
    rows = {r['id']: r for r in program.get('build_contract', {}).get('criteria', {}).get(task['id'], [])}
    result = {}
    for key, contract in contracts(task, program).items():
        if key not in passed:
            continue
        value = receipt(authority, task, rows[key], contract)
        if any(admission['binding'].get(n) != h for n, h in value['files'].items()):
            raise ValueError('Criterion evidence was not frozen at admission')
        result[key] = value
    return result


def conditional(authority, program, tasks, events, latest):
    """Newest submitted result governs each criterion; no fallback on failure."""
    from .execution_authority import digest, file_hash, read
    selected = {}
    admitted = {e['attempt']: e for e in events if e['kind'] == 'ADMIT'}
    lineage = {key: contracts(task, program) for key, task in tasks.items()}
    for event in reversed(events):
        task_id = event.get('task')
        if task_id not in tasks or event['kind'] not in {'RECORD', 'ACCEPT', 'REJECT', 'INTERRUPT'}:
            continue
        rows = program.get('build_contract', {}).get('criteria', {}).get(task_id, [])
        names = {r['id'] for r in rows if r['basis'] == 'NAMED_CONDITIONAL_CHECK'
                 and (task_id, r['id']) not in selected
                 and (r['id'] in lineage[task_id] or event == latest.get(task_id))}
        if not names:
            continue
        try:
            path = authority.path(event['attempt']) / 'admission.json'
            if file_hash(path) != admitted[event['attempt']]['admission_sha256']:
                raise ValueError('Admission changed')
            old = read(path)['task_spec']
            claimed = set(old.get('build_criteria_scope', names)) & names
            # Missing acceptance on a submitted criterion, including a failed
            # validator, supersedes old success. Unrelated records do not.
            for key in claimed:
                selected[(task_id, key)] = event
        except (OSError, ValueError, KeyError, TypeError):
            for key in names:
                selected[(task_id, key)] = None
    accepted = {}
    for (task_id, key), event in selected.items():
        if not event or event['kind'] not in {'RECORD', 'ACCEPT'} or key not in event.get('build_acceptances', []):
            continue
        task = tasks[task_id]
        rows = program['build_contract']['criteria'][task_id]
        try:
            stored = event.get('build_evidence', {}).get(key)
            if stored is None:
                valid = (event == latest.get(task_id)
                         and event.get('build_criteria_sha256') == digest(rows)
                         and authority.attempt_valid(event, task))
            else:
                contract = contracts(task, program).get(key)
                row = next(r for r in rows if r['id'] == key)
                path = authority.path(event['attempt']) / 'admission.json'
                original = read(path)
                valid = (contract is not None
                         and file_hash(path) == admitted[event['attempt']]['admission_sha256']
                         and authority.retained_evidence_valid(event)
                         and original['task_spec'].get('build_criterion_lineage', {}).get(key) == contract
                         and stored == receipt(authority, task, row, contract)
                         and all(original['binding'].get(n) == h for n, h in stored['files'].items()))
            if valid:
                accepted.setdefault(task_id, []).append(key)
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            pass
    return accepted
