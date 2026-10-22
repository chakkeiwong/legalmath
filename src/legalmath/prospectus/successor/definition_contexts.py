"""Finite source-reviewed context links; never a global lexical dictionary."""
from copy import deepcopy
import json
from pathlib import Path

from .anchors import fields
from .contracts import digest
from .definition_applications import require
from .definition_bindings import _checked_report

VERSION = 'definition-context-review.v1'
KEY = 'definition_context_review'
SPEC_SHA256 = '6e4cb558d1db4eb03767f2109f2f9a2755309b5249c7dc73652eb2a268d6a975'


def specification():
    spec = json.loads(Path(__file__).with_name('definition_contexts_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec) == SPEC_SHA256, 'Registered context specification changed')
    return spec


def _meaning(item, nodes):
    keys = {'node','node_sha256','field','reading','quote','spans'}
    fields(item, keys, keys)
    node = nodes.get(item['node'])
    require(node is not None and node['role'] == 'OPERATIVE' and digest(node) == item['node_sha256']
            and node['quote'] == item['quote'] and node['spans'] == item['spans']
            and node.get(item['field']) == item['reading'], 'Meaning differs from exact source clause')
    require(isinstance(item['reading'],dict) and isinstance(item['reading'].get('qualification'),str)
            and item['reading']['qualification'], 'Complete qualified source reading required')


def _decision(row, record, intervals, text, nodes):
    require(row['record'] == record['id'] and isinstance(row['reason'],str) and row['reason'],
            'Context decision has no source reason or record identity')
    require(row['declarations'] == [intervals[i] for i in record['declarations']],
            'Definition declaration identities changed')
    for declaration in row['declarations']:
        require(text[declaration['start']:declaration['end']] == declaration['quote'], 'Declaration quotation changed')
    _meaning(row['meaning'], nodes)
    for item in row['extra_meanings']:
        _meaning(item, nodes)
    expected_indices = [u['interval'] for u in record['uses']]
    require([u['interval'] for u in row['uses']] == expected_indices, 'Context decision omits, duplicates or reorders an original use')
    for use in row['uses']:
        interval = intervals[use['interval']]
        require(all(use[k] == interval[k] for k in ('start','end','quote','source_piece_indices')),
                'Context use differs from original interval/provenance')
        a,b = use['start'],use['end']
        context = use['context']
        require(type(context['start']) is int and type(context['end']) is int
                and 0 <= context['start'] <= a < b <= context['end'] <= len(text)
                and text[context['start']:context['end']] == context['quote']
                and text[a:b] == use['quote'], 'Context does not contain exact source use')
        require(use['kind'] in {'BOUND_CONTEXTUALLY','HEADING_MENTION','NAME_COMPONENT'}, 'Unknown context use kind')
        if row['record'].startswith('D10-'):
            number = {'ICSD':'EACH_OR_RELEVANT_ICSD','ICSDs':'BOTH_ICSDS'}.get(use['quote'])
            require(number is not None and use['number'] == number, 'ICSD each/both distinction changed')
        else:
            require(use['number'] is None, 'Plurality supplied for an unsupported definition')


def project(report, prior, decisions, text, nodes):
    ids = [r['record'] for r in decisions]
    require(len(ids) == len(set(ids)) and len(ids) == 10, 'Duplicate or missing context records')
    records_by_id = {r['id']:r for r in report['records']}
    require(set(ids) <= set(records_by_id), 'Unknown context definition')
    selected = {}
    for row in decisions:
        _decision(row, records_by_id[row['record']], report['intervals'], text, nodes)
        selected[row['record']] = row
    uses = []
    for old in prior['uses']:
        current = {**deepcopy(old), 'prior_disposition':old['disposition'], 'context_binding':None}
        row = selected.get(old['record'])
        if row is not None:
            matches = [u for u in row['uses'] if u['interval'] == old['interval']]
            require(old['origin']=='ORIGINAL' and len(matches)==1, 'Context use association not uniquely reviewed')
            use = matches[0]
            require(all(old[k]==use[k] for k in ('start','end','quote'))
                    and old['disposition']=='UNRECONCILED' and old['binding'] is None,
                    'Context review would overwrite a prior purpose decision')
            binding = {k:deepcopy(row[k]) for k in ('record','concept','reason','declarations','meaning','extra_meanings')}
            binding.update({k:deepcopy(use[k]) for k in ('context','source_piece_indices','number','kind')})
            current.update(context_binding=binding, disposition=use['kind'],
                remaining=['ACTUAL_FACTS_NOT_ESTABLISHED'] if use['kind']=='BOUND_CONTEXTUALLY' else ['MENTION_IS_NOT_AN_OPERATIVE_USE'])
        uses.append(current)
    records = [{**deepcopy(r), 'context_reviewed':r['id'] in selected,
        'context_use_indices':list(r['use_indices']) if r['id'] in selected else []} for r in prior['records']]
    require(len(uses)==612 and len(records)==62, 'Complete definition association denominator changed')
    for record in records:
        require(record['context_use_indices']==[i for i,u in enumerate(uses) if u['record']==record['id'] and u['context_binding'] is not None],
                'Context record/use linkage changed')
    return {'records':records,'uses':uses,'reviewed_records':len(decisions),
        'reviewed_associations':sum(len(r['uses']) for r in decisions),
        'original_associations':610,'supplemental_associations':2}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','specification_sha256','whole_task_complete','legal_truth_established'}
    fields(profile,keys,keys)
    spec=specification()
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256
            and profile['specification_sha256']==SPEC_SHA256
            and profile['products_sha256']==digest(products)==spec['products_sha256']
            and profile['ordinary_answer_sha256']==digest(ordinary)==spec['ordinary_answer_sha256']
            and ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
            and KEY not in ordinary and profile['whole_task_complete'] is False
            and profile['legal_truth_established'] is False, 'Pinned context source or prior answer changed')
    report,text=_checked_report(products,ordinary)
    nodes={n['id']:n for n in products['P3']['payload']['clauses']['nodes']}
    prior=ordinary['definition_use_bindings']
    content=project(report,prior,spec['decisions'],text,nodes)
    require(digest(content)==spec['expected_content_sha256'], 'Complete registered context matrix changed')
    return {KEY:{'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'definition_report_sha256':digest(report),
        'prior_binding_report_sha256':digest(prior),**content,
        'question_links':deepcopy(prior['question_links']),
        'assistance':'EXACT_OCCURRENCE_SUPPLIED_SOURCE_REVIEW',
        'prior_answer_preserved':True,'all_governing_uses_established':False,
        'actual_facts_established':False,'historical_law_established':False,
        'automatic_legal_interpretation':False,'whole_task_complete':False}}


def verify_answer(actual,ordinary,profile,products,root,*,expected_profile_sha256):
    result={**ordinary,**evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)}
    result['report_sha256']=digest({k:v for k,v in result.items() if k!='report_sha256'})
    require(actual==result,'Complete answer differs from source-context reconstruction')
    return {'status':'PASS','whole_answer_equal':True,'legal_truth_established':False}
