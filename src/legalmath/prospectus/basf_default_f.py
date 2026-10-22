"""Source-bound conditional default(f) hypotheses, without choosing a reading."""
from copy import deepcopy
from pathlib import Path

from . import basf_body_coverage
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.occurrences import anchor
from .successor.predicates import dispatch

VERSION='basf-default-f-alternatives.v1'
DOC='basf-base-september-2022-exchange'
FINAL='basf-2032-final'
RANGES={
    'german_f':(DOC,127,12,16), 'english_f_comparison':(DOC,82,12,15),
    'entitlement':(DOC,126,41,43), 'cure':(DOC,127,22,23),
    'quorum':(DOC,127,24,41), 'notice':(DOC,127,42,45),
    'german_priority':(DOC,133,22,24), 'final_language_selection':(FINAL,7,48,53),
}
FACTS={
    'cessation':'Issuer ceases all or substantially all its business operations.',
    'disposal':'Issuer sells or otherwise disposes of all or a substantial part of its assets.',
    'value_cessation':'Cessation causes material diminution of the value of issuer assets.',
    'risk_cessation':'For that causal reason it becomes likely that the issuer cannot fulfil payment obligations to holders.',
    'value_disposal':'Disposal causes material diminution of the value of issuer assets.',
    'risk_disposal':'For that disposal-related causal reason it becomes likely that the issuer cannot fulfil payment obligations to holders.',
    'value_joint':'The combined cessation and disposal cause material diminution of issuer asset value.',
    'risk_joint':'For that combined-conduct causal reason it becomes likely that the issuer cannot fulfil payment obligations to holders.',
}
FORMULAS={
    'both_conducts':{'all':['cessation','disposal','value_joint','risk_joint']},
    'either_qualified_conduct':{'any':[{'all':['cessation','value_cessation','risk_cessation']},
                                     {'all':['disposal','value_disposal','risk_disposal']}]},
    'cessation_or_qualified_disposal':{'any':['cessation',{'all':['disposal','value_disposal','risk_disposal']}]},
}
READINGS={
    'both_conducts':'Cessation and disposal are cumulative, with both financial consequences caused by the combined conduct.',
    'either_qualified_conduct':'Cessation or disposal is sufficient only with both consequences attributable to the relevant conduct.',
    'cessation_or_qualified_disposal':'Cessation is independently sufficient; both financial consequences qualify the disposal alternative.',
}
EXTRA={
    'notice':'At modeled exercise an eligible holder elects by written German/English declaration delivered by hand or registered mail to the designated Fiscal Agent office.',
    'cured_before_exercise':'The particular ground(f) situation was cured before this exercise.',
    'quorum_at_receipt':'Fiscal Agent has received declarations from holders of at least one-tenth of then-outstanding principal.',
    'other_eligible_at_receipt':'An eligible ground(a), (d), (e) or (g), excluding(f), exists when the declaration is received.',
    'f_other_eligibility_at_receipt':'All other requirements for the candidate(f) event to entitle holders at receipt, including the applicable cure restriction, are satisfied.',
}


def qualify(expr,namespace):
    if isinstance(expr,str):return namespace+'.'+expr
    if type(expr) is bool:return expr
    op,args=next(iter(expr.items()))
    return {op:qualify(args,namespace) if op=='not' else [qualify(a,namespace) for a in args]}


def expressions(reading):
    event=FORMULAS[reading]
    x,r=qualify(event,'exercise'),qualify(event,'receipt')
    return {'event_at_exercise':x,'event_at_receipt':r,
        'modeled_f_exercise':{'all':[x,'notice',{'not':'cured_before_exercise'}]},
        'bc_quorum_condition_at_receipt':{'any':['quorum_at_receipt','other_eligible_at_receipt',
            {'all':[r,'f_other_eligibility_at_receipt']}]}}


def comparison(decisions):
    values=set(decisions)
    if 'CONFLICT' in values:return 'CONFLICT_IN_ENUMERATED_READINGS'
    if values=={'YES'}:return 'ALL_ENUMERATED_YES'
    if values=={'NO'}:return 'ALL_ENUMERATED_NO'
    if 'UNKNOWN' in values:return 'UNRESOLVED_WITHIN_ENUMERATED_READINGS'
    return 'DIFFERENT_ENUMERATED_DECISIONS'


def analyze(scenario):
    fields(scenario,{'id','kind','facts'},{'id','kind','facts'})
    if not isinstance(scenario['id'],str) or not scenario['id'] or scenario['kind']!='HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical scenario identity required')
    allowed={prefix+'.'+name for prefix in ('exercise','receipt') for name in FACTS}|set(EXTRA)
    facts=scenario['facts'];fields(facts,allowed)
    if any(v is not None and v!='conflict' and type(v) is not bool for v in facts.values()):
        raise ValueError('Scenario facts are Boolean, unknown or conflict')
    decisions={key:{name:dispatch(expr,facts,engine='finite') for name,expr in expressions(key).items()}
               for key in FORMULAS}
    outcomes={name:comparison([r[name]['status'] for r in decisions.values()])
              for name in next(iter(decisions.values()))}
    return {'id':scenario['id'],'kind':scenario['kind'],'facts':deepcopy(facts),'readings':decisions,
        'comparison':outcomes,'input_conflicts':[k for k,v in facts.items() if v=='conflict'],
        'selected_reading':None,'actual_event_established':False,
        'interpretation':'Comparison is conditional on the enumerated formulas; agreement does not adjudicate the governing clause.',
        'bc_result_scope':'Only the quorum condition; all other requirements for grounds(b)/(c) remain separate.'}


def source_groups(products):
    graph=products['P1']['payload']['graph'];raw={u['id']:u for u in graph['units']}
    if len(raw)!=len(graph['units']):raise ValueError('Duplicate original source identity')
    selected={u['unit']:u for u in products['P2']['payload']['assembly']['units']}
    groups={}
    for name,(doc,page,start,end) in RANGES.items():
        units=[raw[doc+':p'+str(page)+':l'+str(n)] for n in range(start,end+1)]
        if any(not u['visible'] or u['text_sha256']!=digest(u['raw'].encode()) for u in units):
            raise ValueError('Original default or qualification text changed')
        rows=[]
        for u in units:
            s=selected[u['id']]
            role='COMPARISON_ONLY' if name=='english_f_comparison' else 'CONSTRUCTION_AUTHORITY' if name=='final_language_selection' else 'SELECTED_GERMAN'
            row={'source':anchor(u),'bbox':u['bbox'],'use':role}
            if role=='SELECTED_GERMAN':
                row.update(selected_text=s['text'],assembly_role=s['role'],
                           selected_sources=basf_body_coverage.selected_sources(graph,s,0,len(s['text']),raw=raw))
            rows.append(row)
        groups[name]=rows
    german=' '.join(r['source']['quote'] for r in groups['german_f'])
    english=' '.join(r['source']['quote'] for r in groups['english_f_comparison'])
    if ('einstellt, alle oder den' not in german or 'und (i)' not in german or 'und (ii)' not in german
            or 'operations or sells or' not in english or 'and thus (i)' not in english or 'and (ii)' not in english):
        raise ValueError('Original conduct connector or financial qualifications changed')
    if [r['source']['quote'] for r in groups['final_language_selection']][2:]==[
            '\uf078 German and English (German controlling)',
            'Deutsch und Englisch (deutscher Text maßgeblich)',
            '\uf06f English and German (English controlling)',
            'Englisch und Deutsch (englischer Text maßgeblich)']:
        pass
    else:raise ValueError('Actual selected and unselected language options changed')
    return groups


def premises():
    return {**{prefix+'.'+key:{'meaning':value,'time':prefix,'source_group':'german_f',
                              'basis':'SUPPLIED_CAUSAL_PROPOSITION'}
               for prefix in ('exercise','receipt') for key,value in FACTS.items()},
            **{k:{'meaning':v,'time':'exercise' if k in ('notice','cured_before_exercise') else 'receipt',
                   'source_group':'notice' if k=='notice' else 'cure' if k=='cured_before_exercise' else 'quorum',
                   'basis':'SUPPLIED_HYPOTHETICAL_PREMISE'} for k,v in EXTRA.items()}}


def evaluate(products,prior,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','prior_sha256','reviewer','sources','groups','premises','candidates','scenarios',
          'governing_language','selected_reading','candidate_set_exhaustive','independent_legal_acceptance'}
    fields(profile,keys,keys)
    if profile['version']!=VERSION or digest(profile)!=expected_profile_sha256 or profile['products_sha256']!=digest(products) or profile['prior_sha256']!=digest(prior):
        raise ValueError('Pinned default(f) profile or complete comparator changed')
    if (profile['governing_language']!='German' or profile['selected_reading'] is not None or
            profile['candidate_set_exhaustive'] is not False or profile['independent_legal_acceptance'] is not False):
        raise ValueError('Unresolved German construction and finite hypothetical scope must remain')
    reviewer=profile['reviewer'];fields(reviewer,{'identity','basis','independent'},{'identity','basis','independent'})
    if not isinstance(reviewer['identity'],str) or not reviewer['identity'].strip() or reviewer['basis']!='AGENT_EXPOSED_DEVELOPMENT_REVIEW' or reviewer['independent'] is not False:
        raise ValueError('Unsupported default(f) review authority')
    groups=source_groups(products)
    if profile['groups']!=groups:raise ValueError('Complete original/selected source groups changed')
    if profile['premises']!=premises():raise ValueError('Causal, temporal or eligibility premise changed')
    expected=[{'id':k,'meaning':READINGS[k],'event':v,'expressions':expressions(k)} for k,v in FORMULAS.items()]
    if profile['candidates']!=expected:raise ValueError('Candidate causality, notice, cure or receipt condition changed')
    docs=products['P1']['payload']['request']['bundle']['documents']
    sources=profile['sources']
    if [r.get('document') for r in sources]!=[DOC,FINAL]:raise ValueError('Both original source documents required')
    root=Path(root).resolve()
    for s in sources:
        fields(s,{'document','path','sha256','images'},{'document','path','sha256','images'})
        doc=next(d for d in docs if d['id']==s['document'])
        if (s['path'],s['sha256'])!=(doc['path'],doc['sha256']):raise ValueError('Original default(f) edition changed')
        if [i.get('page') for i in s['images']]!=([82,126,127,133] if s['document']==DOC else [7]):
            raise ValueError('Complete original comparison and qualification images required')
        for item in [s,*s['images']]:
            name=item['path'];p=(root/name).resolve()
            if Path(name).is_absolute() or not p.is_relative_to(root) or not p.is_file() or digest(p.read_bytes())!=item['sha256']:
                raise ValueError('Original default(f) PDF or inspected image changed')
    previous=prior['body_coverage_review']
    residual=next(q for q in previous['remaining_questions'] if q['id']=='UNRESOLVED_DEFAULT_F')
    ids=[DOC+':p127:l'+str(n) for n in range(12,17)]
    if residual['status']!='UNRESOLVED' or [r['unit'] for r in residual['evidence']]!=ids:
        raise ValueError('Prior unresolved complete German default(f) must remain')
    if any(r['assembly_role']!='UNKNOWN' for r in groups['german_f']):
        raise ValueError('Conditional comparison cannot promote original default(f) roles')
    scenarios=profile['scenarios']
    if not isinstance(scenarios,list) or not scenarios or len({s.get('id') for s in scenarios})!=len(scenarios):
        raise ValueError('Distinct hypothetical scenario set required')
    if scenarios[0]!={'id':'all-open','kind':'HYPOTHETICAL_DEVELOPMENT','facts':{}}:
        raise ValueError('The all-open baseline must precede supplied hypothetical facts')
    results=[analyze(s) for s in scenarios]
    return {'version':VERSION,'profile_sha256':digest(profile),'reviewer':deepcopy(reviewer),
        'sources':deepcopy(sources),'groups':groups,'premises':premises(),'candidates':deepcopy(expected),
        'scenarios':results,'selected_reading':None,'candidate_set_exhaustive':False,
        'governing_language':'German','prior_default_question':deepcopy(residual),
        'source_meaning_promoted':False,'actual_default_established':False,'independent_legal_acceptance':False,
        'temporal_rule':'Receipt facts determine only the quorum condition; exercise facts, notice and cure determine modeled direct(f) exercise.',
        'causal_rule':'Distinct consequences belong to cessation, disposal or combined conduct; no cross-candidate causal equivalence is assumed.',
        'next_evidence':'Qualified construction of the full governing German provision and relevant authority; dated event, causation, notice and appointment evidence for actual application.'}


def consume(products,prior_profiles,profile,root,*,expected_prior_profiles_sha256,expected_profile_sha256):
    fields(prior_profiles,{'preceding','body'},{'preceding','body'})
    if digest(prior_profiles)!=expected_prior_profiles_sha256:raise ValueError('Pinned preceding profiles changed')
    old,bp=prior_profiles['preceding'],prior_profiles['body']
    prior=basf_body_coverage.consume(products,old,bp,root,
        expected_prior_profiles_sha256=digest(old),expected_profile_sha256=digest(bp))
    return {**prior,'default_f_review':evaluate(products,prior,profile,root,expected_profile_sha256=expected_profile_sha256)}


def consume_verified(products,prior_profiles,profile,root,*,expected_prior_profiles_sha256,expected_profile_sha256):
    """Optional independently checked finite inference; no source-meaning promotion."""
    from .default_f_certificates import certificate, context
    result=consume(products,prior_profiles,profile,root,
        expected_prior_profiles_sha256=expected_prior_profiles_sha256,expected_profile_sha256=expected_profile_sha256)
    bound=context(result,profile,products_sha256=digest(products),prior_profiles_sha256=expected_prior_profiles_sha256)
    return {**result,'reasoning_certificate':certificate(result,profile,expected_context=bound)}
