"""Executable conditional guards for the twenty retained repair candidates."""
from copy import deepcopy
from datetime import date
from itertools import product
from pathlib import Path
import os
import sys
import time

import assurance_evidence_core as c
from legalmath.canonical import digest
from legalmath.interpretation.assurance import conditional_elimination as logic

PLAN = Path('docs/plans/assurance-evidence-guarded-continuation.md')
PARTIAL_FALSE = ('exception-challenger', 'deferred.744c4b5d99bc07afffce029b')
OUTCOME_IDS = {'deferred.744c4b5d99bc07afffce029b', 'deferred.8e90af0c22246aec5c2d05d0'}
OWNERSHIP_FIELDS = ('legal_interests', 'beneficial_interests', 'register_authority',
                    'settlement_finality', 'reconciliation')
CONTEXT_FIELDS = ('provider', 'product', 'arrangement', 'ownership_scope', 'start', 'end')


def atoms(tree):
    if isinstance(tree, str):
        return [] if tree in ('true', 'false') else [tree]
    return list(dict.fromkeys(x for child in tree[1:] for x in atoms(child)))


def evaluate(formal, case, *, role, reading_id, evidence, check_reference):
    """Aggregate supplied judgments; neither this guard nor a receipt proves them."""
    if formal['result_type'] != 'bool' or any(f['type'] != 'bool' for f in formal['facts']):
        c.fail('E_UNSUPPORTED_PROFILE', 'Guard requires the retained Boolean profile')
    names = logic.names_checked([f['name'] for f in formal['facts']])
    scope, body = (logic.parse_boolean(formal[k], names) for k in ('scope', 'result'))
    if not isinstance(body, list) or body[0] != 'and' or any(not isinstance(a, str) or a not in names for a in body[1:]):
        c.fail('E_UNSUPPORTED_PROFILE', 'Reviewed guard supports a conjunction of named judgments')
    context = case.get('context', {})
    answer = {'status': 'UNRESOLVED', 'value': None, 'predicate_label': ('Proposed retained-responsibility and achieved-adequacy predicate'
            if reading_id in OUTCOME_IDS else 'Proposed retained-accountability predicate'),
        'modality': 'SHOULD', 'program_hash': digest(formal), 'case_hash': digest(case),
        'evaluated': False, 'reasons': [], 'auxiliary': deepcopy(case.get('auxiliary', {})),
        'legal_correctness': 'NOT_ESTABLISHED', 'release_eligible': False}
    def stop(reason, status='UNRESOLVED'):
        return {**answer, 'status': status, 'reasons': [reason]}
    if (not isinstance(context, dict) or set(context) != set(CONTEXT_FIELDS)
            or any(not isinstance(context[k], str) or not context[k].strip() for k in CONTEXT_FIELDS)):
        return stop('MISSING_COMMON_PROVIDER_PRODUCT_ARRANGEMENT_OWNERSHIP_PERIOD')
    try:
        if date.fromisoformat(context['end']) < date.fromisoformat(context['start']):
            return stop('INVALID_ASSESSMENT_PERIOD')
    except ValueError:
        return stop('INVALID_ASSESSMENT_PERIOD')
    common = digest(context)
    facts = case.get('facts', {})
    if not isinstance(facts, dict) or not set(facts) <= set(names):
        c.fail('E_SCHEMA', 'Unexpected fact in guarded case')

    def judgment(row, *, ownership=False):
        if row is None:
            return None, 'MISSING_CLASSIFICATION'
        if not isinstance(row, dict) or row.get('status') not in ('known', 'unknown', 'conflict'):
            c.fail('E_SCHEMA', 'Invalid judgment state')
        if row['status'] != 'known':
            if 'value' in row:
                c.fail('E_SCHEMA', 'Unknown or conflicting evidence cannot carry a Boolean classification')
            return None, 'CONFLICTING_CLASSIFICATION' if row['status'] == 'conflict' else 'UNKNOWN_CLASSIFICATION'
        if type(row.get('value')) is not bool or type(row.get('depends_on_ownership')) is not bool:
            c.fail('E_SCHEMA', 'Known judgment requires an explicit Boolean and dependency declaration')
        if (row.get('context_hash') != common or not isinstance(row.get('basis'), str) or not row['basis'].strip()
                or not isinstance(row.get('assessed_by'), str) or not row['assessed_by'].strip()
                or not isinstance(row.get('evidence_ids'), list) or not row['evidence_ids']):
            return None, 'MISSING_OR_MISMATCHED_JUDGMENT_PROVENANCE'
        for key in row['evidence_ids']:
            if not isinstance(key, str) or key not in evidence:
                return None, 'MISSING_JUDGMENT_EVIDENCE'
            check_reference(evidence[key])
        if ownership and row['depends_on_ownership']:
            inventory = case.get('ownership_inventory', {})
            if not isinstance(inventory, dict):
                c.fail('E_SCHEMA', 'Ownership inventory must be an object')
            for field in OWNERSHIP_FIELDS:
                value, reason = judgment(inventory.get(field))
                if value is not True:
                    return None, 'OWNERSHIP_INVENTORY_'+field.upper()+':'+(reason or 'NOT_RESOLVED')
        return row['value'], None

    applicable, reason = judgment(case.get('applicability'), ownership=True)
    if applicable is None:
        return stop('APPLICABILITY:'+reason)
    if not applicable:
        return stop('SUPPLIED_APPLICABILITY_IS_FALSE', 'OUT_OF_SCOPE')
    values, blockers = {}, {}
    for name in atoms(scope):
        value, reason = judgment(facts.get(name), ownership=True)
        if value is None:
            blockers[name] = reason
        else:
            values[name] = value
    if blockers:
        return stop('SCOPE_UNRESOLVED:'+str(blockers))
    if not logic.evaluate(scope, values):
        return stop('SUPPLIED_SCOPE_IS_FALSE', 'OUT_OF_SCOPE')
    expected_interpretation = 'OUTCOME_READING_HYPOTHESIS' if reading_id in OUTCOME_IDS else 'RETENTION_READING_HYPOTHESIS'
    if case.get('interpretation') != expected_interpretation:
        return stop('EXPLICIT_SELECTED_INTERPRETATION_REQUIRED')
    for name in atoms(body):
        value, reason = judgment(facts.get(name), ownership=True)
        if value is None:
            blockers[name] = reason
        else:
            values[name] = value
    partial = (role, reading_id) == PARTIAL_FALSE
    evidenced_false = [name for name in atoms(body) if values.get(name) is False]
    if blockers and not (partial and evidenced_false):
        return stop('REQUIRED_CLASSIFICATIONS_UNRESOLVED:'+str(blockers))
    value = False if blockers else logic.evaluate(body, values)
    return {**answer, 'status': 'CONDITIONAL_PREDICATE_TRUE' if value else 'CONDITIONAL_PREDICATE_FALSE',
        'value': value, 'evaluated': True, 'reasons': ['EVIDENCED_FALSE_CONJUNCT'] if blockers else [],
        'unresolved_classifications': blockers,
        'limitation': 'Receipts and supplied judgments do not establish the legal standard, case truth or overall compliance.'}


def synthetic_case(formal, reading_id, evidence_id='synthetic.case-basis'):
    context = {'provider': 'SYNTHETIC_PROVIDER', 'product': 'SYNTHETIC_PRODUCT',
        'arrangement': 'SYNTHETIC_ARRANGEMENT', 'ownership_scope': 'SYNTHETIC_COMPLETE_INVENTORY',
        'start': '2026-01-01', 'end': '2026-01-31'}
    def supplied():
        return {'status': 'known', 'value': True, 'context_hash': digest(context),
            'basis': 'Synthetic independently supplied classification for a software diagnostic only.',
            'assessed_by': 'SYNTHETIC_REVIEWER', 'evidence_ids': [evidence_id], 'depends_on_ownership': False}
    facts = {f['name']: supplied() for f in formal['facts']}
    for name in facts:
        if 'record' in name:
            facts[name]['depends_on_ownership'] = True
    return {'context': context, 'applicability': supplied(), 'facts': facts,
        'interpretation': 'OUTCOME_READING_HYPOTHESIS' if reading_id in OUTCOME_IDS else 'RETENTION_READING_HYPOTHESIS',
        'ownership_inventory': {k: supplied() for k in OWNERSHIP_FIELDS},
        'auxiliary': {'sfc_request': 'unknown', 'approval': 'unknown', 'consultation': 'unknown',
            'supervision': 'unknown', 'record_performance': 'unknown', 'remediation': 'unknown',
            'confirmation': 'unknown', 'demonstration': 'unknown', 'audit': 'unknown', 'legal_opinion': 'unknown'},
        'hypothetical_only': True}


def program_checks(formal, *, role, reading_id, evidence, check_reference):
    base = synthetic_case(formal, reading_id)
    names = [f['name'] for f in formal['facts']]
    scope, body = (logic.parse_boolean(formal[k], names) for k in ('scope', 'result'))
    probes = []
    def check(label, case, expected):
        result = evaluate(formal, case, role=role, reading_id=reading_id, evidence=evidence, check_reference=check_reference)
        if (result['status'], result['value']) != expected:
            c.fail('E_INTEGRITY', 'Guard contrary case failed: '+label+' '+str(result))
        probes.append({'case_id': label, 'case': case, 'expected': list(expected), 'result': result})
    for index, bits in enumerate(product((False, True), repeat=len(names))):
        case = deepcopy(base)
        values = dict(zip(names, bits))
        for name, value in values.items():
            case['facts'][name]['value'] = value
        expected = ('OUT_OF_SCOPE', None) if not logic.evaluate(scope, values) else (
            'CONDITIONAL_PREDICATE_TRUE' if logic.evaluate(body, values) else 'CONDITIONAL_PREDICATE_FALSE', logic.evaluate(body, values))
        check('total-valuation-'+str(index), case, expected)
    for name in names:
        for state in ('unknown', 'conflict'):
            case = deepcopy(base)
            case['facts'][name] = {'status': state}
            check(name+'-'+state, case, ('UNRESOLVED', None))
        case = deepcopy(base)
        case['facts'][name]['basis'] = ''
        check(name+'-no-basis', case, ('UNRESOLVED', None))
        case = deepcopy(base)
        case['facts'][name]['context_hash'] = '0'*64
        check(name+'-foreign-context', case, ('UNRESOLVED', None))
    for field in OWNERSHIP_FIELDS:
        case = deepcopy(base)
        case['ownership_inventory'][field] = {'status': 'conflict'}
        check('ownership-'+field, case, ('UNRESOLVED', None))
    for state in ('missing', 'unknown', 'conflict', 'false'):
        case = deepcopy(base)
        case['applicability']['depends_on_ownership'] = True
        if state == 'missing':
            case['ownership_inventory'] = {}
        elif state == 'false':
            case['ownership_inventory']['reconciliation']['value'] = False
        else:
            case['ownership_inventory']['reconciliation'] = {'status': state}
        check('applicability-ownership-'+state, case, ('UNRESOLVED', None))
    for label, modify in (
        ('missing-period', lambda v: v['context'].update(start='')),
        ('unknown-applicability', lambda v: v.update(applicability={'status': 'unknown'})),
        ('missing-interpretation', lambda v: v.update(interpretation=None))):
        case = deepcopy(base); modify(case)
        check(label, case, ('UNRESOLVED', None))
    for label, facts in (
        ('no-sfc-request', {'sfc_request': False}),
        ('defective-records-with-remediation', {'record_performance': False, 'supervision': True, 'remediation': True}),
        ('approval-is-separate', {'approval': True, 'consultation': False})):
        case = deepcopy(base); case['auxiliary'].update(facts)
        expected = ('CONDITIONAL_PREDICATE_TRUE', True)
        if label == 'defective-records-with-remediation' and reading_id in OUTCOME_IDS:
            # Supply a separate, explicit negative adequacy classification for
            # this outcome variant; the auxiliary event does not classify it.
            record_name = next(name for name in names if name in ('ownership_records_proper', 'records_adequate'))
            case['facts'][record_name]['value'] = False
            expected = ('CONDITIONAL_PREDICATE_FALSE', False)
        check(label, case, expected)
    retained = next(name for name in atoms(body) if 'retained' in name)
    case = deepcopy(base); case['facts'][retained]['value'] = False
    case['auxiliary']['record_performance'] = True
    check('adequate-outcome-without-retention', case, ('CONDITIONAL_PREDICATE_FALSE', False))
    case = deepcopy(base); case['facts'][retained]['value'] = False
    unknown = next(name for name in atoms(body) if name != retained and name not in atoms(scope))
    case['facts'][unknown] = {'status': 'unknown'}
    check('false-with-other-unknown', case, ('CONDITIONAL_PREDICATE_FALSE', False)
          if (role, reading_id) == PARTIAL_FALSE else ('UNRESOLVED', None))
    return probes


def verify(root, ref):
    path = c.checked(ref, root)
    base = (root/c.BASE/'additional-100-repair-20'/'guarded-program-repair').resolve()
    if path.name != 'completion-receipt.json' or not path.parent.is_relative_to(base):
        c.fail('E_INTEGRITY', 'Foreign guarded repair receipt')
    record = c.read(path)
    covered = set()
    for item in record['files']:
        output = c.checked(item, root)
        if output.parent != path.parent or output.name in covered:
            c.fail('E_INTEGRITY', 'Foreign or duplicated guarded output')
        covered.add(output.name)
    for item in record['inputs']:
        c.checked(item, root)
    if not {'result.json', 'programs.json', 'cases.json', 'synthetic-basis.json', 'run-manifest.json'} <= covered:
        c.fail('E_INTEGRITY', 'Guarded completion receipt is incomplete')
    return c.read(path.parent/'result.json')


def summary(root, ex):
    pointer = root/ex.RUN/'current-guarded-repair.json'
    if not pointer.exists():
        return None
    ref = c.read(pointer)['receipt']
    return {**verify(root, ref), 'receipt': ref}


def execute(root, ex):
    from assurance_evidence_completion import adopted_diagnostic
    from legalmath.interpretation.search.providers import CodexProvider
    began = time.monotonic()
    manifest = ex.verify(root)
    if Path(__file__).resolve().parents[1] != (root/manifest['frozen_root']).resolve():
        c.fail('E_AUTHORITY', 'Guard checks must run from the reviewed frozen code')
    diagnostic = adopted_diagnostic(root, ex)
    if diagnostic is None:
        c.fail('E_DEPENDENCY', 'Current diagnostic required')
    directory = c.checked(diagnostic['current'], root).parent
    refs = [c.receipt(directory/name, root) for name in ('program-inventory.json', 'formal-evidence.json')]
    refs += [c.receipt(root/c.OLD/'assessment-evidence.json', root), c.receipt(root/PLAN, root),
             c.read(root/ex.RUN/'active-revision.json')['receipt']]
    folder = root/ex.RUN/'guarded-program-repair'/digest(refs)[:24]
    receipt_path = folder/'completion-receipt.json'
    before = ex.Allowance(root).verify()
    reservations = ex.master.files_in(root/ex.RUN/'reservations', root)
    complete, reserve = CodexProvider.complete, ex.Allowance.reserve
    def forbidden(*args, **kwargs):
        c.fail('E_AUTHORITY', 'Local program repair cannot dispatch or reserve calls')
    CodexProvider.complete, ex.Allowance.reserve = forbidden, forbidden
    try:
        if not receipt_path.exists():
            inventory = c.read(directory/'program-inventory.json')
            current = {(r['role'], r['reading_id']): r['derived_reading'] for r in c.read(directory/'formal-evidence.json')}
            old = c.read(root/c.OLD/'assessment-evidence.json')
            ex.immutable(folder/'synthetic-basis.json', {'hypothetical_only': True,
                'purpose': 'Software contrary cases. No actual provider, assessment date or case fact is asserted.',
                'date_choice': 'January 2026 is a convenience fixture only; no applicability inference.'})
            evidence = {'synthetic.case-basis': c.receipt(folder/'synthetic-basis.json', root)}
            programs, cases = [], []
            for row in inventory:
                if not row['baseline_program_present'] or not row['required_program_repairs']:
                    continue
                role, cid = row['role'], row['reading_id']
                reading = current.get((role, cid))
                formal = reading['formalization'] if reading else old[role][cid]['formalization']
                probes = program_checks(formal, role=role, reading_id=cid, evidence=evidence,
                    check_reference=lambda ref: c.checked(ref, root))
                programs.append({'role': role, 'reading_id': cid, 'original_status': row['status'],
                    'formalization': formal, 'program_hash': digest(formal),
                    'requirements': row['required_program_repairs'], 'reading_or_prior_assessment': reading or old[role][cid],
                    'mechanical_status': 'GUARD_IMPLEMENTED_AND_CHECKED_CONDITIONALLY',
                    'partial_false_policy': (role, cid) == PARTIAL_FALSE,
                    'accepted_substantive_repair': False,
                    'remaining': ['Independent legal classification criteria, dated applicability and actual case evidence.',
                        'Source-specific interpretation and current-evidence review; original questions and requirements remain operative.']})
                cases.append({'role': role, 'reading_id': cid, 'checks': probes})
            if len(programs) != 20 or len({(r['role'], r['reading_id']) for r in programs}) != 20:
                c.fail('E_INTEGRITY', 'Guard repair must preserve all twenty program identities')
            ex.immutable(folder/'programs.json', programs)
            ex.immutable(folder/'cases.json', cases)
            result = {'status': 'MECHANICAL_CANDIDATES_CHECKED_PENDING_REVIEW', 'programs': len(programs),
                'synthetic_checks': sum(len(r['checks']) for r in cases), 'provider_calls': 0, 'repair_calls': 0,
                'formula_changes': 0, 'production_target_cases': 0, 'accepted_substantive_repairs': 0,
                'original_obligations_open': 46, 'legal_correctness': 'NOT_ESTABLISHED', 'release_eligible': False}
            ex.immutable(folder/'result.json', result)
            run_manifest = {'command': ex.PREFIX+['ops-run'], 'git_commit': manifest['git_commit'],
                'environment': str(root/'.venv'), 'cpu_only': True, 'gpu_hidden': os.environ.get('CUDA_VISIBLE_DEVICES') == '-1',
                'seeds': 'N/A: exhaustive finite valuations and deterministic contrary cases',
                'frozen_root': manifest['frozen_root'], 'inputs': refs, 'plan': str(PLAN),
                'result': str((folder/'result.json').relative_to(root)), 'wall_seconds': round(time.monotonic()-began, 3),
                'allowance_before': before, 'allowance_after': ex.Allowance(root).verify()}
            if (folder/'run-manifest.json').exists():
                run_manifest['wall_seconds'] = c.read(folder/'run-manifest.json')['wall_seconds']
            ex.immutable(folder/'run-manifest.json', run_manifest)
            ex.immutable(receipt_path, {'inputs': refs, 'files': ex.master.files_in(folder, root, ('completion-receipt.json',))})
        if ex.Allowance(root).verify() != before or ex.master.files_in(root/ex.RUN/'reservations', root) != reservations:
            c.fail('E_INTEGRITY', 'Guarded local repair changed spending')
        verify(root, c.receipt(receipt_path, root))
        c.save(root/ex.RUN/'current-guarded-repair.json', {'receipt': c.receipt(receipt_path, root)})
        return summary(root, ex)
    finally:
        CodexProvider.complete, ex.Allowance.reserve = complete, reserve
