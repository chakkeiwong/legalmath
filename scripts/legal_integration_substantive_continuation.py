"""One bounded substantive continuation in the existing integration master.

This module never reopens live acquisition. It adds independently schedulable
source, conditional-answer and target work while preserving every prior byte,
attempt and resource ledger.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import re

from scripts.legal_integration_master import (ROOT, DOC, BASE, PROGRAM, STATE,
    SUBSTANTIVE_PLAN, QUESTIONS, TOOLS, MasterExecution, run_tests)
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = BASE / 'substantive-continuation'
REVIEW = DOC / 'substantive-continuation-review-2026-10-14.md'


def retain(path, value):
    path = ROOT / path
    if path.exists():
        require(read(path) == value, 'Retained continuation evidence changed: ' + str(path))
    else:
        save(path, value)


def _text_for(envelope, needle):
    from scripts.legal_integration_accounts import source_quote
    return [source_quote(envelope, needle)]


def build_review(envelope):
    rows = {
        'p10': {
            'question': next(q['text'] for q in envelope['original_questions'] if q['question_id']=='p10'),
            'propositions': [
                {'id':'allocation','statement':'The retained responsibility allocation is separate from proof of conduct or outcome.',
                 'evidence':_text_for(envelope,'remain fully responsible')},
                {'id':'records','statement':'Proper-record and ownership propositions require their own warrant and facts.',
                 'evidence':_text_for(envelope,'proper records')},
                {'id':'ut-code-6-8','statement':'The footnote cites section 6.8 of the Code on Unit Trusts and Mutual Funds; the retained code text must be bound separately from Handbook clause 6.8.',
                 'evidence':_text_for(envelope,'maintain a register of holders')},
            ],
            'alternatives':['allocation-only','supervisory-conduct','operational-record-outcome'],
            'facts':['appointment/delegation terms','powers and information access','record roles','dated incidents','remedial conduct'],
            'status':'CONDITIONAL_OPEN'},
        'p14': {
            'question': next(q['text'] for q in envelope['original_questions'] if q['question_id']=='p14'),
            'propositions': [
                {'id':'trigger','statement':'The main-text demonstration condition includes an SFC request and a confirmation/demonstration object.',
                 'evidence':_text_for(envelope,'upon SFC')},
                {'id':'rival','statement':'Footnote language is retained as a rival reading and is not silently collapsed into the main trigger.',
                 'evidence':_text_for(envelope,'confirmation')},
            ],
            'alternatives':['main-request-trigger','standing-footnote-rival'],
            'facts':['request scope/date','deployed contract version','audit scope','reliance justification','SFC response'],
            'status':'CONDITIONAL_OPEN'},
        'evidence': {
            'question': next(q['text'] for q in envelope['original_questions'] if q['question_id']=='evidence'),
            'propositions': [
                {'id':'agreement','statement':'Matching records or a completed reconciliation do not by themselves establish legal adequacy.',
                 'evidence':_text_for(envelope,'proper records')},
                {'id':'counterexample','statement':'The matching-but-wrong-record counterexample remains an adverse control.',
                 'evidence':_text_for(envelope,'ownership')},
            ],
            'alternatives':['event-established','sufficiency-established'],
            'facts':['applicable legal standard','record provenance','reconciliation method','supervisory powers','ownership evidence'],
            'status':'CONDITIONAL_OPEN'},
        'gatecoin': {
            'question': next(q['text'] for q in envelope['original_questions'] if q['question_id']=='gatecoin'),
            'propositions': [
                {'id':'scenarios-one-four','statement':'The first four scenario direction is defeasible on evidence of access or use.',
                 'evidence':_text_for(envelope,'1st to 4th scenarios')},
                {'id':'scenario-seven','statement':'The scenario-seven tension remains visible and is not resolved by exclusion.',
                 'evidence':_text_for(envelope,'7th scenario')},
            ],
            'alternatives':['ncc-defeasible-direction','later-treatment-unresolved'],
            'facts':['actual parties','terms','rights','access/use evidence','property relationship','transfer terms'],
            'status':'CONDITIONAL_OPEN'},
    }
    path = WORK / 'conditional-accounts.json'
    retain(path, {'profile':'substantive-conditional-accounts.v1','source':ref(ROOT, BASE/'remaining-work/quotation-repair-envelope.json'), 'questions':rows,
                  'legal_entailment':'REQUIRES_REVIEW','current_law_exhaustive':False})
    return path


def register():
    existing = read(ROOT / PROGRAM)
    if existing.get('substantive_continuation_revision'):
        from scripts.legal_integration_post_review import register as correct, REVIEW as correction_review
        if (ROOT/correction_review).exists():
            correct()
        return MasterExecution(ROOT,PROGRAM,STATE).summary()
    require(existing.get('remaining_work_revision'),
            'Substantive continuation requires the current remaining-work master')
    old_state = read(ROOT / STATE)
    old_mission = read(ROOT / DOC / 'mission.json')
    archive = {}
    for path in (PROGRAM, STATE, DOC / 'mission.json'):
        target = WORK / 'before' / path
        (ROOT / target).parent.mkdir(parents=True, exist_ok=True)
        if (ROOT / target).exists():
            require((ROOT / target).read_bytes() == (ROOT / path).read_bytes(),
                    'Changed continuation baseline: ' + str(path))
        else:
            shutil.copy2(ROOT / path, ROOT / target)
        archive[str(path)] = {'previous':ref(ROOT,path),'archive':ref(ROOT,target)}
    baseline = {'profile':'substantive-continuation-baseline.v1',
        'prior_program':archive[str(PROGRAM)]['archive'], 'prior_state':archive[str(STATE)]['archive'],
        'prior_mission':archive[str(DOC / 'mission.json')]['archive'],
        'archived':list(archive.values()),
        'prior_attempts':{tid:len(row['attempts']) for tid,row in old_state['tasks'].items()},
        'prior_calls':232, 'prior_detours':22}
    retain(WORK / 'baseline.json',baseline)
    require(not any(r['status']=='RUNNING' for r in old_state['tasks'].values()), 'Cannot revise while a node is running')
    envelope = read(ROOT / BASE / 'remaining-work/quotation-repair-envelope.json')
    build_review(envelope)
    require((ROOT/REVIEW).is_file(), 'Missing skeptical continuation review')
    program = deepcopy(existing); state = deepcopy(old_state)
    nodes = []
    def add(tid, requires=(), after=(), questions=QUESTIONS, deliverable=''):
        nodes.append({'id':tid,'executor':'command','kind':'product_evaluation','question_ids':list(questions),
            'priority':5,'requires':list(requires),'after':list(after),'any_success':[],
            'maximum_attempts':1,'write_resources':['substantive-'+tid],'inputs':[ref(ROOT,REVIEW)],
            'acceptance':deliverable,'deliverable':str(BASE/'substantive-continuation'/tid/'result.json'),
            'command':['.venv/bin/python','scripts/legal_integration_master.py','worker',tid], 'timeout_seconds':3600})
    add('ownership-2023',['sources'],questions=['gatecoin'],deliverable='Rendered and source ownership for Gatecoin 2023 answer passages, unresolved displays retained')
    add('ownership-2025',['sources'],questions=['gatecoin'],deliverable='Rendered and source ownership for Gatecoin 2025 reasons/disposition/annexure')
    add('ownership-handbook',['sources'],questions=QUESTIONS,deliverable='Exact retained Handbook answer passages and unresolved clause ownership')
    add('account-p10',['sources'],after=['ownership-handbook'],questions=['p10'],deliverable='Conditional P10 allocation/conduct/outcome account with sources, alternatives and facts')
    add('account-p14',['sources'],after=['ownership-handbook'],questions=['p14'],deliverable='Conditional P14 trigger/object/rival account with paragraphs 15/16 and facts')
    add('account-evidence',['sources'],after=['ownership-handbook'],questions=['evidence'],deliverable='Evidence/sufficiency account with matching-but-wrong-record adverse control')
    add('account-gatecoin',['sources'],after=['ownership-2023','ownership-2025'],questions=['gatecoin'],deliverable='Gatecoin case-specific conditional account including scenario-seven tension')
    add('graph-p14',['account-p14'],questions=['p14'],deliverable='Supported/adverse/unknown P14 targets for installed graph adapters')
    add('graph-gatecoin',['account-gatecoin'],questions=['gatecoin'],deliverable='Supported/adverse/unknown Gatecoin targets for installed graph adapters')
    add('current-binding',after=[n['id'] for n in nodes],questions=QUESTIONS,deliverable='Current code/source/provider binding with finite proposal or exact live veto')
    add('continuation-review',after=[n['id'] for n in nodes]+['current-binding'],questions=QUESTIONS,deliverable='Independent release assessment and exact next frontier')
    program['substantive_continuation_revision']={'profile':'legal-substantive-continuation.v1','prior_detours':22,
        'additional_consolidated_revision':1,'prior_charged_calls':232,'live_calls_added':0,'attempts_reset':False,
        'user_instruction':'do as you suggested to repair the program to close the gaps above. review the program thoroughly. execugte the program',
        'plan':ref(ROOT,SUBSTANTIVE_PLAN),'review':ref(ROOT,REVIEW),
        'prior_program':archive[str(PROGRAM)]['archive'],
        'prior_state':archive[str(STATE)]['archive'],'baseline':ref(ROOT,WORK/'baseline.json'),
        'reopened_nodes':[n['id'] for n in nodes],
        'attempt_ceilings':{n['id']:1 for n in nodes},'live_dispatch':'BLOCKED_UNTIL_CURRENT_CODE_SOURCE_PROVIDER_BINDING'}
    program['protected_evidence'] += [ref(ROOT,SUBSTANTIVE_PLAN),ref(ROOT,REVIEW),ref(ROOT,WORK/'baseline.json')]
    # Preserve the original graph and append a bounded continuation population;
    # the validator sees the original 78 plus these explicit local nodes.
    program['tasks'] += nodes
    for n in nodes:
        state['tasks'][n['id']]={'status':'PENDING','attempts':[]}
    validate_program(program,ROOT)
    state['program_hash']=digest(program)
    state['events'].append({'task_id':None,'action':'REGISTERED_SUBSTANTIVE_CONTINUATION','at_utc':datetime.now(timezone.utc).isoformat(),
        'plan':ref(ROOT,SUBSTANTIVE_PLAN),'review':ref(ROOT,REVIEW),'attempts_reset':False,'live_calls_added':0})
    mission=historical_projection(deepcopy(old_mission),
        {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in archive.values()})
    mission['integration_master']['program']=ref(ROOT,PROGRAM)
    mission['integration_master']['substantive_continuation_revision']=program['substantive_continuation_revision']
    mission['history'].append({'id':'integration-master-substantive-continuation-2026-10-14','task_id':'product-contribution',
      'kind':'product_evaluation','outcome':'no_advance','decision':'Registered bounded source/account/target continuation; live dispatch remains vetoed.',
      'next_task':'product-contribution','next_task_reason':'Execute independent substantive continuation nodes and retain precise blockers.',
      'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'result_evidence':[ref(ROOT,PROGRAM),ref(ROOT,SUBSTANTIVE_PLAN),ref(ROOT,REVIEW)]})
    # Write the new graph and state together. Validation then checks the exact
    # mission projection; a failure restores the archived predecessor bytes.
    try:
        save(ROOT/PROGRAM,program);save(ROOT/STATE,state)
        mission['integration_master']['program']=ref(ROOT,PROGRAM)
        mission['history'][-1]['result_evidence'][0]=ref(ROOT,PROGRAM)
        from scripts import legal_mission_control as control
        require(control.validate(mission,read(ROOT/DOC/'tools.json'),ROOT)['detours_since_advance']==23,
                'Continuation lost cumulative detour accounting')
        save(ROOT/DOC/'mission.json',mission)
    except Exception:
        shutil.copy2(ROOT / archive[str(PROGRAM)]['archive']['path'],ROOT/PROGRAM)
        shutil.copy2(ROOT / archive[str(STATE)]['archive']['path'],ROOT/STATE)
        shutil.copy2(ROOT / archive[str(DOC/'mission.json')]['archive']['path'],ROOT/DOC/'mission.json')
        raise
    return MasterExecution(ROOT,PROGRAM,STATE).summary()


def ownership(tid, envelope, directory):
    from scripts.legal_integration_substantive import ownership_audit
    result = ownership_audit(envelope,directory)
    focus = 'gatecoin-2023' if tid.endswith('2023') else 'gatecoin-2025' if tid.endswith('2025') else None
    if focus:
        path = directory/'answer-relevant.json'
        source = read(ROOT/'artifacts/legal-mission-control/2026-10-12/remaining-work/conditional-source-bank.json')
        tags = ['terms-and-intention','conclusion-82'] if focus.endswith('2023') else ['classification-8','disposition-95','annexure-issue1']
        audit = read(directory/(focus+'-ownership.json'))
        rows=[]
        for tag in tags:
            quote = source[f'{focus}.{tag}']['passage']['span']['quote']
            normalized = ' '.join(quote.split())
            matches=[r['locator'] for r in audit['paragraph_intervals']
                     if normalized[:60] in ' '.join(' '.join(c['text'].split()) for c in r['components'])]
            require(len(matches)==1,'Answer passage has ambiguous paragraph ownership: '+tag)
            rendered = ' '.join((ROOT/audit['rendered']['path']).read_text().split())
            display = '1.1' if tag=='annexure-issue1' else matches[0][1:] + '.'
            visible = re.search(r'(?<!\d)'+re.escape(display)+r'\s+'+re.escape(normalized[:35]),rendered)
            require(visible is not None,'Rendered display label not verified: '+tag)
            annexure = tag=='annexure-issue1'
            if annexure:
                require('ANNEXURE Issue 1' in rendered[max(0,visible.start()-120):visible.start()],
                        'Annexure ownership not visible before 1.1')
            rows.append({'passage':tag,'locator':('Annexure Issue 1 §1.1' if annexure else matches[0]),
                         'source_interval_candidate':matches[0],
                         'excluded_from_main_paragraph':matches[0] if annexure else None,
                         'rendered_label':display,'rendered_label_verified':True,
                         'source':source[f'{focus}.{tag}']['original']})
        save(path,{'focus':focus,'passages':rows,'full_document_qualified':False,'unresolved':audit['remaining']})
        result.update({'answer_relevant':ref(ROOT,path),'_conclusion':focus+' answer passages mapped to unique source intervals and rendered text; full judgment locator qualification remains open.'})
    else:
        handbook=[]
        for unit in envelope['source_packet']['units']:
            if unit.get('unit_id','').startswith('handbook.') and any(str(p) in unit.get('locator','') for p in (16,17,18,24,37,42,43)):
                handbook.append({'unit_id':unit['unit_id'],'locator':unit.get('locator'),'text_hash':digest(unit['text'])})
        require(handbook,'No retained Handbook answer pages')
        code = next(u for u in envelope['source_packet']['units'] if u['unit_id'].startswith('d497635c84096.u0.') )
        general = next(u for u in envelope['source_packet']['units'] if u['unit_id']=='handbook.oct2024.page17')
        require('6.8 The scheme, or in the case of a unit trust' in ' '.join(code['text'].split()),
                'Unit Trust Code section 6.8 not retained')
        require('6.8 All Product Key Facts Statements' in ' '.join(general['text'].split()),
                'General Handbook section 6.8 not retained')
        path=directory/'handbook-ownership.json';save(path,{'pages':handbook,
            'distinct_6_8_sources':{
                'code_on_unit_trusts':{'unit_id':code['unit_id'],'source_text':
                    '6.8 The scheme, or in the case of a unit trust, the trustee or the person so appointed by the trustee must maintain a register of holders.',
                    'use':'Footnote 1 cross-reference to appointed register keeper; source edition/current applicability still needs review.'},
                'general_handbook':{'unit_id':general['unit_id'],'source_text':
                    '6.8 All Product Key Facts Statements shall carry a prominent upfront warning statement',
                    'use':'Different Section I disclosure rule; cannot support footnote 1 outsourcing.'}},
            'clause_boundaries':'SCOPED_6_8_DISTINCTION_ONLY','full_document_qualified':False})
        result.update({'answer_relevant':ref(ROOT,path),'_conclusion':'Retained Unit Trust Code 6.8 and general Handbook 6.8 distinguished; current applicability and wider clause ownership remain open.'})
    result['focus']=tid
    return result


def graph_target(qid, envelope, directory):
    from scripts.legal_integration_accounts import run_graph
    return run_graph(qid, envelope, directory)


def worker(tid,directory):
    envelope=read(ROOT/BASE/'remaining-work/quotation-repair-envelope.json')
    if tid.startswith('ownership-'):
        return ownership(tid,envelope,directory)
    if tid.startswith('account-'):
        from scripts.legal_integration_accounts import conditional_account
        qid=tid[8:]; accounts=conditional_account(qid,envelope)
        path=directory/'account.json'; save(path,accounts)
        return {'account':ref(ROOT,path),'legal_entailment':'CONDITIONAL_SOURCE_REVIEW','facts':accounts['facts_required'],
                '_conclusion':qid+' conditional account retained with source propositions, alternatives and factual requests; not legal closure.'}
    if tid.startswith('graph-'):
        return graph_target(tid[6:],envelope,directory)
    if tid=='current-binding':
        from scripts.legal_integration_post_review import binding_proposal
        return binding_proposal(directory)
    if tid=='continuation-review':
        return {'frontier':MasterExecution(ROOT,PROGRAM,STATE).summary(),'integration_complete':False,
          '_conclusion':'Continuation assessed; source/account/target work is retained, while complete original matched effects remain open.'}
    raise ValueError('No substantive continuation worker: '+tid)

