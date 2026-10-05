"""Future-source observations bind the full investigation, never a supplied grade.

Hashing retained execution establishes identity, not remote attestation or legal
truth. The existing component window remains available for its narrower claim.
"""
from copy import deepcopy
import inspect
from pathlib import Path

from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from ...qualification import prospective as ledger
from ...qualification.assurance import method_manifest as qualification_method
from .integrated import implementation_identity, source_processing_identity
from .integration_contract import read_evidence, evidence_file
from .diversity import identity as journal_identity
from ..search.models import Settings

PROFILE = 'legalmath.whole-investigation-observation.v1'


def file_identity(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise LegalMathError('E_DEPENDENCY', details='Missing method dependency: '+str(path))
    return {'path': str(path), 'sha256': raw_digest(path.read_bytes())}


def method(runner):
    """Derive settings from the actual dispatcher, provider and toolchains."""
    provider = runner.provider
    allowance = getattr(provider, 'allowance', None)
    provider_type = type(provider)
    provider_file = inspect.getsourcefile(provider_type)
    limits = None if allowance is None else {
        'global_maximum': allowance.maximum,
        'global_reservation_ceiling': allowance.reservation_ceiling,
        'arm_maximum': getattr(allowance, 'arm_maximum', getattr(allowance, 'slice_maximum', None)),
        'reservation_ledger': str(Path(allowance.path).resolve()),
        'arm_ledger': str(Path(allowance.slice_path).resolve()) if hasattr(allowance, 'slice_path') else None,
        'grant_sha256': raw_digest(allowance.grant_bytes) if hasattr(allowance, 'grant_bytes') else None}
    inherited = getattr(provider, 'issue_limits', None)
    if inherited is not None:
        limits['original_issue_maximum'] = inherited.binding['maximum_attempts']
        limits['original_issue_deadline_seconds'] = inherited.binding['deadline_seconds']
        limits['history_policy'] = 'PRESERVE_ORIGINAL_SPENDING_AND_START_TIME'
        limits['original_issue_ledger'] = str(inherited.path.resolve())
    tool_python = Path(__file__).parents[4]/'.localresources/assurance-tools/venv/bin/python'
    catala = None if runner.catala is None else {
        key: file_identity(runner.catala[key]) for key in ('compiler', 'lock')}
    from . import challenge_panel
    panel = (challenge_panel.configuration(runner.challenge_providers,**{'input_profile':runner.input_profile,**runner.challenge_options})
             if getattr(runner,'challenge_options',None) is not None else None)
    from .evidence_identity import dependency_identity
    dependencies=(dependency_identity(['pydantic','pydantic-core','jsonschema','httpx','pypdf','z3-solver'])
                  if panel is not None else None)
    return {'profile': PROFILE, 'implementation': implementation_identity(),
        'qualification_implementation': digest(qualification_method()),
        'source_processing': source_processing_identity(tool_python),
        'provider': {'id': provider.provider_id,
            'class': provider_type.__module__+'.'+provider_type.__qualname__,
            'implementation': file_identity(provider_file) if provider_file else None,
            'route': deepcopy(getattr(provider, 'routing', None)),
            'live': getattr(provider, 'live', True) is not False,
            'remote_model_revision': 'NOT_ATTESTED',
            'executable': file_identity(provider.executable) if getattr(provider, 'executable', None) else None},
        'settings': runner.settings.model_dump(),
        'transports': {'core': runner.core_reference_protocol, 'scoped': runner.reference_protocol,
                       'readable_input': runner.input_profile if getattr(runner,'input_profile','literal')!='literal' else
                                         'NOT_ENABLED_IN_COMPLETE_INVESTIGATION'},
        'challenge_panel':panel,
        'installed_dependency_identity':dependencies,
        'scoped_provider_settings': Settings(timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000).model_dump(),
        'scoped': {'maximum_actions': runner.maximum_scoped_actions, 'rounds': runner.scoped_rounds,
                   'batch_size': runner.scoped_batch_size, 'pair_order': runner.scoped_pair_order,
                   'schedule': runner.scoped_schedule},
        'limits': {'outer': {'maximum_actions': 32, 'maximum_per_issue': 3, 'deadline_seconds': 86400},
                   'core': {'maximum_actions': 100, 'maximum_per_issue': 3, 'deadline_seconds': 86400},
                   'scoped': {'maximum_per_issue': 6, 'deadline_seconds': 86400},
                   'provider': limits},
        'questions': 'PROPOSED_FROM_ALL_RETAINED_CANDIDATES_OR_EXPLICITLY_QUALIFIED_ASSIGNMENTS',
        'authority': 'ACTUAL_CONTEXT_AND_RETAINED_AUTHORITY_RESOLUTIONS',
        'machine_qualification': runner.machine_qualification,
        'toolchains': {'java': {name: file_identity(runner.jdk/'bin'/name) for name in ('java', 'javac')},
                       'catala': catala},
        'qualification': 'Configured method and retained execution identity; remote model attestation and dependency correctness are not established.'}


def source_identity(sources):
    """Identity of the primary raw source; extra context cannot hide its reuse."""
    if not sources or any(set(s) != {'url', 'media_type', 'sha256'} for s in sources):
        raise LegalMathError('E_SCHEMA')
    for row in sources:
        ledger.sha(row['sha256'])
        if not all(isinstance(row[k], str) and row[k] for k in ('url', 'media_type')):
            raise LegalMathError('E_SCHEMA')
    return sources[0]['sha256']


def freeze(directory, runner, families, *, ends_at, development_sources=()):
    bound = method(runner)
    if not bound['machine_qualification']:
        raise LegalMathError('E_AUTHORITY', details='Whole observations require machine qualification')
    spec = ledger.freeze(directory, digest(bound), families, ends_at=ends_at,
                         development_sources=development_sources)
    ledger.put_new(Path(directory)/'investigation-method.json', bound)
    return spec


def frozen_method(directory, window_hash):
    spec, _ = ledger.load(directory, window_hash)
    bound = loads((Path(directory)/'investigation-method.json').read_bytes())
    if bound.get('profile') != PROFILE or digest(bound) != spec['method_hash']:
        raise LegalMathError('E_INTEGRITY', details='Whole method changed or component window supplied')
    return bound


def admit(directory, window_hash, item, runner):
    frozen_method(directory, window_hash)
    return ledger.admit(directory, window_hash, item, method_hash=digest(method(runner)))


def repair(directory, window_hash, runner, *, reason):
    frozen_method(directory, window_hash)
    return ledger.repair(directory, window_hash, new_method_hash=digest(method(runner)), reason=reason)


def check_stages(root, dossier, bound, runner):
    """Join stage receipts, original source/question and re-executed qualifications."""
    from .complete_investigation import verify
    from .qualification_adapter import verify as verify_qualification
    verify(root, dossier)
    if dossier.get('profile')=='complete-investigation-challenge-continuation.v1':
        raise LegalMathError('E_STALE_REVIEW', details='Retained-stage continuation is not a fresh whole-method observation')
    binding = dossier['binding']
    if (canonical(binding.get('investigation_method')) != canonical(bound) or
            digest(method(runner)) != digest(bound) or
            binding['implementation'] != bound['implementation'] or
            canonical(binding['settings']) != canonical(bound['settings']) or
            not binding.get('machine_qualification')):
        raise LegalMathError('E_STALE_REVIEW', details='Investigation does not use the frozen whole method')
    scoped = bound['scoped']
    if (binding['scoped_actions'] != scoped['maximum_actions'] or
            binding['scoped_rounds'] != scoped['rounds'] or
            binding['scoped_batch_size'] != scoped['batch_size'] or
            binding.get('scoped_pair_order', 'claim-first') != scoped['pair_order'] or
            binding.get('scoped_schedule', 'batch-first') != scoped['schedule'] or
            binding.get('source_reference_protocol', 'literal') != bound['transports']['scoped']):
        raise LegalMathError('E_STALE_REVIEW')
    # Absolute producer directories are allowed only inside this evidence root.
    location = Path(dossier['core']['interpretation']['directory']).resolve()
    root = Path(root).resolve()
    if not location.is_relative_to(root): raise LegalMathError('E_REFERENCE')
    retained = {r['path']: r for r in dossier['evidence']}
    def original(path):
        key = str(path.relative_to(root))
        if key not in retained:
            raise LegalMathError('E_REFERENCE', details='Required investigation stage was not retained: '+key)
        return read_evidence(retained[key], root)
    # interpretation lives at core/actions/action-N/interpretation.
    journal_path = location.parent.parent/'journal.json'
    journal = original(journal_path)
    if journal['sha256'] != journal_identity(journal['value']): raise LegalMathError('E_INTEGRITY')
    stages = [a for a in journal['value']['actions'] if a['status'] == 'EXECUTED']
    source = [a for a in stages if a['spec']['stage'] == 'source']
    interpretations = [a for a in stages if a['spec']['stage'] == 'interpretation']
    if not source or not interpretations: raise LegalMathError('E_REFERENCE', details='Missing source or interpretation stage')
    if canonical(source[-1]['spec']['inputs']['processing']) != canonical(bound['source_processing']):
        raise LegalMathError('E_STALE_REVIEW', details='Extractor/model identities differ')
    expected_sources = [{'url': s['url'], 'media_type': s['media_type'], 'hash': s['sha256']}
                        for s in binding['sources']]
    if canonical(source[-1]['spec']['inputs']['sources']) != canonical(expected_sources):
        raise LegalMathError('E_STALE_REVIEW')
    actual_interpretation = interpretations[-1]['spec']['inputs']
    expected_input=bound['transports']['readable_input']
    expected_input='literal' if expected_input=='NOT_ENABLED_IN_COMPLETE_INVESTIGATION' else expected_input
    if actual_interpretation.get('input_profile','literal')!=expected_input:
        raise LegalMathError('E_STALE_REVIEW',details='Actual input codec differs from the frozen method')
    if (canonical(actual_interpretation['settings']) != canonical(bound['settings']) or
            actual_interpretation['scope'] != binding['question'] or
            actual_interpretation['implementation'] != bound['implementation'] or
            actual_interpretation.get('source_reference_protocol', 'literal') != bound['transports']['core'] or
            actual_interpretation['authority_registry'] != binding['authority_catalog']):
        raise LegalMathError('E_STALE_REVIEW', details='Actual interpretation stage differs from frozen method/input')
    model_journal = original(location.parents[2]/'model-evidence'/'journal.json')
    if model_journal['sha256'] != journal_identity(model_journal['value']): raise LegalMathError('E_INTEGRITY')
    model_inputs = model_journal['value']['binding']['inputs']
    if canonical(model_inputs['route']) != canonical(bound['provider']['route'] or runner.provider.provider_id):
        raise LegalMathError('E_STALE_REVIEW', details='Actual provider route differs')
    authority = original(location/'authority-resolutions.json')
    context = original(location/'source-context.json')
    criticism = original(location/'criticism.json')
    packet = read_evidence(dossier['packet'], root)
    readings = read_evidence(dossier['candidates'], root)
    documents = {d['raw_sha256']: d for d in context['documents']}
    for source_input in binding['sources']:
        h = source_input['sha256']
        if h not in documents:
            raise LegalMathError('E_REFERENCE', details='Selected source missing from extraction context')
        rawpath = location/'sources'/(h+'.bin')
        rawref = retained.get(str(rawpath.relative_to(root)))
        if rawref is None or raw_digest(read_evidence(rawref, root, json_value=False)) != h:
            raise LegalMathError('E_INTEGRITY', details='Actual source bytes differ from admitted edition')
    claims = read_evidence(dossier['claims'], root)
    expected_pairs = {(c['claim_id'], cid) for c in claims for cid in readings}
    supplied_pairs = list(map(tuple, dossier['scoped']['required_pairs']))
    if len(supplied_pairs) != len(expected_pairs) or set(supplied_pairs) != expected_pairs:
        raise LegalMathError('E_REFERENCE', details='Scoped pair denominator does not cover actual candidates and claims')
    scoped_path = (root/dossier['component_refs']['scoped']['path']).parent/'model'/'journal.json'
    scoped_journal = original(scoped_path)
    if scoped_journal['sha256'] != journal_identity(scoped_journal['value']): raise LegalMathError('E_INTEGRITY')
    actual_scoped = scoped_journal['value']['binding']['inputs']
    if actual_scoped.get('input_profile','literal')!=expected_input:
        raise LegalMathError('E_STALE_REVIEW',details='Actual scoped input codec differs')
    if (canonical(actual_scoped['route']) != canonical(bound['provider']['route'] or runner.provider.provider_id) or
            canonical(actual_scoped['settings']) != canonical(bound['scoped_provider_settings']) or
            actual_scoped.get('source_reference_protocol', 'literal') != bound['transports']['scoped'] or
            set(map(tuple, actual_scoped['pairs'])) != expected_pairs):
        raise LegalMathError('E_STALE_REVIEW', details='Actual scoped stage does not match the frozen method')
    assignments = {q['candidate_id']: q for q in dossier['questions']['assignments']}
    if len(assignments) != len(dossier['questions']['assignments']) or set(assignments) != set(readings):
        raise LegalMathError('E_REFERENCE')
    rows = []
    for record in dossier['qualifications']:
        cid = record['candidate_id']; question = assignments[cid]
        directory = (root/record['directory']).resolve()
        if not directory.is_relative_to(root): raise LegalMathError('E_REFERENCE')
        result = verify_qualification(directory, packet, readings[cid], question['question'], runner.jdk,
            assignment_status=question['assignment_status'], compiler=runner.catala['compiler'] if runner.catala else None)
        if canonical(record['report']) != canonical(result): raise LegalMathError('E_INTEGRITY')
        rows.append({'candidate_id': cid, 'qualification_hash': digest(result), 'summary': result['summary']})
    extra_stages={};panel_summary=None
    if bound.get('challenge_panel') is not None:
        if binding.get('challenge_panel')!=bound['challenge_panel']:raise LegalMathError('E_STALE_REVIEW')
        from . import challenge_panel
        path=(root/dossier['component_refs']['challenges']['path']).parent
        panel_summary=challenge_panel.verify(path,packet,readings,
            {cid:r['question'] for cid,r in assignments.items()},expected_configuration=bound['challenge_panel'])
        envelope=original(path/'actions/journal.json')
        if envelope['sha256']!=journal_identity(envelope['value']):raise LegalMathError('E_INTEGRITY')
        extra_stages['challenges']=envelope['value']['started_ms']
    return {'profile': PROFILE, 'investigation_revision': dossier['revision'],
        'method_hash': digest(bound), 'source_hash': source_identity(binding['sources']),
        'source_bundle_hash': digest(binding['sources']),
        'question_hash': digest(binding['question']), 'packet_hash': digest(packet),
        'authority_resolution_hash': digest(authority), 'context_hash': digest(context),
        'criticism_hash': digest(criticism), 'candidate_count': len(readings), 'qualifications': rows,
        'challenge_summary_hash':digest(panel_summary) if panel_summary is not None else None,
        'execution_complete': dossier['execution_complete'],
        'pending_scoped_pairs': dossier['scoped']['pending_pairs'],
        'residual_questions': dossier['core']['residual_questions'],
        'legal_correctness': 'NOT_ESTABLISHED', 'unknown_future_legal_generalization': 'NOT_ESTABLISHED',
        'human_quality_evidence': False, 'remote_execution_attested': False,
        'remote_model_revision': 'NOT_ATTESTED',
        'external_dependency_state': 'LOCK_RECORDS_BOUND; INSTALLED_PACKAGE_CONTENTS_NOT_ATTESTED',
        'stage_started_ms': {
            'source_interpretation': journal['value']['started_ms'],
            'core_model': model_journal['value']['started_ms'],
            'scoped': scoped_journal['value']['started_ms'],**extra_stages}}


def observe(directory, window_hash, task_id, dossier_ref, runner):
    bound = frozen_method(directory, window_hash)
    with ledger.locked(directory):
        spec, events = ledger.load(directory, window_hash)
        selected = [e for e in events if e['kind'] == 'SELECT' and e['item']['task_id'] == task_id]
        if len(selected) != 1 or any(e['kind'] == 'OBSERVE' and e['task_id'] == task_id for e in events):
            raise LegalMathError('E_REFERENCE')
        if selected[0]['status'] != 'PENDING' or any(e['kind'] == 'REPAIR' for e in events):
            raise LegalMathError('E_STALE_REVIEW', details='Repaired/ineligible window cannot receive confirmation evidence')
        dossier = read_evidence(dossier_ref, runner.root)
        item = selected[0]['item']
        if (source_identity(dossier['binding']['sources']) != item['source_hash'] or
                digest(dossier['binding']['question']) != item['question_hash']):
            raise LegalMathError('E_STALE_REVIEW', details='Different source edition or selected question')
        result = check_stages(runner.root, dossier, bound, runner)
        selected_ms = int(ledger.instant(selected[0]['at']).timestamp()*1000)
        observed_ms = int(ledger.instant(ledger.now()).timestamp()*1000)
        if any(type(at) is not int or not selected_ms <= at <= observed_ms
               for at in result['stage_started_ms'].values()):
            raise LegalMathError('E_STALE_REVIEW', details='Investigation stage predates admission or lies in the future')
        return ledger.append(directory, spec, events, {'kind': 'OBSERVE', 'task_id': task_id,
            'investigation': deepcopy(dossier_ref), 'investigation_revision': dossier['revision'],
            'summary': result, 'qualification_hash': digest(result),
            'legal_generalization': 'NOT_ESTABLISHED'})


def report(directory, window_hash, *, expected_head=None):
    bound = frozen_method(directory, window_hash)
    result = ledger.report(directory, window_hash, expected_head=expected_head)
    _, events = ledger.load(directory, window_hash)
    observed = [e for e in events if e['kind'] == 'OBSERVE']
    by_task = {e['task_id']: e for e in observed}
    for row in result['tasks']:
        if row['task_id'] in by_task and not by_task[row['task_id']]['summary']['execution_complete']:
            row['status'] = 'OBSERVED_INCOMPLETE'
    return {**result, 'scope': PROFILE, 'component_only_window': False,
        'distinct_primary_sources_submitted': len({r['source_hash'] for r in result['tasks']}),
        'distinct_primary_sources_observed': len({e['summary']['source_hash'] for e in observed}),
        'observed_complete': sum(e['summary']['execution_complete'] for e in observed),
        'observed_incomplete': sum(not e['summary']['execution_complete'] for e in observed),
        'method': bound,
        'observation_qualification': 'Every retained investigation and candidate qualification is bound and rechecked; no model or human answer is a legal quality label.'}
