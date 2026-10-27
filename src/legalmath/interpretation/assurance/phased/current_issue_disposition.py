"""Explicit reviewed disposition of old objections against an exact current answer.

Opt-in evidence only. No provider calls, answer regeneration or automatic waiver.
Fresh answer/account/dependency reviews remain separate acceptance requirements.
"""
from legalmath.canonical import digest
from ..bounded_context import require
from ..integration_contract import read_evidence
from .context_disposition import answer_quote

PROFILE='current-answer-issue-disposition.v1'
SETTLED={'CORRECTED_IN_CURRENT_ANSWER','NOT_APPLICABLE_TO_CURRENT_ANSWER',
    'CONDITIONALLY_ADDRESSED','SUPPORTED_BY_REVIEWED_SOURCE'}

def census(reviews, assessments):
    by_index={}
    for assessment in assessments:
        i=assessment['review_index']
        require(type(i) is int and 0<=i<len(reviews) and i not in by_index
            and assessment['original_review_hash']==digest(reviews[i]),
            'Changed original objection identity','E_INTEGRITY')
        by_index[i]=assessment
    expected={i for i,r in enumerate(reviews) if r.get('status')=='VALIDATED'
        and r['value']['verdict']=='REJECT'}
    require(set(by_index)==expected,'Missing original adverse review assessment','E_INTEGRITY')
    rows=[]
    for i in sorted(expected):
        review=reviews[i]; outcome=by_index[i]['result']
        issues=review['value']['issues']
        require(issues,'Adverse review has no issues','E_INTEGRITY')
        decisions={}
        if outcome['status']=='VALIDATED':
            values=outcome['value']['decisions']
            require(len(values)==len(issues) and {d['issue_id'] for d in values}
                =={'issue-'+str(j) for j in range(len(issues))},
                'Incomplete original issue assessment','E_INTEGRITY')
            decisions={d['issue_id']:d for d in values}
        for j,issue in enumerate(issues):
            rows.append(dict(id=str(i)+':issue-'+str(j),review_index=i,
                review_hash=digest(review),issue=issue,
                prior_assessment=decisions.get('issue-'+str(j)),
                assessment_hash=digest(outcome)))
    return rows

def validate(product, qid, question, original, candidate, details, reviews, assessments, value):
    population=census(reviews,assessments)
    # Warrant reassessment may change; the original issue and review identity may not.
    original_population=[{k:r[k] for k in ('id','review_index','review_hash','issue')} for r in population]
    expected=dict(profile=PROFILE,question_id=qid,question_hash=digest(question),
        input_hash=product.route.input_hash,original_answer_hash=digest(original),
        current_answer_hash=digest(candidate),requirement_details_hash=digest(details),
        issue_population_hash=digest(original_population))
    require(all(value.get(k)==v for k,v in expected.items()),
        'Stale or foreign current-answer disposition','E_INTEGRITY')
    require(isinstance(value.get('reviewer'),str) and value['reviewer'].strip()
        and read_evidence(value['review_note'],product.root,json_value=False).strip(),
        'Missing current-answer review evidence','E_INTEGRITY')
    for pointer in value.get('reviewed_evidence',[]):
        read_evidence(pointer,product.root,json_value=False)
    rows=value['dispositions']; identifiers=[r['id'] for r in rows]
    require(len(identifiers)==len(set(identifiers))
        and set(identifiers)=={r['id'] for r in population},
        'Missing or duplicate original-issue dispositions','E_INTEGRITY')
    records=[r for r in product.route.records.values() if r['kind']=='source'
        and qid in product.acquisition_questions(r)]
    pending=[]
    for row in rows:
        require(row.get('disposition') in SETTLED|{'STILL_REQUIRED'}
            and isinstance(row.get('reason'),str) and row['reason'].strip(),
            'Missing substantive current-issue disposition','E_INTEGRITY')
        if row['disposition']=='STILL_REQUIRED':
            pending.append(row);continue
        require(row.get('support') and row.get('blocking_source_gaps')==[],
            'Necessary missing evidence cannot be waived','E_INTEGRITY')
        product.citations({'support':row['support'],'source_gaps':[],'assertion_bindings':[]},records)
        answer_quote(candidate,**row['answer_evidence'])
        if row['disposition']=='SUPPORTED_BY_REVIEWED_SOURCE':
            require(bool(value.get('reviewed_evidence')),
                'Supplemental source disposition lacks retained review evidence','E_INTEGRITY')
        if row['disposition']=='CONDITIONALLY_ADDRESSED':
            require(isinstance(row.get('necessary_premises'),list) and row['necessary_premises'],
                'Conditional disposition omits its premises','E_INTEGRITY')
            for premise in row['necessary_premises']:
                require(isinstance(premise.get('description'),str) and premise['description'].strip(),
                    'Missing conditional premise','E_INTEGRITY')
                answer_quote(candidate,**premise['answer_evidence'])
    return dict(profile=PROFILE,current_answer_hash=digest(candidate),
        issue_population_hash=digest(original_population),issue_count=len(population),
        pending=pending,complete=not pending,legal_acceptance=False)

def apply(product,qid,question,original,candidate,details,reviews,assessments):
    checkpoint=getattr(product,'capacity_checkpoint',None)
    if checkpoint is None:return None
    outer=read_evidence(checkpoint,product.root)
    pointer=outer.get('current_answer_issue_dispositions',{}).get(qid)
    if pointer is None:return None
    value=read_evidence(pointer,product.root)
    result=validate(product,qid,question,original,candidate,details,reviews,assessments,value)
    return {**result,'review':pointer}
