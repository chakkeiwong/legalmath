"""Predict finite source-role changes without invoking candidate inference."""
from collections import Counter
from copy import deepcopy
from scripts import prospectus_structural_candidate as c
from scripts.prospectus_typed_delta import changes,apply
from legalmath.prospectus.successor.contracts import digest


def seal(stage,bundle,inputs,payload):
    body={'version':'prospectus-product.v3','stage':stage,'bundle_sha256':digest(bundle),'inputs':inputs,'payload':payload}
    return {**body,'sha256':digest(body)}


def baseline():
    p=c.read(c.BASE/'complete-products.json.gz');a=c.read(c.BASE/'complete-expected-answer.json.gz')
    identity=c.read(c.BASE/'complete-inputs.json')
    assert digest(p)==identity['products_sha256'] and digest(a)==identity['answer_sha256']
    return p,a


def expected():
    base,old_answer=baseline();p=deepcopy(base);answer=deepcopy(old_answer)
    spec=c.read(c.PREP/'candidate/structural_roles_spec.json');manifest=c.read(c.PREP/'candidate-manifest.json')
    marker={'profile':spec['profile'],'profile_sha256':digest(spec)}
    ids={r['unit'] for r in spec['decisions']}
    assembly=p['P2']['payload']['assembly'];units={u['unit']:u for u in assembly['units']}
    for row in spec['decisions']:
        assert units[row['unit']]==row['before']
        units[row['unit']].update(role='HEADER',reason=row['reason'])
    assembly['unresolved']=[u['unit'] for u in assembly['units'] if u['role']=='UNKNOWN']
    assert digest(assembly)==spec['migrated_body_sha256']
    assembly['structural_role_review']=marker
    assert digest(assembly)==manifest['assembly_sha256']
    semantic=p['P3']['payload'];clauses=semantic['clauses'];removed_nodes=set();mixed=[]
    kept=[]
    for n in clauses['nodes']:
        if not ids.intersection(n['units']):kept.append(n);continue
        assert n['effect']=='unknown'
        spans=[s for s in n['spans'] if s['unit'] not in ids]
        if not spans:removed_nodes.add(n['id']);continue
        n.update(spans=spans,units=list(dict.fromkeys(s['unit'] for s in spans)),
            quote=' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in spans))
        kept.append(n);mixed.append(n['id'])
    assert len(removed_nodes)==14 and len(mixed)==5
    assert all(e['from'] not in removed_nodes and e['to'] not in removed_nodes for e in clauses['edges'])
    clauses.update(nodes=kept,assembly_sha256=digest(assembly),
        uncovered_units=[u for u in clauses['uncovered_units'] if u not in ids])
    request=p['P1']['payload']['request'];request['structural_roles']=marker;request['clauses']=deepcopy(kept)
    for packet in (request['reference_admission'],semantic['interpretation_input']['reference_admission']):
        packet.update(version='reviewed-references.v4',assembly_sha256=digest(assembly),structural_role_review=marker)
    definitions={}
    for kind in ('scopes','applications'):
        value=c.read(c.ROOT/c.PREFIX/('definition_'+kind+'_spec.json.gz'))
        assert digest(value)==spec['definition_profiles'][kind]
        value['bindings']['assembly_sha256']=digest(assembly);value['profile']+='.structural-v1'
        definitions[kind]={'profile':value['profile'],'profile_sha256':digest(value)}
    semantic['interpretation_input']['definition_sources']={**definitions['scopes'],'applications':definitions['applications']}
    report=semantic['definition_sources'];report.update(definitions['scopes']);report['bindings']['assembly_sha256']=digest(assembly)
    app=report['application_supplement'];app.update(definitions['applications']);app['bindings']['assembly_sha256']=digest(assembly)
    dependencies=[];removed_deps=set();resolved=set();structural_count=0
    for d in semantic['dependencies']:
        if d.get('source_use',{}).get('unit') in ids:
            assert not d['targets'] and d['status']=='UNRESOLVED' and not d['id'].startswith('reviewed-reference:')
            removed_deps.add(d['id']);continue
        if d['id'].startswith('definition-source:'):d['profile_sha256']=definitions['scopes']['profile_sha256']
        context=[t for t in d.get('targets',[]) if t['unit'] in ids]
        if context:
            assert d['id'].startswith('reviewed-reference:') and d['status']=='UNRESOLVED'
            assert set(d['unknown_target_uses'])<=ids
            d['targets']=[t for t in d['targets'] if t['unit'] not in ids]
            assert d['targets']
            d.update(structural_targets=context,structural_role_review=marker,status='RESOLVED')
            d.pop('unknown_target_uses');d.pop('source_binding');resolved.add(d['id']);structural_count+=len(context)
        dependencies.append(d)
    assert len(removed_deps)==12 and len(resolved)==4 and structural_count==18
    for d in dependencies:
        if not d['id'].startswith('reference-closure:'):continue
        for key in ('roots','reachable'):d[key]=[u for u in d[key] if u not in ids]
        excluded={'Unresolved reference: '+v for v in removed_deps|resolved}
        assert excluded<=set(d['unresolved'])
        d['unresolved']=[u for u in d['unresolved'] if u not in excluded]
    semantic['dependencies']=dependencies
    removed=ids|removed_nodes|removed_deps|resolved
    for q in ('Q1','Q2'):
        for value in [semantic['questions'][q],*semantic['questions'][q].get('subquestions',{}).values()]:
            assert removed<=set(value['unresolved'])
            value['unresolved']=[u for u in value['unresolved'] if u not in removed]
        semantic['questions']['Q3']['value'][q]['unresolved']=deepcopy(semantic['questions'][q]['unresolved'])
        answer['questions'][q]=deepcopy(semantic['questions'][q])
        answer['questions']['Q3']['value'][q]['unresolved']=deepcopy(semantic['questions'][q]['unresolved'])
    assert len(removed)==74
    for key in ('substitution_references','financial_references','internal_references'):
        r=answer[key];targets={t['use'] for row in r['references'] for t in row['targets']}
        r['unknown_target_uses']=[u for u in r['unknown_target_uses'] if u not in ids]
        r.update(structural_target_uses=sorted(targets&ids),structural_role_review=marker)
    answer['definition_sources']=deepcopy(report)
    coverage=answer['meaning_coverage'];coverage.update(assembly_sha256=digest(assembly),clauses_sha256=digest(clauses))
    account={r['unit']:r['role'] for r in p['P2']['payload']['selected_contract']['unit_accounting']}
    totals=Counter();chars=Counter()
    for key in ids:
        totals[account[key]]+=1;chars[account[key]]+=sum(not ch.isspace() for ch in units[key]['text'])
    assert set(totals)=={'BODY_CANDIDATE'}
    summary=coverage['source_categories']['BODY_CANDIDATE'];summary['assembly_roles']['UNKNOWN']-=44
    summary['assembly_roles']['HEADER']=summary['assembly_roles'].get('HEADER',0)+44
    summary['assembly_roles']=dict(sorted(summary['assembly_roles'].items()))
    summary['active_characters']['nonspace']-=chars['BODY_CANDIDATE']
    summary['active_characters']['unknown_only']-=chars['BODY_CANDIDATE']
    # Mixed-node residuals retain their exact intervals; only complete HEADER units disappear.
    coverage['selected_body_pending']=[u for u in coverage['selected_body_pending'] if u['unit'] not in ids]
    assert all(not ids.intersection(u['unit'] for u in g['unresolved_body_meanings']) for g in answer['printed_margin_review']['groups'])
    bundle=request['bundle']
    p['P1']=seal('P1',bundle,{'request':digest(request)},p['P1']['payload'])
    p['P2']=seal('P2',bundle,{'P1':p['P1']['sha256']},p['P2']['payload'])
    p['P3']=seal('P3',bundle,{'P1':p['P1']['sha256'],'P2':p['P2']['sha256']},semantic)
    p['P4']=seal('P4',bundle,{'P1':p['P1']['sha256'],'P3':p['P3']['sha256']},p['P4']['payload'])
    p['P5']=seal('P5',bundle,{'P2':p['P2']['sha256'],'P3':p['P3']['sha256']},p['P5']['payload'])
    answer.update(request_sha256=digest(request),consumed_products={k:v['sha256'] for k,v in p.items()})
    answer['report_sha256']=digest({k:v for k,v in answer.items() if k!='report_sha256'})
    summary={'structural_units':44,'removed_nodes':sorted(removed_nodes),'mixed_nodes':mixed,
        'removed_dependencies':sorted(removed_deps),'resolved_source_links':sorted(resolved),
        'structural_targets_retained':structural_count,'removed_uncertainty_ids':sorted(removed),
        'question_unresolved':{q:len(semantic['questions'][q]['unresolved']) for q in ('Q1','Q2')},
        'candidate_services_invoked':False,'legal_meaning_established':False}
    return p,answer,summary


def prepare():
    base,old=baseline();p,a,summary=expected()
    c.save(c.PREP/'expected.json.gz',{'base':c.rel(c.BASE),'products_delta':changes(base,p),'answer_delta':changes(old,a),
        'products_sha256':digest(p),'answer_sha256':digest(a),'summary':summary})
    c.save(c.PREP/'prediction.json',summary)
    return {'status':'PASS','products_sha256':digest(p),'answer_sha256':digest(a),'unresolved':summary['question_unresolved']}


def retained():
    p,a=baseline();saved=c.read(c.PREP/'expected.json.gz')
    p,a=apply(p,saved['products_delta']),apply(a,saved['answer_delta'])
    assert digest(p)==saved['products_sha256'] and digest(a)==saved['answer_sha256']
    return p,a
