"""Lossless, source-addressed audit of retained question uncertainty."""
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_definition_package as baseline_package
from scripts import prospectus_question_scope_audit as failed
prior=baseline_package
from legalmath.prospectus.execution_authority import Authority,CODE,digest as authority_digest
from legalmath.prospectus.successor.contracts import digest

AUTH=prior.AUTH
PREP=AUTH/'reviews/question-scope-provenance-292'
HERE=AUTH/'attempts/basf-references/attempt-033'
METHOD='scripts/prospectus_question_scope_repair.py'
PLAN='docs/plans/prospectus-question-scope-provenance-repair-2026-10-18.md'
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior_resources']['cumulative026_032_measured_seconds']+extra
    seconds+=read(PREP/'repair-preparation.json')['wall_seconds']
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (METHOD,PLAN,'scripts/prospectus_question_scope_repair_preparation.py'))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0292.json')
    size=start['prior_resources']['cumulative026_032_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<3600 and size<380*1024**2,'Cumulative question-audit resource bound'
    return {'cumulative026_033_measured_seconds':seconds,'cumulative026_033_bytes':size,
        'seconds_bound':3600,'bytes_bound_including_4MiB_reserve':384*1024**2,
        'prior_costs_reset':False,'historical_manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':start['prior_resources']['prior_unmeasured_preparation']}


def prepare():
    program=read(AUTH/'program.json')
    assert program['revision']==291
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==32 and any(e['kind'] in ('RECORD','REJECT') and e.get('attempt')==rel(failed.HERE) for e in events)
    assert read(prior.HERE/'result.json')['installed_complete_answer_equal']
    save(PREP/'accounting-start.json',{'prior_resources':failed.costs(),
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    bindings={n:sha(ROOT/n) for n in (*CODE,METHOD,PLAN,'pyproject.toml',
        'src/legalmath/prospectus/successor/clause_graph.py',
        'src/legalmath/prospectus/successor/service.py',
        'src/legalmath/prospectus/successor/reference_closure.py',
        'src/legalmath/prospectus/successor/occurrences.py',
        'scripts/prospectus_question_scope_repair_preparation.py')}
    bindings.update({rel(p):sha(p) for p in PREP.iterdir() if p.is_file()})
    for name in ('outputs.json','complete-products.json.gz','complete-expected-answer.json.gz','complete-inputs.json'):
        bindings[rel(prior.HERE/name)]=sha(prior.HERE/name)
    bindings[rel(failed.HERE/'outputs.json')]=sha(failed.HERE/'outputs.json')
    bindings[failed.METHOD]=sha(ROOT/failed.METHOD)
    save(PREP/'freeze.json',{'bindings':bindings,'production_changes':False,'answer_evaluation':False})
    proposal=deepcopy(program)
    proposal['revision']=292
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Trace every remaining question uncertainty to source roles, clauses and dependencies before selecting the next semantic repair',
        question_scope_audit={'review':rel(PREP),'baseline':rel(prior.HERE),'production_changes':False,
            'original_task_complete':False,'cumulative026_033_seconds':3600,
            'cumulative026_033_bytes_including_4MiB_reserve':384*1024**2})
    proposal['budgets']['basf-references']['maximum_new_attempts']=33
    routes=read(ROOT/program['continuation_review']['routes'])
    routes['baseline_revision']=292
    for row in routes['tasks']:
        if row['task']=='basf-references':
            row.update(dossier=PLAN,task_sha256=authority_digest(task),
                next_action='Reconcile all current uncertainty to actual sources, inspect examples and exceptional entries, then admit a source-reasoned semantic repair',
                stop_condition='33 admissions;180s stages;3600s cumulative026 onward;384MiB including4MiB reserve;no unchanged retries')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),
        rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    resource=costs()
    projected=resource['cumulative026_033_bytes']+3*(AUTH/'program.json').stat().st_size+12*1024**2
    assert projected<380*1024**2 and resource['cumulative026_033_measured_seconds']+120<3600
    review={'baseline':authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Lossless investigation of original unanswered questions;no semantic filtering or production edits',
            'Admission32 to33;existing cumulative time unchanged;storage320 to384MiB includes failed audit and repair'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'projected_bytes':projected},
        'evidence_contract':{'primary':'Every retained unresolved identifier preserved with actual source/node/dependency pointers or explicit unmatched classification and source analysis',
            'promotion_veto':['Lost identifier','Invented provenance','Counts treated as correctness','Unsupported relevance exclusion'],
            'continuation_veto':['Corrupt baseline','Method drift','Missing source result','Exhausted limits'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Correctness of UNKNOWN','Legal completion','General recall']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':32,'new_maximum':33,
            'retained_attempts':attempts,'reason':'Failed audit used metadata instead of exact occurrence source anchors; changed mapper preserves source gaps',
            'next_discriminating_check':'Lossless uncertainty-to-source reconciliation and original-source reading',
            'stop_condition':'180s stages;3600s cumulative;384MiB including4MiB reserve;no unchanged retries',
            'same_scope_authorization':'User requested refreshed master and continued complete build'},
        'resource_revision':{'prior_seconds':3600,'new_seconds':3600,'prior_bytes':320*1024**2,
            'new_bytes':384*1024**2,'reserve_bytes':4*1024**2,'prior_costs_retained':True},
        'original_obligations_preserved':True,'production_changes':False}
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':292,'resources':costs(),'projected_bytes':projected}


def frozen():
    admission=read(HERE/'admission.json')
    assert authority_digest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,value in read(PREP/'freeze.json')['bindings'].items():
        assert sha(ROOT/name)==value,name
    for name,value in read(prior.HERE/'outputs.json').items():
        assert sha(prior.HERE/name)==value,name


def inventory():
    p=read(prior.HERE/'complete-products.json.gz')
    answer=read(prior.HERE/'complete-expected-answer.json.gz')
    identities=read(prior.HERE/'complete-inputs.json')
    assert digest(p)==identities['products_sha256'] and digest(answer)==identities['answer_sha256']
    graph=p['P1']['payload']['graph']
    assembly=p['P2']['payload']['assembly']
    semantic=p['P3']['payload']
    clauses=semantic['clauses']
    nodes={r['id']:(i,r) for i,r in enumerate(clauses['nodes'])}
    units={r['unit']:(i,r) for i,r in enumerate(assembly['units'])}
    raw={r['id']:(i,r) for i,r in enumerate(graph['units'])}
    deps={r['id']:(i,r) for i,r in enumerate(semantic['dependencies'])}
    assert len(nodes)==len(clauses['nodes']) and len(units)==len(assembly['units'])
    assert len(deps)==len(semantic['dependencies'])
    pieces=semantic['definition_sources']['source_pieces']
    selected={use['unit'] for piece in pieces for use in piece.get('assembly_uses',[])}
    missing=[{'piece_index':i,'piece':piece} for i,piece in enumerate(pieces)
             if piece['kind']=='EXACT_SOURCE_COPY' and not piece['assembly_uses']]
    from legalmath.prospectus.successor.occurrences import segments
    raw_by_id={k:v[1] for k,v in raw.items()}
    def source_segments(unit):
        matches=segments(graph,unit,_raw=raw_by_id)
        for segment in matches:
            anchor=segment['source']
            original=raw_by_id[anchor['unit']]
            assert (anchor['document'],anchor['source_sha256'])==(original['document'],original['source_sha256'])
            assert original['raw'][anchor['start']:anchor['end']]==anchor['quote']
            assert unit['text'][segment['start']:segment['end']]==anchor['quote']
        return matches
    uncovered=set(clauses['uncovered_units'])
    entries={}
    query_rows={}
    for question in ('Q1','Q2'):
        query_rows[question]=answer['questions'][question]['unresolved']
        for name,row in answer['questions'][question].get('subquestions',{}).items():
            query_rows[question+'/'+name]=row['unresolved']
    for query,identifiers in query_rows.items():
        assert identifiers==sorted(set(identifiers))
        q=query.split('/')[0]
        for identity in identifiers:
            row=entries.setdefault(identity,{'id':identity,'queries':[],'causes':[],'pointers':[],'assembly_units':[]})
            row['queries'].append(query)
            if len(row['queries'])>1:
                continue
            if identity in nodes:
                i,node=nodes[identity]
                row['pointers'].append(['P3','payload','clauses','nodes',i])
                row['assembly_units'].extend(node['units'])
                row['causes'].append('UNKNOWN_CLAUSE_EFFECT' if node['effect']=='unknown' else 'OTHER_CLAUSE')
            if identity in units:
                i,unit=units[identity]
                row['pointers'].append(['P2','payload','assembly','units',i])
                row['assembly_units'].append(identity)
                if unit['role']=='UNKNOWN':
                    row['causes'].append('UNKNOWN_ASSEMBLY_ROLE')
                if identity in uncovered:
                    row['causes'].append('UNCOVERED_ASSEMBLY_TEXT')
            if identity in deps:
                i,dependency=deps[identity]
                row['pointers'].append(['P3','payload','dependencies',i])
                row['causes'].append('UNRESOLVED_DEPENDENCY')
                assert dependency['status']!='RESOLVED'
                if isinstance(dependency.get('source_use'),dict):
                    value=dependency['source_use'].get('unit')
                    if value in units:
                        row['assembly_units'].append(value)
                if dependency.get('kind')=='DEFINITION_SOURCE':
                    rid=identity.removeprefix('definition-source:')
                    for j,record in enumerate(semantic['definition_sources']['records']):
                        if record['id']==rid:
                            row['pointers'].append(['P3','payload','definition_sources','records',j])
                            break
                    else:
                        raise ValueError('Missing original definition record')
                if dependency.get('kind')=='STATUTORY_REFERENCE':
                    row['causes'].append('STATUTORY_SOURCE_OR_APPLICATION')
            if identity=='Question scope not complete: '+q:
                row['causes'].append('DECLARED_INCOMPLETE_SCOPE')
                row['pointers'].append(['P3','payload','scope',q])
            prefixes=('Unresolved reference: ','Unsupported reference cycle: ','Missing reference target: ',
                      'Unsupported priority: ','Nested predicate activation requires admitted expression: ',
                      'Missing actor/affected interest: ','Missing conversion arguments: ')
            for prefix in prefixes:
                if identity.startswith(prefix):
                    target=identity.removeprefix(prefix)
                    if target in nodes:
                        i,node=nodes[target]
                        row['pointers'].append(['P3','payload','clauses','nodes',i])
                        row['assembly_units'].extend(node['units'])
                        row['causes'].append('CLAUSE_DIAGNOSTIC')
                    for j,edge in enumerate(clauses['edges']):
                        if target==edge.get('id') or target==str(edge.get('from'))+':'+str(edge.get('to')):
                            row['pointers'].append(['P3','payload','clauses','edges',j])
                            row['causes'].append('REFERENCE_CLOSURE_DIAGNOSTIC')
            if not row['causes']:
                row['causes'].append('UNMATCHED_REQUIRES_SOURCE_REVIEW')
            row['causes']=sorted(set(row['causes']))
            row['assembly_units']=sorted(set(row['assembly_units']))
            row['selected_source_units']=sorted(selected.intersection(row['assembly_units']))
            row['other_inventory_units']=sorted(set(row['assembly_units'])-selected)
            # Each pointer binds an actual retained object, not an inferred prefix.
            row['pointer_hashes']=[]
            for pointer in row['pointers']:
                value=p
                for key in pointer:
                    value=value[key]
                row['pointer_hashes'].append(digest(value))
    for query,identifiers in query_rows.items():
        assert sorted(k for k,r in entries.items() if query in r['queries'])==identifiers
    cause_counts=Counter(c for r in entries.values() for c in r['causes'])
    doc_counts=Counter()
    source_rows={}
    for row in entries.values():
        for unit_id in row['assembly_units']:
            if unit_id in source_rows:
                continue
            i,unit=units[unit_id]
            matches=source_segments(unit)
            anchors=[]
            covered=set()
            for segment in matches:
                j,original=raw[segment['source']['unit']]
                anchors.append({'raw_index':j,'raw_sha256':digest(original),**segment})
                covered.update(range(segment['start'],segment['end']))
            unmapped=[n for n,c in enumerate(unit['text']) if not c.isspace() and n not in covered]
            source_rows[unit_id]={'assembly_index':i,'assembly_sha256':digest(unit),'exact_segments':anchors,
                'document':unit['source']['document'],'page':unit['source']['page'],
                'role':unit['role'],'context':unit['context'],'questions':unit['questions'],
                'unmapped_nonspace_positions':unmapped,'selected_source_copy':unit_id in selected}
            doc_counts[(unit['source']['document'],unit['role'],unit_id in selected)]+=1
    samples={}
    for row in entries.values():
        for cause in row['causes']:
            key=cause+('/selected' if row['selected_source_units'] else '/other-or-no-unit')
            if key in samples:
                continue
            examples=[]
            for uid in row['assembly_units'][:2]:
                i,unit=units[uid]
                matches=source_segments(unit)
                originals=[raw[s['source']['unit']][1] for s in matches]
                examples.append({'unit':uid,'assembly':unit,'raw_sources':originals,
                                 'source_mapping':source_rows[uid]})
            samples[key]={'entry':row,'sources':examples}
    all_unmatched=[r for r in entries.values() if 'UNMATCHED_REQUIRES_SOURCE_REVIEW' in r['causes']]
    save(HERE/'uncertainty-index.json.gz',{'base_products':rel(prior.HERE/'complete-products.json.gz'),
        'base_products_sha256':digest(p),'base_answer_sha256':digest(answer),
        'original_queries':query_rows,'entries':list(entries.values()),'source_units':source_rows,
        'missing_selected_assembly_occurrences':missing,'no_identifiers_dropped':True,
        'source_relevance_decisions_made':False})
    save(HERE/'reading-samples.json.gz',samples)
    save(HERE/'unmatched.json.gz',all_unmatched)
    summary={'status':'PASS','query_counts':{k:len(v) for k,v in query_rows.items()},
        'unique_identifiers':len(entries),'cause_counts':dict(cause_counts),
        'documents':[{'document':k[0],'role':k[1],'selected_source_copy':k[2],'units':v}
                     for k,v in sorted(doc_counts.items())],
        'selected_unit_ids':len(selected),'missing_selected_assembly_pieces':len(missing),
        'source_units_with_unmapped_text':sum(bool(v['unmapped_nonspace_positions']) for v in source_rows.values()),
        'unmatched_identifiers':len(all_unmatched),'question_scope':semantic['scope'],
        'no_identifiers_dropped':True,'source_relevance_decisions_made':False,
        'original_task_complete':False}
    save(HERE/'summary.json',summary)
    return {k:v for k,v in summary.items() if k not in ('documents','question_scope')}


def seal():
    assert read(HERE/'stages/inventory/result.json')['status']=='PASS'
    review=read(HERE/'source-analysis.json')
    assert review['status']=='PASS' and review['original_identifiers_preserved']
    assert review['summary_sha256']==sha(HERE/'summary.json')
    assert review['unmatched_sha256']==sha(HERE/'unmatched.json.gz')
    assert review['next_plan'] and (ROOT/review['next_plan']).is_file()
    result={'status':'PASS','task':'basf-references','result_kind':'QUESTION_UNCERTAINTY_SOURCE_AUDIT',
        'original_task_complete':False,'summary':read(HERE/'summary.json'),
        'source_analysis':review,'resources':costs(),'next_action':review['next_action']}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in ('inventory','seal')],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden',
        'random_seeds':'N/A deterministic','data_version':sha(prior.HERE/'outputs.json'),
        'wall_time':result['resources'],'plan':PLAN,'result':rel(HERE/'result.json'),
        'source_analysis_time':'UNKNOWN manual reading;not counted as zero'})
    return {'status':'PASS','audit_complete':True,'original_task_complete':False,'resources':costs()}


def main():
    assert len(sys.argv)==2 and sys.argv[1] in ('prepare','inventory','seal')
    stage=sys.argv[1]
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged audit retry refused'
    if stage!='prepare':
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_question_scope_repair',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'stage_seconds':180})
    started=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Question scope audit stage bound')))
    signal.alarm(180)
    try:
        if stage!='prepare':
            frozen()
        result=globals()[stage]()
        if stage!='prepare':
            frozen()
        costs(time.monotonic()-started)
        result['wall_seconds']=time.monotonic()-started
        save(folder/'result.json',result)
        if stage=='seal':
            save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts})
        print(prior.prior.old.json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-started})
        raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    main()
