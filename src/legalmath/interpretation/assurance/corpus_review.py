"""Consume explicitly reviewed corpus evidence; never infer legal truth from fidelity."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from legalmath.canonical import digest
from .bounded_context import require

PROFILE = 'scoped-corpus-review-evidence.v1'
QUESTIONS = {'p10', 'p14', 'evidence', 'gatecoin'}
CONTROLS = {'positive': 'VALIDATED', 'wrong_source': 'REJECTED', 'false_attribution': 'REJECTED'}

def checked_file(root, reference):
    require(isinstance(reference,dict) and set(reference) == {'path','sha256'},
        'Malformed corpus evidence reference', 'E_INTEGRITY')
    path = Path(reference['path'])
    require(not path.is_absolute() and '..' not in path.parts, 'Foreign corpus evidence path', 'E_INTEGRITY')
    target = (Path(root) / path).resolve()
    require(target.is_relative_to(Path(root).resolve()), 'Corpus evidence escapes root', 'E_INTEGRITY')
    data = target.read_bytes()
    require(sha256(data).hexdigest() == reference['sha256'], 'Changed corpus evidence: '+str(path), 'E_INTEGRITY')
    return data

def read(root, reference):
    return json.loads(checked_file(root, reference))

def expected_context(root, expected):
    require(expected.get('profile') == PROFILE and isinstance(expected.get('scope'),str)
        and expected['scope'].strip(), 'Missing corpus review scope', 'E_INTEGRITY')
    when = datetime.fromisoformat(expected['as_of'].replace('Z','+00:00'))
    require(when.tzinfo is not None, 'Corpus as-of time needs timezone', 'E_INTEGRITY')
    require(set(expected['answers']) == QUESTIONS and set(expected['required_propositions']) == QUESTIONS,
        'Incomplete original-question corpus coverage', 'E_INTEGRITY')
    for ids in expected['required_propositions'].values():
        require(isinstance(ids,list) and ids and all(isinstance(i,str) and i for i in ids)
            and len(ids) == len(set(ids)), 'Missing or duplicate proposition duties', 'E_INTEGRITY')
    require(expected['sources'], 'Empty corpus source population', 'E_INTEGRITY')
    for reference in [*expected['sources'].values(), *expected['answers'].values()]:
        checked_file(root, reference)
    fidelity = read(root, expected['fidelity'])
    require(fidelity.get('fidelity_reconciled') is True, 'Corpus fidelity remains unqualified', 'E_INTEGRITY')
    require(isinstance(fidelity.get('evidence'),list) and fidelity['evidence'],
        'Missing fidelity evidence', 'E_INTEGRITY')
    for reference in fidelity['evidence']:
        checked_file(root, reference)
    return digest(expected)

def ownership_text(root, row, fidelity):
    reference = row['passage']
    require(reference in fidelity['evidence'],
        'Unregistered corpus passage ownership receipt', 'E_INTEGRITY')
    ownership = read(root, reference)
    require(ownership.get('source') == row['source'],
        'Corpus passage belongs to another source', 'E_INTEGRITY')
    pointer = row.get('passage_pointer')
    require(isinstance(pointer, str) and pointer.startswith('/'),
        'Missing exact corpus passage pointer', 'E_INTEGRITY')
    parts = pointer.split('/')[1:]
    require(len(parts) == 3 and parts[1].isdigit() and str(int(parts[1])) == parts[1]
        and parts[2] == 'text', 'Unsupported corpus passage pointer', 'E_INTEGRITY')
    name, position, _ = parts
    collection = ownership.get(name)
    require(isinstance(collection, list) and int(position) < len(collection),
        'Corpus passage pointer outside receipt', 'E_INTEGRITY')
    item = collection[int(position)]
    profile = ownership.get('profile')
    if profile == 'judgment-rendered-fidelity.v2':
        require(ownership.get('full_document_qualified') is True
            and ownership.get('unresolved') == [] and ownership.get('remaining') == [],
            'Unqualified judgment ownership', 'E_INTEGRITY')
        require(name in ('main_paragraphs', 'full_components', 'full_footnotes'),
            'Unqualified judgment passage collection', 'E_INTEGRITY')
        if name == 'main_paragraphs':
            require(item.get('rendered_label_verified') is True
                and item.get('locator') == row['locator'],
                'Wrong judgment paragraph locator', 'E_INTEGRITY')
        elif name == 'full_components':
            require(item.get('full_text_and_label_verified') is True
                and item.get('owner') == row['locator'] and item.get('region') == 'reasons',
                'Wrong judgment component owner', 'E_INTEGRITY')
        else:
            require(item.get('full_text_and_label_verified') is True
                and row['locator'] == 'FN' + item['display'],
                'Wrong judgment footnote locator', 'E_INTEGRITY')
    elif profile == 'handbook-passage-fidelity.v2':
        require(name == 'clauses' and ownership.get('source_passages_qualified') is True
            and ownership.get('cross_page_delivery_gaps') == []
            and item.get('fully_delivered_pages') is True
            and row['locator'] == item['section'] + ':' + item['label'],
            'Wrong or unqualified Handbook clause', 'E_INTEGRITY')
    else:
        require(False, 'Unsupported corpus passage ownership profile', 'E_INTEGRITY')
    require(isinstance(item.get('text'), str), 'Missing owned passage text', 'E_INTEGRITY')
    return item['text']

def support(root, rows, sources, allowed, fidelity):
    require(isinstance(rows,list) and rows, 'Missing checked primary-source passages', 'E_INTEGRITY')
    for row in rows:
        sid = row['source_id']
        require(sid in allowed and row['source'] == sources[sid], 'Wrong source in corpus support', 'E_INTEGRITY')
        source_bytes = checked_file(root,row['source'])
        if row['passage'] == row['source']:
            require('passage_pointer' not in row,
                'Direct-source passage cannot use an extraction pointer', 'E_INTEGRITY')
            passage = source_bytes.decode('utf-8')
        else:
            passage = ownership_text(root, row, fidelity)
        require(isinstance(row['quote'],str) and row['quote'].strip() and row['quote'] in passage,
            'Corpus quotation absent from retained passage', 'E_INTEGRITY')
        require(isinstance(row.get('locator'),str) and row['locator'].strip(),
            'Missing corpus passage locator', 'E_INTEGRITY')

def answer_support(answer, rows):
    """Check attribution to an exact answer field; never infer entailment."""
    require(isinstance(rows,list) and rows, 'Missing exact answer passages', 'E_INTEGRITY')
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'path','quote'}
            and isinstance(row['path'],str) and row['path'].startswith('/')
            and isinstance(row['quote'],str) and row['quote'].strip(),
            'Malformed answer passage', 'E_INTEGRITY')
        value=answer
        for token in row['path'][1:].split('/'):
            import re
            require(re.search(r'~(?![01])',token) is None,
                'Invalid answer pointer escape','E_INTEGRITY')
            token=token.replace('~1','/').replace('~0','~')
            if isinstance(value,list):
                require(token.isascii() and token.isdecimal()
                    and str(int(token))==token and int(token)<len(value),
                    'Answer passage index outside answer','E_INTEGRITY')
                value=value[int(token)]
            else:
                require(isinstance(value,dict) and token in value,
                    'Answer passage pointer outside answer','E_INTEGRITY')
                value=value[token]
        require(isinstance(value,str) and row['quote'] in value,
            'Answer quotation absent from selected answer field','E_INTEGRITY')

def evaluate(root, expected, bundle_reference=None):
    identity = expected_context(root, expected)
    fidelity = read(root, expected['fidelity'])
    remaining = []
    if bundle_reference is None:
        return {'profile':PROFILE, 'context_hash':identity, 'status':'BLOCKED',
            'corpus_acceptance_complete':False, 'legal_correctness_established':False,
            'remaining':['Reviewed applicability and later treatment: '+s for s in expected['sources']] +
                ['Reviewed proposition/source use: '+q for q in sorted(QUESTIONS)] +
                ['Positive, wrong-source and false-attribution controls for this context']}
    bundle = read(root,bundle_reference)
    require(bundle.get('profile') == PROFILE and bundle.get('context_hash') == identity,
        'Stale or foreign corpus review bundle', 'E_INTEGRITY')
    require(bundle.get('as_of') == expected['as_of'] and bundle.get('scope') == expected['scope'],
        'Corpus legal date or scope mismatch', 'E_INTEGRITY')
    require(isinstance(bundle.get('reviewer'),str) and bundle['reviewer'].strip(),
        'Missing explicit corpus reviewer', 'E_INTEGRITY')
    require(bool(checked_file(root,bundle['review_note']).strip()),
        'Empty corpus review note', 'E_INTEGRITY')
    applicability = bundle['applicability']
    ids = [r['source_id'] for r in applicability]
    require(len(ids) == len(set(ids)) and set(ids) == set(expected['sources']),
        'Missing or duplicate source applicability duties', 'E_INTEGRITY')
    for row in applicability:
        sid = row['source_id']
        require(row['source'] == expected['sources'][sid] and row['scope'] == expected['scope']
            and row['as_of'] == expected['as_of'] and row.get('version'),
            'Applicability identity, date or scope mismatch', 'E_INTEGRITY')
        for duty in ('applicability','later_treatment'):
            finding = row[duty]
            require(finding.get('status') in ('QUALIFIED','UNRESOLVED','REJECTED')
                and isinstance(finding.get('finding'),str) and finding['finding'].strip(),
                'Missing substantive applicability finding', 'E_INTEGRITY')
            if finding['status'] != 'QUALIFIED':
                remaining.append(sid+': '+duty+' '+finding['status'])
            else:
                support(root,finding['primary_evidence'],expected['sources'],set(expected['sources']),fidelity)
    answers = bundle['answer_use']
    ids = [r['question'] for r in answers]
    require(len(ids) == len(set(ids)) and set(ids) == QUESTIONS,
        'Missing or duplicate answer-use duties', 'E_INTEGRITY')
    for row in answers:
        q = row['question']
        require(row['answer'] == expected['answers'][q], 'Stale answer-use review', 'E_INTEGRITY')
        answer=read(root,row['answer'])
        props = row['propositions']
        ids = [p['id'] for p in props]
        require(len(ids) == len(set(ids)) and set(ids) == set(expected['required_propositions'][q]),
            'Incomplete proposition population', 'E_INTEGRITY')
        for p in props:
            require(p.get('status') in ('SUPPORTED','UNRESOLVED','REJECTED') and p.get('reason')
                and isinstance(p.get('source_ids'),list) and p['source_ids']
                and set(p['source_ids']) <= set(expected['sources']),
                'Missing proposition support or decision', 'E_INTEGRITY')
            if p['status'] != 'SUPPORTED':
                remaining.append(q+': '+p['id']+' '+p['status'])
            else:
                support(root,p['primary_evidence'],expected['sources'],set(p['source_ids']),fidelity)
                answer_support(answer,p.get('answer_evidence'))
    require(set(bundle['controls']) == set(CONTROLS), 'Missing corpus adverse controls', 'E_INTEGRITY')
    for name, outcome in CONTROLS.items():
        control = read(root,bundle['controls'][name])
        require(control.get('context_hash') == identity and control.get('control') == name
            and control.get('expected') == outcome and control.get('observed') == outcome,
            'Failed or wrong-context corpus control: '+name, 'E_INTEGRITY')
        require(bool(checked_file(root,control['execution_evidence']).strip()),
            'Empty control execution evidence', 'E_INTEGRITY')
    return {'profile':PROFILE, 'context_hash':identity, 'status':'BLOCKED' if remaining else 'SUCCEEDED',
        'corpus_acceptance_complete':not remaining, 'legal_correctness_established':False,
        'review_bundle':bundle_reference, 'remaining':remaining,
        'scope':'Recorded explicit scoped reviews; no automated proof of legal truth.'}
