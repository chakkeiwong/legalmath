"""Bounded continuation evidence under the original integration-master grant."""
from copy import deepcopy
from dataclasses import replace, asdict
from datetime import datetime, timezone
from pathlib import Path
import math

from scripts.legal_integration_master import (ROOT,BASE,DOC,PROGRAM,PLAN,RULES,STATE,
    TOOLS,QUESTIONS,TOKENIZER,ref,verify,read,save,require)
from scripts.legal_integration_reopening import WORK,LIMITS,USER_INSTRUCTION,AUDIT_PLAN,retain
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct,NOTE,PROFILE


def prepare_binding():
    from scripts.legal_integration_recovery import REPAIR
    from scripts.legal_integration_rehearsal import UnresolvedProvider
    qualification=read(ROOT/WORK/'qualification.json')
    rehearsal=read(ROOT/WORK/'rehearsal-summary.json')
    require(qualification['qualified_local_input'] and
            all(r['answer_validated'] for r in rehearsal['questions'].values()),
            'Reopening is not locally qualified')
    grant=read(ROOT/BASE/'live-grant.json'); ledger=read(ROOT/BASE/'live-calls.json')
    require(len(ledger['calls'])==175,'Reopening ledger changed before registration')
    probe=BoundedProduct(ROOT,ROOT/WORK/'resource-probe',UnresolvedProvider(),
        read(ROOT/WORK/'combined-envelope.json'),tokenizer(ROOT/TOKENIZER),limits=LIMITS)
    populations={}
    for q in QUESTIONS:
        requirements=sum(r['kind'] in ('obligation','reading','case') and probe.applicable(r,q)
                         for r in probe.route.records.values())
        sources=sum(r['kind']=='source' and q in probe.acquisition_questions(r)
                    for r in probe.route.records.values())
        populations[q]={'requirements':requirements,'source_chunks':sources,
            'answer_call_cap':requirements+math.ceil(sources/2)+16,'common_call_cap':640}
    scope={'semantic_controls':96,'canaries':8,
        'acquisition':qualification['reading_packets']+qualification['bridges'],
        'common_preparation':4*640,
        'answers':7*sum(r['answer_call_cap'] for r in populations.values()),
        'comparisons':144,'cross_question_reviews':42}
    total=len(ledger['calls'])+sum(scope.values())
    require(total<=grant['maximum_calls'],'Reopening exceeds original call ceiling')
    seconds=math.ceil((scope['semantic_controls']+8)*120 +
        (sum(scope.values())-scope['semantic_controls']-8)*120/2+1800)
    remaining=math.floor((datetime.fromisoformat(grant['deadline_utc'])-
                          datetime.now(timezone.utc)).total_seconds())
    require(seconds<=remaining,'Reopening exceeds original clock')
    resources={'scope':scope,'populations':populations,'total_including_prior':total,
        'prior_calls':175,'global_ceiling':grant['maximum_calls'],'deadline_utc':grant['deadline_utc'],
        'limits':asdict(LIMITS),'common_cap':640,'arm_buffer':16,'source_review_group_minimum':2,
        'seconds_required':seconds,'seconds_available_at_preparation':remaining,
        'live_calls':0,'role':'Finite admission hypothesis; actual populations are re-budgeted before descendants.'}
    retain(WORK/'resource-envelope.json',resources)
    retain(WORK/'ledger-before.json',ledger)
    original=read(ROOT/BASE/'approval-proposal.json')
    recovery_approval=read(ROOT/BASE/'recovery-approval.json')
    recovery=read(ROOT/recovery_approval['proposal']['path'])
    historical=list(original['bindings'])+list(recovery['bindings'])
    historical += [r['current'] for r in recovery['replacements']]
    baseline=read(ROOT/WORK/'baseline.json')
    archives={(r['path'],r['sha256']):{'path':r['archive'],'sha256':r['sha256']} for r in baseline['files']}
    archives.update({(r['previous']['path'],r['previous']['sha256']):r['archive']
                     for r in recovery['replacements']})
    rows=[]; seen=set()
    for previous in historical:
        key=(previous['path'],previous['sha256'])
        if key in seen: continue
        seen.add(key)
        if ref(ROOT,previous['path'])==previous: continue
        archive=archives.get(key)
        require(archive is not None,'No exact historical archive for '+previous['path'])
        verify(ROOT,archive)
        rows.append({'previous':previous,'archive':archive})
    paths=[PROGRAM,PLAN,RULES,AUDIT_PLAN,WORK/'combined-envelope.json',WORK/'source-result.json',
        WORK/'qualification.json',WORK/'rehearsal-summary.json',WORK/'resource-envelope.json',
        BASE/'campaign-routing.toml',BASE/'applicability.json',Path('requirements-context.lock')]
    paths += [Path(r['path']) for r in qualification['canaries']]
    paths += sorted((ROOT/'src/legalmath').rglob('*.py'))
    paths += [p for p in (ROOT/'scripts').glob('legal_*.py')]
    bindings={str(p):ref(ROOT,p) for p in paths}
    proposal={'profile':'integration-master-reopening-proposal.v1',
        'grant_hash':digest(grant),'global_ceiling':grant['maximum_calls'],
        'deadline_utc':grant['deadline_utc'],'prior_recovery':ref(ROOT,BASE/'recovery-approval.json'),
        'ledger_before':ref(ROOT,WORK/'ledger-before.json'),'historical_bindings':rows,
        'bindings':list(bindings.values()),'resources':ref(ROOT,WORK/'resource-envelope.json'),
        'user_instruction':USER_INSTRUCTION,
        'command':'.venv-context/bin/python scripts/legal_integration_master.py live',
        'attempts':'Original attempts retained; acquisition has one final attempt (3).',
        'review':'Same model, account, ceiling and deadline; new hashes do not alter original authorization.'}
    retain(WORK/'binding-proposal.json',proposal)
    return {'proposal':ref(ROOT,WORK/'binding-proposal.json'),'resources':resources}


def bind():
    proposal=read(ROOT/WORK/'binding-proposal.json')
    for r in proposal['bindings']: verify(ROOT,r)
    for r in proposal['historical_bindings']: verify(ROOT,r['archive'])
    require(read(ROOT/BASE/'live-calls.json')==read(ROOT/proposal['ledger_before']['path']),
            'Unexpected calls before reviewed binding')
    binding={'profile':'integration-master-reopening-binding.v1',
        'proposal':ref(ROOT,WORK/'binding-proposal.json'),'grant_hash':proposal['grant_hash'],
        'user_instruction':USER_INSTRUCTION,'basis':'Continuation of existing user-authorized grant; '
            'no new spending, model, account or clock approval inferred.'}
    retain(BASE/'reopening-binding.json',binding)
    return binding


def fixture(mutation=False, *, explicit_scope=False, missing_authority=False):
    # Opaque record IDs carry no hints about the dependency. The two operative
    # rules appear in different reading/reduction groups with no explicit link.
    texts=['A custodian must block an outgoing transfer whenever the daily totals cannot be reconciled.',
        'Records must identify the currency used for every entry.',
        'The daily register must contain a timestamp.',
        'Staff retain the audit file for seven years.',
        'A supervisor signs the monthly staffing roster.',
        'Currency amounts must include a unit of account.',
        'The archive records the name of the reporting officer.',
        ('Emergency transfers remain subject to the reconciliation block.' if mutation else
         'An outgoing transfer ordered by the court to prevent imminent loss is exempt from the reconciliation block.')]
    question={'question_id':'p14','text':'Synthetic rules only. The daily totals cannot be reconciled. '
        'A court ordered this outgoing transfer to prevent imminent loss. '
        'Must the custodian block it under these rules? Begin the conclusion with exactly '
        'DUTY_REQUIRED or DUTY_NOT_REQUIRED, then explain the rule and every relevant qualification.'}
    if missing_authority:
        texts[-1] = ('Court-ordered emergency transfers are governed by the priority rule in Emergency '
            'Schedule Z, which determines whether they override the reconciliation block. '
            'Emergency Schedule Z is not included in the supplied material.')
        question['text'] = ('The supplied synthetic material is incomplete. The daily totals cannot '
            'be reconciled. A court ordered this outgoing transfer to prevent imminent loss. '
            'Must the custodian block it under the applicable synthetic regime, including its '
            'incorporated Emergency Schedule Z? Begin the conclusion with exactly DUTY_REQUIRED, '
            'DUTY_NOT_REQUIRED or DUTY_UNRESOLVED, then explain the rule and every relevant qualification.')
    envelope = {'source_packet':{'source_key':'semantic.control','authority':'SYNTHETIC_FIXTURE',
        'selected_slice':question['text'],'family_ids':['scope'],'dependencies':[],
        'units':[{'unit_id':f'unit.{i}','locator':f'synthetic clause {i+1}','text':text,
                  'normative':True,'span':{}} for i,text in enumerate(texts)]},
        'original_questions':[question],
        'source_qualification':{'limitations':['Synthetic deterministic rules; no actual legal finding.']},
        'answer_acceptance':{'profile':'product-answer-acceptance.v1','original_questions':[question],
            'source_documents':[],'acceptance_obligations':[],'original_readings':[],'cases':[]}}
    if explicit_scope:
        envelope['question_scopes'] = {'p14': {'mode': 'OPEN_CORPUS' if missing_authority else 'SUPPLIED_RULES_ONLY',
            'basis': ('The question includes an expressly incorporated missing schedule.' if missing_authority
                else 'The question expressly asks for a determination under the supplied synthetic rules only.')}}
    return envelope


def semantic_control(service, *, directory=None, limits=None, per_case_calls=46, maximum_corrections=0,
                     retained_initial=None, scope_controls=False):
    from scripts.legal_product_completion import run_product
    control_directory=directory or ROOT/WORK/'live/semantic-control'
    result_path=control_directory/'result.json'
    rows=[]
    cases = [(False, False, 'remote-exception'), (True, False, 'changed-exception')]
    if scope_controls:
        if retained_initial:
            require(all(read(ROOT/r['path']).get('profile') in ('bounded-exact-checkpoint.v2', 'bounded-full-checkpoint.v3')
                for arms in retained_initial.values() for r in arms.values()),
                'Scoped controls require exact input-bound checkpoints')
        cases.append((False, True, 'missing-incorporated-rule'))
    for mutation, missing_authority, name in cases:
        checkpoints = retained_initial[name] if retained_initial else {}
        envelope=fixture(mutation, explicit_scope=scope_controls, missing_authority=missing_authority)
        partitioned_envelope=deepcopy(envelope)
        partitioned_envelope['answer_acceptance']['acceptance_obligations']=[{
            'id':'synthetic-duty','question_ids':['p14'],
            'statement': ('Resolve the requested applicable regime, preserving genuinely missing incorporated authority.'
                if missing_authority else 'Resolve the stated transfer question under all supplied synthetic rules.')}]
        from legalmath.interpretation.assurance.answer_acceptance import validate_manifest
        validate_manifest(partitioned_envelope['answer_acceptance'],
                          partitioned_envelope['original_questions'],ROOT)
        expected='DUTY_UNRESOLVED' if missing_authority else 'DUTY_REQUIRED' if mutation else 'DUTY_NOT_REQUIRED'
        directory=control_directory/name
        local_limits=replace(limits or LIMITS,records_per_request=1)
        comparison=BoundedProduct(ROOT,directory/'unpartitioned',service,envelope,
            tokenizer(ROOT/TOKENIZER),limits=local_limits,maximum_calls=2,
            retained_initial=checkpoints.get('unpartitioned'))
        records=[r for r in comparison.route.records.values() if r['kind']=='source']
        question=envelope['original_questions'][0]
        baseline=comparison.note('same-evidence-answer','ANSWER_ORIGINAL_QUESTION',question,
            records,{'method':'Read all supplied evidence together.'},[r['id'] for r in records],partition=False)
        # Actual full product entry, same evidence/model and answer contract.
        output=run_product(ROOT,directory/'partitioned',service,Path('/unused-jdk'),
            '2026-10-13T00:00:00Z',sources=[],questions=envelope['original_questions'],
            acceptance_ref=None,qualification={},required={'maximum_calls':per_case_calls,
                'maximum_corrections':maximum_corrections},
            deadline_utc=read(ROOT/BASE/'live-grant.json')['deadline_utc'],selected_tools=[],
            settings=None,consumer_profile=PROFILE,bounded_envelope=partitioned_envelope,
            bounded_encode=tokenizer(ROOT/TOKENIZER),bounded_limits=local_limits,
            retained_initial=checkpoints.get('partitioned'))
        answer=output['answers'].get('p14',{})
        def outcome(value):
            if value.get('status')!='VALIDATED': return False
            text=value['value']['conclusion']
            support=value['value']['support']+value['value']['contrary']
            return text.startswith(expected) and (not missing_authority or bool(value['value']['unresolved'])) and all(any(r['text'] in c['quote']
                for c in support) for r in (records[0],records[-1]))
        row={'case':name,'expected':expected,'same_source_hash':digest(envelope['source_packet']),
            'baseline_pass':outcome(baseline),'partitioned_pass':outcome(answer.get('answer',{})),
            'partitioned_review_accepted':answer.get('review_accepted',False),
            'baseline':baseline,'partitioned':ref(ROOT,directory/'partitioned/result.json'),
            'scope':'One deterministic synthetic control, not general English or legal reliability.'}
        rows.append(row)
        if checkpoints:
            row['retained_initial'] = checkpoints
            row['evidence_class'] = ('Exact request continuation including retained corrections; not an independent model replication.'
                if any(read(ROOT/r['path']).get('profile') == 'bounded-full-checkpoint.v3' for r in checkpoints.values())
                else 'Retained identical initial responses; correction and corrected reviews are fresh; not an independent model replication.')
        save(result_path,{'rows':rows,'qualified':False,'complete':False})
    value={'rows':rows,'complete':True,'qualified':all(r['baseline_pass'] and r['partitioned_pass']
        and r['partitioned_review_accepted'] for r in rows),'promotion':'Scoped G9 control only',
        'repair_trigger':'If meaning or citations are lost, retain the stage and reject full acquisition; '
            'do not retry until favorable.'}
    save(result_path,value)
    return value
