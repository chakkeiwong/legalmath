"""Finite supplied source readings with explicit ambiguity and missing definitions."""
from copy import deepcopy
import json
from pathlib import Path
from .anchors import fields
from .contracts import digest
from .definition_applications import require
from .definition_bindings import _checked_report

VERSION='definition-remainder-review.v1'
KEY='definition_remainder_review'
SPEC_SHA256 = 'da05ac44828cdcef07481d4bb8aa593a2c11ac1d78fdc105d5abf031fdbcc59a'
KINDS={'SCOPED_SOURCE_READING','HEADING_MENTION','NAME_COMPONENT','SCOPE_AMBIGUITY',
       'GENERIC_DUE_DATE','OTHER_DEFINITION_COMPONENT','CONDITIONAL_ROLE',
       'TABLE_COLUMN','ROLE_LABEL','MISSING_DEFINITION'}

def specification():
    spec=json.loads(Path(__file__).with_name('definition_remainders_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec)==SPEC_SHA256,'Registered remainder specification changed')
    return spec

def _span(span,text):
    require(type(span['start']) is int and type(span['end']) is int
        and 0<=span['start']<span['end']<=len(text)
        and text[span['start']:span['end']]==span['quote'],'Source span differs')

def _decision(row,record,intervals,text,nodes):
    require(row['record']==record['id'],'Wrong remainder record')
    require(row['declarations']==[intervals[i] for i in record['declarations']],
        'Definition declaration identity changed')
    for declaration in row['declarations']:_span(declaration,text)
    require(isinstance(row['reading'],str) and row['reading'].strip()
        and isinstance(row['open_issues'],list) and row['open_issues']
        and all(isinstance(x,str) and x.strip() for x in row['open_issues']),
        'Qualified supplied reading required')
    require(isinstance(row['source_evidence'],list) and row['source_evidence'],'Full source evidence required')
    ids=[v['node'] for v in row['source_evidence']]
    require(len(ids)==len(set(ids)),'Duplicate source evidence')
    for retained in row['source_evidence']:
        node=nodes.get(retained['node'])
        require(node is not None and retained['evidence']==node and retained['node_sha256']==digest(node)
            and node.get('id')==retained['node'] and node.get('role')=='OPERATIVE'
            and node.get('quote') and node.get('spans')
            and any(k.endswith('_reading') and isinstance(v,(str,dict)) and bool(v) for k,v in node.items()),
            'Full source node, reading, provenance or authority differs')
    for span in row['support']:_span(span,text)
    require([u['interval'] for u in row['uses']]==[u['interval'] for u in record['uses']],
        'Original use missing, duplicated or reordered')
    for use in row['uses']:
        interval=intervals[use['interval']]
        require(all(use[k]==interval[k] for k in ('start','end','quote','source_piece_indices')),
            'Occurrence identity or provenance differs')
        _span(use,text);_span(use['context'],text)
        require(use['context']['start']<=use['start']<use['end']<=use['context']['end'],
            'Occurrence outside source context')
        require(use['kind'] in KINDS and isinstance(use['reason'],str) and use['reason'].strip()
            and use['open_issues']==row['open_issues'],'Missing qualified source decision')

def project(report,prior,decisions,text,nodes):
    selected={r['record']:(i,r) for i,r in enumerate(decisions)}
    unresolved={u['record'] for u in prior['uses'] if u['disposition']=='UNRECONCILED'}
    require(len(selected)==len(decisions)==44 and set(selected)==unresolved,'Remainder record set changed')
    originals={r['id']:r for r in report['records']}
    for row in decisions:_decision(row,originals[row['record']],report['intervals'],text,nodes)
    uses=[]
    for old in prior['uses']:
        current={**deepcopy(old),'prior_remainder_disposition':old['disposition'],'remainder_binding':None}
        pair=selected.get(old['record'])
        if pair is not None:
            row_index,row=pair
            matches=[u for u in row['uses'] if (u['interval'],u['start'],u['end'])
                ==(old['interval'],old['start'],old['end'])]
            require(old['origin']=='ORIGINAL' and len(matches)==1 and old['disposition']=='UNRECONCILED'
                and all(old.get(k) is None for k in ('binding','context_binding','referent_binding')),
                'Prior decision would be overwritten')
            item=matches[0];require(item['quote']==old['quote'],'Use quotation differs')
            binding={'source_record_index':row_index,'record':row['record'],
                **{k:deepcopy(item[k]) for k in ('context','source_piece_indices','kind','reason','open_issues')}}
            current.update(remainder_binding=binding,disposition=item['kind'],remaining=deepcopy(item['open_issues']))
        uses.append(current)
    records=[{**deepcopy(r),'remainder_reviewed':r['id'] in selected,
        'remainder_use_indices':list(r['use_indices']) if r['id'] in selected else []} for r in prior['records']]
    require(len(uses)==612 and len(records)==62,'Complete association denominator changed')
    for record in records:
        require(record['remainder_use_indices']==[i for i,u in enumerate(uses)
            if u['record']==record['id'] and u['remainder_binding'] is not None],'Record/use linkage differs')
    require(sum(len(r['uses']) for r in decisions)==231,'Remainder association count differs')
    return {'records':records,'uses':uses,'source_records':deepcopy(decisions),
        'reviewed_records':44,'reviewed_associations':231,'original_associations':610,'supplemental_associations':2}

def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','specification_sha256','whole_task_complete','legal_truth_established'}
    fields(profile,keys,keys);spec=specification()
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256
        and profile['specification_sha256']==SPEC_SHA256
        and profile['products_sha256']==digest(products)==spec['products_sha256']
        and profile['ordinary_answer_sha256']==digest(ordinary)==spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False
        and profile['legal_truth_established'] is False,'Pinned remainder source or prior answer differs')
    report,text=_checked_report(products,ordinary)
    nodes={n['id']:n for n in products['P3']['payload']['clauses']['nodes']}
    prior=ordinary['definition_referent_review'];content=project(report,prior,spec['decisions'],text,nodes)
    require(digest(content)==spec['expected_content_sha256'],'Registered remainder content differs')
    return {KEY:{'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'definition_report_sha256':digest(report),
        'prior_referent_report_sha256':digest(prior),**content,'question_links':deepcopy(prior['question_links']),
        'assistance':'EXACT_OCCURRENCE_SUPPLIED_SOURCE_REVIEW','prior_answer_preserved':True,
        'all_governing_uses_established':False,'actual_facts_established':False,
        'historical_law_established':False,'automatic_legal_interpretation':False,'whole_task_complete':False}}

def verify_answer(actual,ordinary,profile,products,root,*,expected_profile_sha256):
    result={**ordinary,**evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)}
    result['report_sha256']=digest({k:v for k,v in result.items() if k!='report_sha256'})
    require(actual==result,'Complete answer differs from remainder reconstruction')
    return {'status':'PASS','whole_answer_equal':True,'legal_truth_established':False}
