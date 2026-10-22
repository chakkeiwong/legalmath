"""Reviewed H1 heading associations and separate original-source checks."""
from copy import deepcopy
import json

from scripts.prospectus_h1_current_acceptance import read, require, BASE

VERSION = 'bes-h1-statement-context.v1'
LIMITS = {'supplied_source_specific_interpretation': True,
    'automatic_interpretation_established': False, 'source_authenticity_established': False,
    'intended_individual_unit_resolved': False, 'clipped_equity_restored': False,
    'incorporation_selected': False, 'financial_accuracy_established': False,
    'original_task_complete': False}
S = '/answer/source_statement_cells'
M = S + '/management_statement_evidence/tables/'
GROUPS = {
    'p52:l87': {'kind':'INCOME_TAX', 'members':[M+'management_income/rows/'+str(i) for i in (22,23)],
        'subtotals':[], 'heading_is_numeric_row':False, 'labels':['Current tax','Deferred tax']},
    'p54:l79': {'kind':'INCOME_TAX', 'members':[M+'individual_income/rows/'+str(i) for i in (20,21)],
        'subtotals':[], 'heading_is_numeric_row':False, 'labels':['Current tax','Deferred tax']},
    'p56:l161': {'kind':'EARNINGS_PER_SHARE', 'members':[S+'/tables/income/rows/'+str(i) for i in (30,31)],
        'subtotals':[], 'heading_is_numeric_row':False, 'labels':['Basic ( in E uro)','Diluted ( in E uro)'],
        'profit_attribution':S+'/tables/income/rows/27', 'beneficiary':'equity holders of the Bank',
        'weighted_denominator_recomputed':False},
    'p57:l73': {'kind':'OTHER_COMPREHENSIVE_INCOME',
        'members':[S+'/tables/comprehensive/rows/'+str(i) for i in (3,4,6,7,8)],
        'subtotals':[S+'/tables/comprehensive/rows/'+str(i) for i in (5,9)],
        'heading_is_numeric_row':False,
        'labels':['E xchange differences','Deferred taxes','Gains/ (losses) arising during the period',
            'R eclassification adjustments for gains/ (losses) included in the profit or loss','Deferred taxes']},
    'p57:l76': {'kind':'AVAILABLE_FOR_SALE_OCI',
        'members':[S+'/tables/comprehensive/rows/'+str(i) for i in (6,7,8)],
        'subtotals':[S+'/tables/comprehensive/rows/9'], 'heading_is_numeric_row':False,
        'labels':['Gains/ (losses) arising during the period',
            'R eclassification adjustments for gains/ (losses) included in the profit or loss','Deferred taxes'],
        'entire_oci':False},
}


def at(value, pointer):
    for key in pointer[1:].split('/'):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def compact(value):
    import hashlib
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def associations(root, graph, prior):
    units = {u['id']:u for u in graph['units']}
    rows = read(root/BASE/'attempt-068/source-dispositions.json')['rows']
    result=[]
    for row in rows:
        if row['classification'] not in {'EXISTING_MEANING_MISSING_DIRECT_LINK','GROUP_RELATION_IMPLICIT'}:
            continue
        source=row['source']; u=units[source['id']]
        require(source['quote']==u['raw'] and source['bbox']==u['bbox'] and source['source_sha256']==u['source_sha256'], '068source differs')
        short=source['id'].split(':',1)[1]
        pointers=deepcopy(row['current_field_paths'])
        group=deepcopy(GROUPS.get(short))
        if group:
            pointers=group['members']+group['subtotals']
            if 'profit_attribution' in group:
                pointers.append(group['profit_attribution'])
        elif short in {'p51:l27','p51:l28','p51:l29'}:
            i={'p51:l27':0,'p51:l28':1,'p51:l29':2}[short]
            pointers=[M+t+'/columns/'+str(i) for t in ('management_assets','management_liabilities','management_equity')]
        targets=[{'path':p,'sha256':compact(at(prior,p))} for p in pointers]
        result.append({'source':{'unit':source['id'],'document':source['document'],
            'source_sha256':source['source_sha256'],'start':0,'end':len(source['quote']),
            'quote':source['quote'],'bbox':source['bbox']},
            'role':row['classification'], 'meaning':row['meaning'], 'targets':targets,
            'group':group, 'basis':'SUPPLIED_ORIGINAL_SOURCE_REVIEW'})
    require(len(result)==64 and len({r['source']['unit'] for r in result})==64,'Expected exact64context sources')
    return result


def source_oracle(graph, prior, rows):
    """Independent field/geometry checks for the interpretation-bearing groups."""
    units={u['id']:u for u in graph['units']}
    found={r['source']['unit'].split(':',1)[1]:r for r in rows if r.get('group')}
    require(set(found)==set(GROUPS),'Exact five source groups required')
    checked=[]
    for short, definition in GROUPS.items():
        row=found[short]; group=row['group']; heading=units[row['source']['unit']]
        require(group==definition,'Group meaning or member set changed')
        labels=[at(prior,p)['label'] for p in group['members']]
        require([v['quote'] for v in labels]==definition['labels'],'Wrong group row labels')
        for label in labels:
            u=units[label['id']]
            require(u['raw']==label['quote'] and u['page']==heading['page']
                and u['bbox'][1]>heading['bbox'][1],'Group member does not follow its heading on the same page')
        for p in group['members']+group['subtotals']:
            cells=at(prior,p)['cells']
            field='printed_unit' if short in {'p52:l87','p54:l79'} else 'unit'
            expected='EUR per share' if short=='p56:l161' else 'EUR thousands'
            require(all(c[field]==expected for c in cells), 'Group unit changed')
        if short=='p56:l161':
            label=at(prior,group['profit_attribution'])['label']
            require(label['id']=='bes-interim-h1-2010:p56:l158' and label['quote']==units[label['id']]['raw'], 'Wrong EPS profit beneficiary')
        checked.append({'heading':row['source']['unit'],'members':len(labels),'subtotals':len(group['subtotals']), 'source_geometry_checked':True})
    # Dates distinguish duration as well as year. No recomputation from rounded EPS.
    require(at(prior,S+'/tables/income/columns')==at(prior,S+'/tables/comprehensive/columns')==['2010Q2','2009Q2','2010H1','2009H1'], 'Quarter/half-year order changed')
    require(at(prior,S+'/terms/scope/balance_dates')==['2010-06-30','2009-12-31'], 'Balance dates changed')
    require(at(prior,S+'/terms/scope/notes_integral') is True and at(prior,S+'/terms/authority/actual_incorporation_selected') is False, 'Integral notes incorrectly select incorporation')
    return {'five_groups':checked,'periods_and_units_checked':True,'legal_selection':False,'general_interpretation_proved':False}


def profile(root,graph,prior):
    from legalmath.prospectus.successor.contracts import digest
    rows=associations(root,graph,prior)
    source_oracle(graph,prior,rows)
    return {'version':VERSION,'graph_sha256':digest(graph),'prior_sha256':digest(prior),
        'associations':rows,'limits':deepcopy(LIMITS)}


def verify(root,graph,baseline,answer,value):
    from legalmath.prospectus.successor.contracts import digest
    added={'h1_statement_context_review','h1_statement_context_explanation'}
    require(set(answer)==set(baseline)|added and {k:v for k,v in answer.items() if k not in added}==baseline,'Complete067answer changed')
    expected=associations(root,graph,baseline)
    require(value['associations']==expected,'Candidate differs from reviewed068source map')
    review=answer['h1_statement_context_review']
    require(review=={'version':VERSION,'status':'SUPPLIED_STATEMENT_CONTEXT','graph_sha256':value['graph_sha256'],
        'prior_sha256':value['prior_sha256'],'profile_sha256':digest(value),'associations':expected,
        'reviewed_map_sha256':compact(expected),'limits':LIMITS},'Delivered context differs')
    explanation=answer['h1_statement_context_explanation']
    require(explanation['associations']==expected and explanation['limits']==LIMITS,'Explanation dropped associations or limits')
    return {'whole067_preserved':True,'source_associations':len(expected), 'source_oracle':source_oracle(graph,baseline,expected)}


def adverse(graph,baseline,value):
    from legalmath.prospectus import h1_statement_context as context
    from legalmath.prospectus.successor.contracts import digest
    controls=[]
    def refused(name, fn):
        try: fn()
        except ValueError as exc: controls.append({'case':name,'refused':True,'reason':str(exc)})
        else: raise ValueError('Accepted context corruption: '+name)
    for name in ('missing-heading','wrong-source','wrong-group-member','EPS-wrong-beneficiary','OCI-double-count','wrong-target'):
        bad=deepcopy(value['associations'])
        if name=='missing-heading': bad.pop()
        elif name=='wrong-source': bad[0]['source']['unit']='bes-interim-h1-2010:p53:l1'
        elif name=='wrong-group-member': next(r for r in bad if r.get('group'))['group']['members'][0]=S+'/tables/income/rows/0'
        elif name=='EPS-wrong-beneficiary': next(r for r in bad if r['source']['unit'].endswith(':p56:l161'))['group']['beneficiary']='non-controlling interests'
        elif name=='OCI-double-count': next(r for r in bad if r['source']['unit'].endswith(':p57:l73'))['group']['members'].append(S+'/tables/comprehensive/rows/9')
        else: bad[0]['targets'][0]['path']=S+'/terms/review_identity'
        refused(name,lambda:context.check_associations(graph,baseline,bad))
    for name,path,new in [('quarter-halfyear',S+'/tables/income/columns/0','2010H1'),
            ('statement-unit',S+'/terms/measurement/statement_unit','EUR million'),
            ('missing-EPS-unit',S+'/terms/measurement/EPS_unit','EUR thousands')]:
        bad=deepcopy(baseline)
        parent,key=path.rsplit('/',1); target=at(bad,parent)
        target[int(key) if isinstance(target,list) else key]=new
        refused(name,lambda:context.check_associations(graph,bad,value['associations']))
    bad=deepcopy(value); bad['limits']['incorporation_selected']=True
    refused('incorporation-selected',lambda:context.evaluate(graph,baseline,bad,expected_profile_sha256=digest(bad)))
    bad=deepcopy(value); bad['prior_sha256']='0'*64
    refused('stale-prior',lambda:context.evaluate(graph,baseline,bad,expected_profile_sha256=digest(bad)))
    refused('wrong-profile-pin',lambda:context.evaluate(graph,baseline,value,expected_profile_sha256='0'*64))
    bad_graph=deepcopy(graph)
    uid=value['associations'][0]['source']['unit']
    next(u for u in bad_graph['units'] if u['id']==uid)['bbox'][0]+=1
    refused('changed-source-geometry',lambda:context.check_associations(bad_graph,baseline,value['associations']))
    return controls
