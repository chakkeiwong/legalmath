"""Reviewed finite retry migration, retaining every successful answer unchanged."""
from copy import deepcopy
from jsonschema import validate
from legalmath.canonical import digest
from ..bounded_context import require
from ..integration_contract import read_evidence
from . import capacity_policy
from .evidence_store import save_exact

PROFILE = 'repaired-review-checkpoint.v1'
FIELDS = {'context_reference_profile': ('AUDIT_EXPLICIT_DEPENDENCY_CONTEXT', 'exact-context-answer-and-needs.v1'),
    'warrant_reference_profile': ('ASSESS_REVIEW_WARRANT', 'exact-warrant-answer-fields.v1'),
    'correction_input_profile': ('CORRECT_REVIEWED_ANSWER', 'exact-correction-gap-occurrences.v1')}
RETRY_TASKS = {'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT','ASSESS_REVIEW_WARRANT',
    'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS','AUDIT_ANSWER_AND_DETAILED_ACCOUNT'}

def normalized(request):
    result = deepcopy(capacity_policy.annotate(request))
    for field, (task, profile) in FIELDS.items():
        if field in result:
            require(result['task'] == task and result[field] == profile,
                'Unknown retry transport profile', 'E_AUTHORITY')
            result.pop(field)
    return result

def equivalent(previous, current, checkpoint, row, root=None):
    if capacity_policy.annotate(previous) == capacity_policy.annotate(current):
        return True
    if checkpoint.get('retry_profile') != PROFILE or row['mode'] not in ('VALIDATED','REVIEWED_FAILURE_RETRY'):
        return False
    left,right=normalized(previous),normalized(current)
    # An identical local diagnostic may move with the fresh runtime. Verify both
    # files before restoring its old pointer; no substantive prompt field changes.
    a=left.get('payload',{}).get('invalid_review_repair',{}).get('full_diagnostic') if isinstance(left.get('payload'),dict) else None
    b=right.get('payload',{}).get('invalid_review_repair',{}).get('full_diagnostic') if isinstance(right.get('payload'),dict) else None
    if a and b and a != b and root is not None and a['sha256']==b['sha256']:
        read_evidence(a,root,json_value=False);read_evidence(b,root,json_value=False)
        right['payload']['invalid_review_repair']['full_diagnostic']=a
    return left==right

def retryable(checkpoint, row, request, prior, root):
    require(checkpoint.get('retry_profile') == PROFILE and prior['status'] == 'FAILED'
        and not prior.get('continuation_veto') and request['task'] in RETRY_TASKS
        and row['result'] in checkpoint['reviewed_failed_results'],
        'Unreviewed failure retry or successful answer resampling', 'E_AUTHORITY')
    read_evidence(checkpoint['retry_review'], root, json_value=False)

def retained_raw(product,key,result,request,schema):
    if product.capacity_checkpoint is None:
        return None
    checkpoint=read_evidence(product.capacity_checkpoint,product.root)
    row=checkpoint.get('calls',{}).get(key,{})
    if checkpoint.get('retry_profile')!=PROFILE or not row.get('raw'):
        return None
    previous=read_evidence(row['request'],product.root)
    require(previous==request and read_evidence(row['schema'],product.root)==schema
        and read_evidence(row['result'],product.root)==result
        and row['mode']=='RETAINED_FAILURE', 'Changed retained malformed group', 'E_INTEGRITY')
    journal=read_evidence(row['dispatch'],product.root)
    require(journal['input_hash']==product.route.input_hash
        and journal['calls'][row.get('dispatch_key',key)]['result_hash']==digest(result),
        'Changed retained malformed dispatch', 'E_INTEGRITY')
    return deepcopy(read_evidence(row['raw'],product.root)['value'])

def fixed_correction(product, qid, question, original, details):
    if product.capacity_checkpoint is None:
        return None
    checkpoint = read_evidence(product.capacity_checkpoint, product.root)
    pointer = checkpoint.get('fixed_correction')
    if pointer is None:
        return None
    require(checkpoint.get('retry_profile') == PROFILE
        and checkpoint['input_hash'] == product.route.input_hash,
        'Foreign fixed correction checkpoint', 'E_INTEGRITY')
    fixed = read_evidence(pointer, product.root)
    require(fixed['profile'] == 'fixed-corrected-answer-continuation.v1'
        and fixed['question_id'] == qid and fixed['question'] == question,
        'Changed corrected answer question', 'E_INTEGRITY')
    report = read_evidence(fixed['answers'], product.root)[qid]
    correction = report['correction']
    require(correction['source_identity'] == product.route.input_hash
        and correction['original_answer']['value'] == original
        and correction['original_requirement_details'] == details,
        'Changed fixed-answer inputs', 'E_INTEGRITY')
    row = checkpoint['calls']['correction-'+qid]
    request, schema, result, journal = [read_evidence(row[k], product.root)
        for k in ('request','schema','result','dispatch')]
    recorded = journal['calls']['correction-'+qid]
    require(row['mode'] == 'VALIDATED' and result['status'] == recorded['status'] == 'VALIDATED'
        and recorded['result_hash'] == digest(result)
        and recorded['identity'] == product.dispatch.request_identity(request,schema)
        and request['task'] == 'CORRECT_REVIEWED_ANSWER'
        and request['question'] == question and request['payload']['original'] == original
        and request['input_hash'] == product.route.input_hash
        and report['answer']['value'] == correction['candidate']['value'] == result['value'],
        'Changed fixed corrected response', 'E_INTEGRITY')
    require(all(product.route.records.get(r['id']) == r for r in request['records']),
        'Changed fixed correction sources', 'E_INTEGRITY')
    validate(result['value'],schema)
    product.citations(result['value'],request['records'])
    value = deepcopy(correction)
    value['fixed_continuation'] = pointer
    return value

def resume_correction(product, qid, question, answer, details, dependencies):
    held = fixed_correction(product,qid,question,answer['value'],details)
    if held is None:
        return None
    valid = [r for r in held['original_reviews'] if r.get('status') == 'VALIDATED']
    candidate = deepcopy(held['candidate'])
    from . import current_issue_disposition
    checkpoint = getattr(product,'capacity_checkpoint',None)
    outer = read_evidence(checkpoint,product.root) if checkpoint is not None else {}
    if outer.get('current_answer_issue_dispositions',{}).get(qid) is not None:
        # The fixed correction already authenticates these original assessments.
        # A complete disposition binds original issue identities, not a new
        # model's reassessment; validate it before spending any duplicate call.
        assessments = held.get('review_warrants',[])
        disposition = current_issue_disposition.apply(product,qid,question,answer['value'],
            candidate['value'],held['corrected_requirement_details'],valid,assessments)
        require(disposition is not None,'Registered current-answer disposition was not applied','E_INTEGRITY')
        held['historical_warrant_reuse']='AUTHENTICATED_FIXED_CORRECTION'
    else:
        assessments, _, _ = product.review_warrants(qid,question,answer,valid,details)
        disposition = None
    reviews = product.audit_answer(qid,question,candidate['value'],held['corrected_requirement_details'],prefix='corrected-')
    reviews += product.audit_dependencies(qid,question,candidate['value'],dependencies,prefix='corrected-')
    unresolved = [r for r in assessments if r['result']['status'] != 'VALIDATED'
        or any(d['disposition']=='UNRESOLVED' for d in r['result']['value']['decisions'])]
    if disposition is not None:
        held['current_answer_issue_disposition']=disposition
        unresolved=disposition['pending']
    if unresolved:
        reviews.append(dict(status='FAILED',error='E_DEPENDENCY',
            reason='Fixed corrected answer retained; original issue warrants remain unresolved',assessments=unresolved))
    held.update(status='REVIEWED_FIXED_CANDIDATE', review_warrants=assessments, candidate_reviews=reviews,
        new_answer_calls=0, legal_acceptance=False)
    save_exact(product.directory/('fixed-correction-'+qid+'.json'),held)
    return candidate,reviews,held
