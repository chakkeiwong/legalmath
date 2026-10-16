"""Reviewed continuation of the same integration master; no historical reset."""
from copy import deepcopy
from dataclasses import replace, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import os
import subprocess
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.legal_integration_master import (BASE, DOC, TOKENIZER, QUESTIONS, TOOLS,
    PROGRAM, PLAN, STATE, MasterExecution, read, save, ref, verify, require)
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer, citation_dependencies
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, AUDIT
from legalmath.interpretation.assurance.bounded_references import prepare as references
from scripts.legal_integration_recovery import ReferenceRehearsal, selected_canary_records

WORK = BASE/'reviewed-reopening'
LIMITS = replace(Limits(), records_per_request=2)
AUDIT_PLAN = DOC/'integration-master-code-audit-2026-10-13.md'
USER_INSTRUCTION = ('thoroughly audit the code base to identify all the issues with the integration issues.  '
    'refresh the master program with the remaining works.   review the program.  execute')


def retain(path, value):
    path = ROOT/path
    if path.exists(): require(read(path) == value, 'Refuse to replace retained input: '+str(path))
    else: save(path, value)


def sources():
    from legalmath.interpretation.assurance.legal_locators import build_index, retained_html
    from legalmath.interpretation.assurance.answer_acceptance import reading_quote_locations, validate_manifest
    original = read(ROOT/BASE/'combined-envelope.json')
    envelope = deepcopy(original)
    supplement_path = BASE/'corpus-work/source-supplement.json'
    supplement = read(ROOT/supplement_path); handbook = supplement['handbook']
    verify(ROOT, handbook['current_pdf'])
    extracted = BASE/'corpus-work/ut-handbook-current.txt'
    pages = (ROOT/extracted).read_text().split('\f')
    # Selected pages include the complete Overarching Principles (including
    # definitions and adjacent scope), not only convenient isolated clauses.
    selected = sorted(set(range(7,16)) | {24,37,42,43})
    units = envelope['source_packet']['units']
    for page in selected:
        text = pages[page-1]
        require(text.strip(), 'Empty retained Handbook page')
        units.append({'unit_id': f'handbook.oct2024.page{page}',
            'text': text, 'locator': f'SFC Handbook October 2024 fifth edition, PDF page {page}',
            'normative': True, 'span': None})
    require(len(units) == len({r['unit_id'] for r in units}), 'Duplicate corpus identity')
    # None is permitted by the original Packet schema; ContextRoute requires
    # mapping metadata for this exact indexed profile.
    for unit in units:
        if unit.get('span') is None: unit['span'] = {}
    envelope['source_question_ids'] = {u['unit_id']: (['gatecoin'] if 'judiciary.hk' in u['locator']
        else list(QUESTIONS)) for u in units}
    packet = envelope['source_packet']
    envelope['source_qualification']['source_packet_hash'] = digest(packet)
    envelope['source_qualification']['evidence'] += [ref(ROOT,supplement_path),
        handbook['current_pdf'], ref(ROOT,extracted)]
    envelope['source_qualification']['limitations'] += [
        'Added complete retained Handbook general-principle pages and selected UT pages. '
        'Applicability depends on actor/product/date/authorization conditions; no universal P10 cure test.',
        'Handbook and judgment quotations use exact source-unit text; full legal paragraph/footnote indexing remains unqualified.']
    envelope['legal_indexes'] = [build_index(packet,retained_html(d['source'],ROOT),source_ref=d['source'],
        unit_ids=d['unit_ids'],root=ROOT,numbering_profile=d.get('numbering_profile','ordered-lists'))
        for d in envelope['answer_acceptance']['source_documents']]
    envelope['answer_acceptance']['current_quote_locations'] = reading_quote_locations(envelope['answer_acceptance'],packet)
    envelope['binding'] = {'profile':'bounded-combined-corpus.v2', 'predecessors':[
        ref(ROOT,BASE/'combined-envelope.json'),ref(ROOT,supplement_path)], 'source_packet_hash':digest(packet)}
    envelope['binding_hash'] = digest(envelope['binding'])
    validate_manifest(envelope['answer_acceptance'],envelope['original_questions'],ROOT)
    for name in ('acceptance_obligations','original_readings','cases'):
        require(envelope['answer_acceptance'][name] == original['answer_acceptance'][name], 'Changed original population')
    retain(WORK/'combined-envelope.json',envelope)
    result = {'original_units':len(original['source_packet']['units']), 'revised_units':len(units),
        'added_pdf_pages':selected, 'original_populations_unchanged':True,
        'symmetric_comparator_sources':True,'full_corpus_qualification':False,
        'remaining':['Verified judgment/Handbook locators','Source-to-rule and applicability review',
                     'Complete relevant later-treatment and contrary-authority research']}
    retain(WORK/'source-result.json',result)
    return result


def qualification():
    from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
    from legalmath.interpretation.search.schema import validate_output_schema
    envelope = read(ROOT/WORK/'combined-envelope.json')
    encoder = tokenizer(ROOT/TOKENIZER)
    service = BoundedCodexProvider(ROOT,ROOT/BASE,encoder,LIMITS,
        routing_file=ROOT/BASE/'campaign-routing.toml')
    product = BoundedProduct(ROOT,ROOT/WORK/'qualification',ReferenceRehearsal(),envelope,encoder,limits=LIMITS)
    packets,blocked = product.route.reading_plan()
    deps,unresolved = citation_dependencies(envelope)
    bridges,bridge_blocks = product.route.dependency_packets(deps)
    measurements=[]
    for packet in packets+bridges:
        prepared = references(packet['request'],packet['schema'])
        validate_output_schema(prepared['schema'])
        try: outcome={'status':'PASS', **service.measure(prepared['request'],prepared['schema'])}
        except Exception as exc: outcome={'status':'FAILED','reason':str(getattr(exc,'details',None) or exc)}
        measurements.append({'packet_hash':packet['packet_hash'],**outcome})
    canaries=[]; canary_measurements=[]
    for q in envelope['original_questions']:
        ids,selection=selected_canary_records(product,q['question_id'])
        packet=product.route.make_packet('READ_SOURCE',ids,question_ids=[q['question_id']],reader='reopening-canary')
        request=product.request('AUDIT_ANSWER_AGAINST_SOURCE',q,[product.route.records[i] for i in ids],
            payload={'conclusion':'A recorded action alone establishes full compliance; no further legal standard or fact matters.',
                     'control':'Deliberately unsupported statement; assess it against the sources.'},expected=ids)
        for req,schema in ((packet['request'],packet['schema']),(request,AUDIT)):
            wire=references(req,schema); validate_output_schema(wire['schema'])
            try: measurement={'status':'PASS',**service.measure(wire['request'],wire['schema'])}
            except Exception as exc: measurement={'status':'FAILED','reason':str(getattr(exc,'details',None) or exc)}
            canary_measurements.append({'question':q['question_id'],'task':req['task'],**measurement})
        path=WORK/'canaries-qualified'/(q['question_id']+'.json')
        retain(path,{'question':q['question_id'],'reading':packet,'review_request':request,
                     'review_schema':AUDIT,'source_selection':selection})
        canaries.append(ref(ROOT,path))
    result={'input_hash':product.route.input_hash,'source_chunks':sum(r['kind']=='source' for r in product.route.records.values()),
        'reading_packets':len(packets),'bridges':len(bridges),'blocked':blocked+bridge_blocks+unresolved,
        'wire_measurements':measurements,'canaries':canaries,'canary_measurements':canary_measurements,'live_calls':0,
        'qualified_local_input':not(blocked+bridge_blocks+unresolved) and
            all(m['status']=='PASS' for m in measurements+canary_measurements),
        'semantic_preservation_qualified':False,'actual_service_framing_qualified':False}
    retain(WORK/'qualification.json',result)
    return {k:v for k,v in result.items() if k not in ('wire_measurements','canaries')}


def rehearse():
    from scripts.legal_product_completion import run_product
    from legalmath.interpretation.assurance.bounded_product import PROFILE
    directory = ROOT/WORK/'rehearsal'
    implementation = [ref(ROOT,p) for p in [Path(__file__),
        ROOT/'src/legalmath/interpretation/assurance/bounded_product.py',
        ROOT/'src/legalmath/interpretation/assurance/bounded_references.py']]
    retain(WORK/'rehearsal-implementation.json', implementation)
    envelope = read(ROOT/WORK/'combined-envelope.json')
    provider = ReferenceRehearsal()
    result = run_product(ROOT,directory,provider,Path('/unused-jdk'),'2026-10-13T00:00:00Z',
        sources=[],questions=envelope['original_questions'],acceptance_ref=None,qualification={},
        required={'maximum_calls':4096},deadline_utc=read(ROOT/BASE/'live-grant.json')['deadline_utc'],
        selected_tools=[],settings=None,consumer_profile=PROFILE,bounded_envelope=envelope,
        bounded_encode=tokenizer(ROOT/TOKENIZER),bounded_limits=LIMITS)
    for item in implementation: verify(ROOT,item)
    summary = {'live_calls':0,'scripted_calls':len(provider.requests),'trace':result['trace'],
        'questions':{q:{'answer_validated':r.get('answer',{}).get('status')=='VALIDATED',
            'reason':r.get('reason')} for q,r in result['answers'].items()},
        'legal_acceptance':False,'meaning_preservation_qualified':False,
        'implementation':implementation,'result':ref(ROOT,directory/'result.json')}
    retain(WORK/'rehearsal-summary.json',summary)
    return summary


def migrate():
    """Explicit same-program migration; completed attempts remain immutable."""
    from scripts.legal_mission_execution import digest as state_digest, validate_program
    from scripts import legal_mission_control as control
    import fcntl
    with (ROOT/STATE).with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        mission=read(ROOT/DOC/'mission.json')
        if mission['integration_master'].get('reviewed_reopening'):
            return {'migration':'ALREADY_REGISTERED'}
        baseline=read(ROOT/WORK/'baseline.json')
        archives={row['path']:{'path':row['archive'],'sha256':row['sha256']} for row in baseline['files']}
        program=read(ROOT/PROGRAM); state=read(ROOT/STATE)
        require(state['program_hash']==state_digest(program),'Unexpected prior program')
        require(not any(r['status']=='RUNNING' for r in state['tasks'].values()),'Prior owner still running')
        require(len(read(ROOT/BASE/'live-calls.json')['calls'])==175,'Prior call count changed')
        require(ref(ROOT,PROGRAM)['sha256']==archives[str(PROGRAM)]['sha256'],'Prior program changed')
        require(ref(ROOT,STATE)['sha256']==archives[str(STATE)]['sha256'],'Prior execution changed')
        for path in (PROGRAM,PLAN,STATE): verify(ROOT,archives[str(path)])
        def historical(value):
            if isinstance(value,dict):
                if set(value)=={'path','sha256'} and value['path'] in archives:
                    archived=archives[value['path']]
                    if value['sha256']==archived['sha256'] and ref(ROOT,value['path'])!=value:
                        return archived
                return {k:historical(v) for k,v in value.items()}
            if isinstance(value,list): return [historical(v) for v in value]
            return value
        # Historical rows refer to the byte-identical predecessor, not the
        # current mutable program. The active registration is set separately.
        mission=historical(mission)
        for row in mission['history']:
            for item in row.get('result_evidence',[]):
                if item.get('path')==str(PROGRAM) and item.get('sha256')==archives[str(PROGRAM)]['sha256']:
                    item.update(archives[str(PROGRAM)])
        program['protected_evidence']=[archives[str(PLAN)] if r['path']==str(PLAN) else r
                                       for r in program['protected_evidence']]
        program['protected_evidence'] += [ref(ROOT,PLAN),ref(ROOT,AUDIT_PLAN)]
        reopened=[]
        for task in program['tasks']:
            tid=task['id']
            if tid=='scope' or tid.startswith('legal-'): continue
            row=state['tasks'][tid]
            if row['status']=='PENDING': continue
            require(len(row['attempts'])<3,'No fourth attempt permitted')
            task['maximum_attempts']=max(task['maximum_attempts'],len(row['attempts'])+1)
            row['status']='PENDING'; row['reason']='Reviewed reopening; all earlier attempts retained.'
            row.pop('result',None)
            row.pop('live_supervisor',None); row.pop('master_live',None)
            reopened.append(tid)
        program['reviewed_reopening']={'audit':ref(ROOT,AUDIT_PLAN),'prior_program':archives[str(PROGRAM)],
            'prior_state':archives[str(STATE)],'prior_calls':175,'prior_detours':19,
            'reopened_nodes':reopened,'sources':ref(ROOT,WORK/'combined-envelope.json')}
        validate_program(program,ROOT)
        state['program_hash']=state_digest(program)
        state.pop('mission_sync_error',None)
        state['events'].append({'task_id':'scope','action':'REVIEWED_SAME_PROGRAM_MIGRATION',
            'at_utc':datetime.now(timezone.utc).isoformat(),'reopened_nodes':reopened,
            'prior_state':archives[str(STATE)],'attempts_reset':False})
        save(ROOT/PROGRAM,program); save(ROOT/STATE,state)
        registration=mission['integration_master']
        registration.update(program=ref(ROOT,PROGRAM),plan=ref(ROOT,PLAN),
            reviewed_reopening={'prior_detours':19,'additional_consolidated_revision':1,
                'prior_charged_calls':175,'review':ref(ROOT,AUDIT_PLAN),
                'user_instruction':USER_INSTRUCTION,'baseline':ref(ROOT,WORK/'baseline.json')})
        mission['history'].append({'id':'integration-master-reviewed-reopening-2026-10-13',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Reviewed same-master repair; preserve all prior calls, attempts and original deadline.',
            'next_task':'product-contribution','next_task_reason':'Execute repaired independent branches; '
                'qualify actual semantic preservation before original acquisition.',
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[ref(ROOT,AUDIT_PLAN),ref(ROOT,PROGRAM),ref(ROOT,WORK/'baseline.json')]})
        mission['next_task_reason']=mission['history'][-1]['next_task_reason']
        # The currently blocked substantive status is preserved until its new
        # prerequisites are actually qualified; refresh can record a refusal.
        save(ROOT/DOC/'mission.json',mission)
    control.validate(mission,read(ROOT/DOC/'tools.json'),ROOT)
    return {'migration':'REGISTERED','reopened':reopened,'prior_calls':175,'detours':20}


def local_node(tid, directory):
    if tid=='sources':
        return {'envelope':ref(ROOT,WORK/'combined-envelope.json'),
                'source_result':ref(ROOT,WORK/'source-result.json')}
    if tid.startswith('qualify-'):
        q=read(ROOT/WORK/'qualification.json'); rehearsal=read(ROOT/WORK/'rehearsal-summary.json')
        require(q['qualified_local_input'],'Local request qualification failed')
        require(rehearsal['questions'][tid[8:]]['answer_validated'],'Original-input rehearsal failed')
        return {'qualification':ref(ROOT,WORK/'qualification.json'),
            'rehearsal':ref(ROOT,WORK/'rehearsal-summary.json'),'semantic_control':'LIVE_REQUIRED'}
    if tid=='campaign':
        from scripts.legal_integration_reopening_live import prepare_binding
        return prepare_binding()
    raise ValueError('Unknown reviewed local node')


def activate():
    from scripts import legal_integration_campaign as campaign
    campaign.LIVE=WORK/'live'
    campaign.ENVELOPE=WORK/'combined-envelope.json'
    campaign.CANARIES=WORK/'canaries-qualified'
    campaign.RESOURCES=WORK/'resource-envelope.json'
    campaign.LIMITS=LIMITS
    campaign.COMMON_CAP=640
    campaign.ARM_BUFFER=16
    campaign.SOURCE_REVIEW_GROUP_MINIMUM=2


def main():
    actions={'sources':sources,'qualify':qualification,'rehearse':rehearse,'migrate':migrate}
    require(len(sys.argv)==2 and sys.argv[1] in actions,'Unknown reviewed reopening action')
    print(json.dumps(actions[sys.argv[1]](),indent=2))


if __name__=='__main__': main()
