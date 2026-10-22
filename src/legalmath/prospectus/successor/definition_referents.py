"""Registered, occurrence-specific referents with conditional source support."""
from copy import deepcopy
import json
from pathlib import Path
from .anchors import fields
from .contracts import digest
from .definition_applications import require
from .definition_bindings import _checked_report
from .definition_contexts import _meaning

VERSION='definition-referent-review.v1'
KEY='definition_referent_review'
SPEC_SHA256 = 'e59853af8b53e33597b81f998f931738c23ce7540629fa3cd682957de490ec5f'
KINDS={'BOUND_REFERENT','CONDITIONAL_REFERENT','HEADING_MENTION','NAME_COMPONENT',
       'GENERIC_SECURITY_CLASS','OTHER_CREDITORS'}
RECORDS={'D01-notes','D02-issuer','D12-holder'}

def specification():
    spec=json.loads(Path(__file__).with_name('definition_referents_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec)==SPEC_SHA256,'Registered referent specification changed')
    return spec

def _decision(row,record,intervals,text,nodes):
    require(row['record']==record['id'] and row['record'] in RECORDS,'Wrong referent record')
    require(row['declarations']==[intervals[i] for i in record['declarations']],
            'Definition declaration identity changed')
    for declaration in row['declarations']:
        require(text[declaration['start']:declaration['end']]==declaration['quote'],'Declaration differs from source')
    _meaning(row['meaning'],nodes)
    require(row['support'],'Complete supporting source required')
    for span in row['support']:
        require(type(span['start']) is int and type(span['end']) is int
                and 0<=span['start']<span['end']<=len(text)
                and text[span['start']:span['end']]==span['quote'],'Supporting source differs')
    require([u['interval'] for u in row['uses']]==[u['interval'] for u in record['uses']],
            'Original use missing, duplicated or reordered')
    for use in row['uses']:
        interval=intervals[use['interval']]
        require(all(use[k]==interval[k] for k in ('start','end','quote','source_piece_indices')),
                'Occurrence identity or provenance differs')
        a,b=use['start'],use['end'];context=use['context']
        require(type(context['start']) is int and type(context['end']) is int
                and 0<=context['start']<=a<b<=context['end']<=len(text)
                and text[context['start']:context['end']]==context['quote']
                and text[a:b]==use['quote'],'Occurrence context differs')
        require(use['kind'] in KINDS and all(isinstance(use[k],str) and use[k].strip()
                for k in ('referent','reason','qualification')),'Missing qualified source decision')

def project(report,prior,decisions,text,nodes):
    selected={r['record']:r for r in decisions}
    require(len(selected)==len(decisions)==3 and set(selected)==RECORDS,'Referent record set changed')
    originals={r['id']:r for r in report['records']}
    for row in decisions:_decision(row,originals[row['record']],report['intervals'],text,nodes)
    uses=[]
    for old in prior['uses']:
        current={**deepcopy(old),'prior_referent_disposition':old['disposition'],'referent_binding':None}
        row=selected.get(old['record'])
        if row is not None:
            matches=[u for u in row['uses'] if (u['interval'],u['start'],u['end'])
                     ==(old['interval'],old['start'],old['end'])]
            require(old['origin']=='ORIGINAL' and len(matches)==1 and old['disposition']=='UNRECONCILED'
                    and old['binding'] is None and old['context_binding'] is None,'Prior decision would be overwritten')
            item=matches[0];require(item['quote']==old['quote'],'Use quotation differs')
            binding={k:deepcopy(row[k]) for k in ('record','declarations','meaning','support')}
            binding.update({k:deepcopy(item[k]) for k in ('context','source_piece_indices','kind','referent','reason','qualification')})
            current.update(referent_binding=binding,disposition=item['kind'],
                remaining=['SOURCE_READING_IS_CONDITIONAL;ACTUAL_FACTS_AND_HISTORICAL_LAW_OPEN'])
        uses.append(current)
    records=[{**deepcopy(r),'referent_reviewed':r['id'] in selected,
        'referent_use_indices':list(r['use_indices']) if r['id'] in selected else []} for r in prior['records']]
    require(len(uses)==612 and len(records)==62,'Complete association denominator changed')
    for record in records:
        require(record['referent_use_indices']==[i for i,u in enumerate(uses)
                if u['record']==record['id'] and u['referent_binding'] is not None],'Record/use linkage differs')
    require(sum(len(r['uses']) for r in decisions)==276,'Referent association count differs')
    return {'records':records,'uses':uses,'reviewed_records':3,'reviewed_associations':276,
            'original_associations':610,'supplemental_associations':2}

def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','specification_sha256','whole_task_complete','legal_truth_established'}
    fields(profile,keys,keys);spec=specification()
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256
        and profile['specification_sha256']==SPEC_SHA256
        and profile['products_sha256']==digest(products)==spec['products_sha256']
        and profile['ordinary_answer_sha256']==digest(ordinary)==spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False
        and profile['legal_truth_established'] is False,'Pinned referent source or prior answer differs')
    report,text=_checked_report(products,ordinary)
    nodes={n['id']:n for n in products['P3']['payload']['clauses']['nodes']}
    prior=ordinary['definition_context_review'];content=project(report,prior,spec['decisions'],text,nodes)
    require(digest(content)==spec['expected_content_sha256'],'Registered referent content differs')
    return {KEY:{'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'definition_report_sha256':digest(report),
        'prior_context_report_sha256':digest(prior),**content,'question_links':deepcopy(prior['question_links']),
        'assistance':'EXACT_OCCURRENCE_SUPPLIED_SOURCE_REVIEW','prior_answer_preserved':True,
        'all_governing_uses_established':False,'actual_facts_established':False,
        'historical_law_established':False,'automatic_legal_interpretation':False,'whole_task_complete':False}}

def verify_answer(actual,ordinary,profile,products,root,*,expected_profile_sha256):
    result={**ordinary,**evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)}
    result['report_sha256']=digest({k:v for k,v in result.items() if k!='report_sha256'})
    require(actual==result,'Complete answer differs from referent reconstruction')
    return {'status':'PASS','whole_answer_equal':True,'legal_truth_established':False}
