"""Freeze the original substitution-reference continuation before admission."""
from copy import deepcopy
from scripts.prospectus_substitution_references import ROOT,AUTH,DONOR,PREP,SPEC,PLAN,TESTS,costs
from scripts.prospectus_margin_preparation import read,save,sha,relative


def propose():
    from legalmath.prospectus.execution_authority import Authority,CODE,digest as authority_digest
    program=read(AUTH/'program.json')
    assert program['revision']==276
    inputs={relative(f):sha(f) for f in sorted(PREP.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
    spec=read(PREP/'source-review.json')
    inputs.update(spec['images'])
    inputs.update({s['path']:s['sha256'] for s in spec['sources']})
    for folder,names in ((DONOR,('outputs.json','installed-construct/products.json.gz',
        'installed-interpret/semantic.json.gz','installed-complete/downstream-products.json.gz','installed-answer/ordinary-answer.json.gz')),
        (AUTH/'attempts/basf-references/attempt-017',('outputs.json','candidate-answer.json.gz','result.json')),
        (AUTH/'attempts/basf-references/attempt-017',('outputs.json','candidate-answer-reconciliation.json.gz'))):
        manifest=read(folder/'outputs.json')
        for name in names:
            f=folder/name
            if name!='outputs.json':assert sha(f)==manifest[name]
            inputs[relative(f)]=sha(f)
    for name,checksum in inputs.items():assert sha(ROOT/name)==checksum
    methods={relative(f):sha(f) for f in sorted((ROOT/'src/legalmath/prospectus').rglob('*')) if f.suffix in ('.py','.json')}
    for name in (*CODE,PLAN,'scripts/prospectus_substitution_revision.py','scripts/prospectus_substitution_references.py',
        'scripts/prospectus_substitution_reference_preparation.py','scripts/prospectus_substitution_reference_oracle.py',
        'scripts/prospectus_default_references.py','scripts/prospectus_default_reference_preparation.py',
        'scripts/prospectus_governance_references.py','scripts/prospectus_governance_reference_preparation.py',
        'scripts/prospectus_reference_integrity.py','scripts/prospectus_reference_integrity_preparation.py',
        'scripts/prospectus_reference_integrity_oracle.py','scripts/prospectus_payment_references.py',
        'scripts/prospectus_payment_reference_preparation.py','scripts/prospectus_relative_notices.py',
        'scripts/prospectus_margin_preparation.py','scripts/prospectus_typed_delta.py',*TESTS):
        methods[name]=sha(ROOT/name)
    save(PREP/'freeze.json',{'methods':methods,'inputs':inputs})
    attempts=[e['attempt'] for e in Authority(ROOT).events() if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==17
    proposal=deepcopy(program)
    proposal['revision']=277
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,timeout_seconds=180,build_criteria_scope=[],
        reason='Original substitution certification and amendment references need complete selected targets; generic admission accepts omitted conditions and procedures',
        substitution_reference_review={'version':'basf-substitution-references.v1','review':relative(PREP),
            'original_task_complete':False,'bounds':{'stage_seconds':180,'new_seconds':1200,'new_bytes':160*1024**2},
            'further_harness_retry_allowed':False},pre_admission_review=relative(PREP/'PRE-ADMISSION-REVIEW.md'))
    task['inputs']=list(dict.fromkeys(task['inputs']+list(methods)+list(inputs)+[relative(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=18
    routes=read(ROOT/program['continuation_review']['routes'])
    routes['baseline_revision']=277
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(dossier=PLAN,task_sha256=authority_digest(task),
                remaining='017 records30links and separates source binding from target meaning; original substitution and amendment targets remain incomplete.',
                next_action='Bind complete conditions(a)-(d) and amendment procedures, replace the exact discovery identity, preserve target uncertainty and continue original source remainder.',
                acceptance='Independent original paragraphs and whole-answer effects, source/consumer forgeries refused, original60records preserved; finite partial evidence only.',
                stop_condition='Eighteen cumulative admissions;90s preparation;180s stages;1200s new measured;160MiB/4MiB reserve;no unchanged/harness retry.')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=relative(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),relative(PREP/'routes.json'):sha(PREP/'routes.json'),
        relative(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    review={'baseline':authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'original_obligations_preserved':True,'changes':['Two original substitution source links','Complete conditions and amendment procedures with unchanged v3 uncertainty',
            'Matched omission and actual consumer verification','Original60record reconciliation preserved'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'reproduced':relative(PREP/'pre-repair.json'),
            'target_bounds':{'certification':'128:75-81;129:1-4,12-22;exact selected brackets','amendment':'129:54-76;130:1-2,10-11,23-74;131:1-31'},
            'statutory_interpretation_remains_unresolved':True,'whole_task_acceptance_claimed':False},
        'evidence_contract':{'primary':'Independently transcribed original targets and actual complete consumer behavior',
            'veto':['Lost condition(d)','Lost amendment procedure','Promoted UNKNOWN meaning','Wrong paragraph','Hidden uncertainty','Changed unrelated meaning','Method drift','Resource/harness failure'],
            'not_concluded':['Actual substitution','Actual certification or votes','Statutory application','Whole reference graph','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':17,'new_maximum':18,'retained_attempts':attempts,
            'reason':'Two new original unresolved target mappings and reproduced truncation acceptance; no retry of prior packages',
            'next_discriminating_check':'Complete conditions and amendment targets versus missing(d), omitted procedures and false promotion through actual consumer',
            'stop_condition':'180s stages;1200s measured;160MiB;no unchanged/harness retry',
            'same_scope_authorization':'User requests general build and original source closure without external-opinion dependency'}}
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':277,'prior_admissions':17,'resources':costs()}
