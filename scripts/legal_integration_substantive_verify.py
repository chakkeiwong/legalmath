#!/usr/bin/env python3
"""Verify the additive local continuation without promoting legal completion."""
from pathlib import Path
import json

from scripts.legal_integration_master import ROOT, BASE, PROGRAM, STATE, MasterExecution
from scripts.legal_mission_execution import read, ref, verify, require, digest, save

WORK = BASE / 'substantive-continuation'
NODES = ('ownership-2023','ownership-2025','ownership-handbook','account-p10',
         'account-p14','account-evidence','account-gatecoin','graph-p14',
         'graph-gatecoin','current-binding','continuation-review')


def check():
    program=read(ROOT/PROGRAM)
    revision=program['substantive_continuation_revision']
    correction=revision.get('post_review')
    if correction and (ROOT/WORK/'post-review/finalization/review.md').exists():
        from scripts.legal_integration_post_review import finalize
        finalize()
        program=read(ROOT/PROGRAM)
        revision=program['substantive_continuation_revision']
        correction=revision['post_review']
    baseline=read(ROOT/revision['baseline']['path'])
    for key in ('prior_program','prior_state','prior_mission'):
        verify(ROOT,baseline[key])
    old_program=read(ROOT/baseline['prior_program']['path'])
    old_state=read(ROOT/baseline['prior_state']['path'])
    state=read(ROOT/STATE)
    require(old_state['program_hash']==digest(old_program),'Baseline state changed')
    require(program['deadline_utc']==old_program['deadline_utc']
            and program['global_call_ceiling']==old_program['global_call_ceiling'],
            'Resource ceilings changed')
    require(set(state['tasks'])==set(old_state['tasks'])|set(NODES),'Task population changed')
    for tid,row in old_state['tasks'].items():
        require(state['tasks'][tid]==row,'Historical task outcome changed: '+tid)
    if correction:
        from scripts.legal_integration_post_review import WORK as CORRECTION, REPAIRED
        prior=read(ROOT/correction['prior_state']['path'])
        for tid,row in prior['tasks'].items():
            require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'],
                    'First continuation attempt changed: '+tid)
        require(all(len(state['tasks'][tid]['attempts'])==2 for tid in REPAIRED),
                'Correction was not charged to existing attempts')
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    require(not view['ready'] and not view['running'],'Unexecuted ready local work remains')
    outcomes={tid:state['tasks'][tid]['status'] for tid in NODES}
    require(all(outcomes[tid]=='BLOCKED' for tid in NODES[:3]),'Source qualification status changed')
    require(all(outcomes[tid]=='SUCCEEDED' for tid in NODES[3:]),'Local follow-up failed')
    def evidence(tid):
        path=ROOT/BASE/tid/('attempt-'+str(len(state['tasks'][tid]['attempts'])))/'evidence.json'
        require(path.is_file(),'Missing result: '+tid)
        return read(path)
    g2025=read(ROOT/evidence('ownership-2025')['answer_relevant']['path'])
    annex=next(r for r in g2025['passages'] if r['passage']=='annexure-issue1')
    require(annex['locator']=='Annexure Issue 1 §1.1'
            and annex['excluded_from_main_paragraph']=='P100'
            and annex['rendered_label_verified'], 'Annexure misattributed')
    hb=read(ROOT/evidence('ownership-handbook')['answer_relevant']['path'])
    require('register of holders' in hb['distinct_6_8_sources']['code_on_unit_trusts']['source_text']
            and 'Product Key Facts Statements' in hb['distinct_6_8_sources']['general_handbook']['source_text'],
            'Two distinct 6.8 clauses conflated')
    graph={}
    for q in ('p14','gatecoin'):
        target=read(ROOT/evidence('graph-'+q)['targets']['path'])
        graph[q]={}
        require(target['answer_effect_evaluated'] is False,'Native pass promoted to answer effect')
        for case,row in target['executions'].items():
            statuses=[v['status'] for v in row['native']['results']]
            require(statuses==['PASS','PASS','PASS'],'Native adapter did not pass all controls')
            require(row['evaluation']['legal_premises_verified'] is False,'Graph claimed legal verification')
            if correction:
                require(row['evaluation']['semantics']['grounded']==row['expected_grounded'],
                        'Declared graph result differs')
            graph[q][case]=statuses
    if correction:
        from scripts.legal_integration_accounts import source_quote, SOURCE
        envelope=read(ROOT/SOURCE)
        for q in ('p10','p14','evidence','gatecoin'):
            account=read(ROOT/evidence('account-'+q)['account']['path'])
            require(account['original_inventory_fulfilled'] is False and account['actual_product_answer'] is False,
                    'Conditional account promoted to original answer fulfillment')
            for item in account['sources'].values():
                matched=source_quote(envelope,item['quote'],unit_id=item['unit_id'])
                require(all(item[k]==matched[k] for k in matched), 'Changed account quotation')
        target=read(ROOT/evidence('graph-gatecoin')['targets']['path'])
        adverse=target['executions']['ADVERSE']['proposal']
        require(adverse['attacks'][0]['kind']=='UNDERCUT' and
                not any(a['conclusion']=={'atom':'ncc','negative':True} for a in adverse['arguments']),
                'Defeating NCC default incorrectly proved non-NCC')
        require(not any('7th scenario' in c['quote'] for a in adverse['arguments'] for c in a['evidence']),
                'Scenario seven substituted as contrary-access warrant')
    binding=evidence('current-binding')
    require(binding['provider_binding']==('PROPOSAL_ONLY' if correction else 'ABSENT') and binding['live_dispatch']=='VETOED',
            'Unqualified live binding promoted')
    if correction:
        from scripts.legal_integration_post_review import approval_packet
        proposal=approval_packet()
        # Old evidence binds the retained bytes, not the edited current file.
        archived=read(ROOT/CORRECTION/'baseline.json')['archived']
        old_binding=read(ROOT/BASE/'current-binding/attempt-1/evidence.json')
        old_code=next(r for r in archived if r['previous']==old_binding['code'])
        verify(ROOT,old_code['archive']);verify(ROOT,old_binding['source'])
    else:
        verify(ROOT,binding['code']);verify(ROOT,binding['source'])
    report={'profile':'legal-substantive-continuation-verification.v1',
        'program':ref(ROOT,PROGRAM),'state':ref(ROOT,STATE),'plan':revision['plan'],
        'prior_program':baseline['prior_program'],'prior_state':baseline['prior_state'],
        'old_nodes_unchanged':len(old_state['tasks']), 'new_outcomes':outcomes,
        'annexure_locator':annex['locator'],'false_interval_rejected':annex['excluded_from_main_paragraph'],
        'distinct_code_6_8':True,'native_controls':graph,
        'master_execution':view['execution'],'ready':view['ready'],'running':view['running'],
        'original_answers_accepted':False,'matched_tool_effects':0,
        'live_provider_binding':binding['provider_binding'],'live_calls_added':0}
    if correction:
        report.update(first_attempts_preserved=True,correction_attempts=len(REPAIRED),
            detours=24,proposal=proposal['proposal'],remaining_calls=proposal['remaining_calls'],
            full_worst_case_demand=proposal['all_branch_maximum'],blockers=proposal['blockers'])
    save(ROOT/(CORRECTION if correction else WORK)/'verification.json',report)
    return report


if __name__=='__main__':
    value=check()
    print(json.dumps({k:value[k] for k in ('master_execution','old_nodes_unchanged',
        'new_outcomes','annexure_locator','matched_tool_effects','live_provider_binding')},indent=2))
