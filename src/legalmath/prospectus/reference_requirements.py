"""Original BASF requirement evidence; consistency never implies legal completeness."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import argparse, gzip, hashlib, json
from .successor.contracts import digest

VERSION='original-reference-assessment.v1'
EVIDENCE_SHA256 = '3db34a77624271407223f8c1cec2fd18146a58ff27b4e2b9b6c89c5fe5d0877d'
REPORTS=('relative_call_notices','payment_method_references','original_reference_review',
         'governance_references','default_references','substitution_references',
         'financial_references','internal_references')
MARKERS=('B12','B13','B16','B21','B31','B35','B36','B37','B40','B62','B66','B79','B80','B82')
STATUTES=('H16','H28','H35','H38','H39','H40','A2','A3','A7','A8','A11','A12')
GAP_IDS=('general-reference-discovery','general-definition-discovery',
         'historical-law-and-onward-scope','default-f-meaning',
         'definition-scope-and-missing-terms','agent-designated-office',
         'incorporation-and-question-scope')
ANCHOR_KEYS=('unit','document','source_sha256','start','end','quote')

def require(condition,message):
    if not condition: raise ValueError(message)

def inventory_digest(value):
    """Independent inventory uses compact JSON; product digests keep their format."""
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def read(path):
    path=Path(path)
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1048576),b''):h.update(part)
    return h.hexdigest()

def contained(root,name):
    p=(Path(root)/name).resolve()
    require(p.is_relative_to(Path(root).resolve()),'Evidence path escapes repository')
    return p

def unique(rows,key,label):
    result={row[key]:row for row in rows}
    require(len(result)==len(rows),'Duplicate '+label)
    return result

class Sources:
    def __init__(self,products):
        self.raw=unique(products['P1']['payload']['graph']['units'],'id','source unit')
        self.selected=unique(products['P2']['payload']['assembly']['units'],'unit','selected unit')

    def anchor(self,s):
        require(all(k in s for k in ANCHOR_KEYS),'Incomplete source anchor')
        u=self.raw.get(s['unit']);a,b=s['start'],s['end']
        require(u is not None and u.get('visible',False),'Source unavailable')
        require(s['document']==u['document'] and s['source_sha256']==u['source_sha256'],'Source edition differs')
        require(type(a) is int and type(b) is int and 0<=a<b<=len(u['raw']),'Source interval differs')
        require(u['raw'][a:b]==s['quote'],'Source quotation differs')

    def retained(self,s):
        self.anchor(s);u=self.selected.get(s['unit'])
        require(u is not None,'Selected source missing')
        if "character_map" not in u:
            raw=self.raw[s["unit"]]
            require(u["text"]==raw["raw"] and u.get("original_sha256")==raw.get("text_sha256")==digest(raw["raw"].encode())
                and u.get("source",{}).get("document")==raw["document"]
                and u.get("source",{}).get("page")==raw["page"],
                "Unmapped source is not an exact direct copy")
            return
        covered=set()
        for m in u.get('character_map',[]):
            t=m.get('source') or {}
            if t.get('unit')!=s['unit']:continue
            a,b=max(t['start'],s['start']),min(t['end'],s['end'])
            if a>=b:continue
            self.anchor(t)
            require(m['end']-m['start']==t['end']-t['start'],'Source copy length changed')
            require(u['text'][m['start']:m['end']]==t['quote'],'Selected quotation differs')
            covered.update(range(a,b))
        require(set(range(s['start'],s['end']))<=covered,'Original selected source lost')

def inspect_evidence(data,products,expected,root):
    answer=data['answer'];inventory=data['inventory'];ledger=data['ledger']
    require(answer.get('report_sha256')==digest({k:v for k,v in answer.items() if k!='report_sha256'}),'Answer digest differs')
    source=Sources(products);headings=[];lines=[]
    for name,count,out in [('headings',49,headings),('reference_candidates',47,lines)]:
        require(len(inventory[name])==count,'Original '+name+' denominator differs')
        for i,row in enumerate(inventory[name]):
            for s in row['sources']:
                if 'unit' in s:source.retained(s)
                else:require('substitution_basis' in s,'Unrecognized scalar provenance')
            out.append({'index':i,'section':row['section'],'source_sha256':inventory_digest(row['sources'])})
    require(headings==expected['headings'] and lines==expected['reference_lines'],'Original inventory identity differs')
    selected=products['P2']['payload']['selected_contract']
    require(tuple(inventory['bracket_roles'])==MARKERS,'Original marker identities differ')
    dispositions=unique(data['dispositions'],'id','marker disposition');marker_rows=[]
    for name in MARKERS:
        r=dispositions[name]
        for s in r['spans']:source.retained(s)
        marker_rows.append({'id':name,'role':inventory['bracket_roles'][name],
            'decision':'PRESERVE_PRINTED_LABEL_AND_DELIMITERS'})
    require(marker_rows==expected['markers'],'Printed marker decision differs')
    for s in dispositions['B54']['spans']:source.retained(s)
    require(Counter(r['preview'] for r in selected['remaining_brackets'])==
        Counter(dispositions[k]['text'] for k in (*MARKERS,'B54')),'Remaining printed marker or office placeholder differs')
    refs=unique(products['P3']['payload']['interpretation_input']['reference_admission']['references'],'id','admitted reference')
    current={}
    for key in REPORTS:
        require(answer[key]['missing']==[],'Current reference reports missing targets')
        for r in answer[key]['references']:
            require(r['id'] not in current,'Duplicate answer reference')
            require(refs.get(r['id'])==r,'Complete answer reference differs from P3')
            source.retained(r['source']);source.anchor(r['authority'])
            for t in r['targets']:source.retained(t['source'])
            current[r['id']]=(key,r)
    require(len(ledger['records'])==60,'Original reference ledger denominator differs')
    identities=[];reference_rows=[]
    statutes=unique(answer['statutory_references']['records'],'id','statutory record')
    require(tuple(statutes)==STATUTES,'Original statutory records differ')
    for r in ledger['records']:
        identity=('H' if r['family']=='historical_candidate_lines' else 'A')+str(r['index'])
        identities.append(identity)
        if identity.startswith('H'):
            require(r['original']['source_pieces']==inventory['reference_candidates'][r['index']]['sources'],'Original reference-line identity differs')
        for item in r['source_pieces']:
            s=item['original'];kind=item['kind']
            if kind=='RAW_ANCHOR':source.retained(s)
            elif kind=='SCALAR_ANCHOR':source.anchor(s['substitution_basis'])
            else:
                require(kind=='SCALAR_EXTRACTION_PROVENANCE','Unknown provenance kind')
                b=s['substitution_basis']
                require(sha(contained(root,b['original']))==b['source_sha256'] and
                    sha(contained(root,b['text']))==b['text_sha256'],'Scalar source/extraction differs')
        ref=r['current_reference'];row={'id':identity,'historical_record_sha256':inventory_digest(r)}
        if ref:
            require(refs.get(ref['id'])==ref,'Historical complete reference differs')
            key,actual=current[ref['id']]
            row.update(reference_id=ref['id'],answer_report=key,target_count=len(actual['targets']))
        else:
            require(identity in statutes,'Unaccounted original reference')
            row.update(reference_id=None,answer_report='statutory_references',target_count=0)
        if identity in statutes:
            s=statutes[identity]
            require(s['original_family']==r['family'] and s['original_index']==r['index'],'Statutory original identity differs')
            require(s['availability']=='RETAINED_PRIMARY_READING' and s['application']=='UNKNOWN'
                and s['historical_validity']=='UNKNOWN' and s['unresolved_application'],'Historical/application uncertainty lost')
            row['current_evidence']='SOURCE_READING_APPLICATION_UNKNOWN'
        elif identity=='H43':
            p=answer['publication_routes_review']['context']
            require(p['original_H43']['original_record_sha256']==digest(r) and p['current_source_available'] is True
                and p['historical_application']=='NOT_ESTABLISHED' and p['implementing_rules']=='NOT_RETRIEVED',
                'H43 current source or historical qualification differs')
            row['current_evidence']='PUBLICATION_SOURCE_APPLICATION_UNKNOWN'
        else:row['current_evidence']='SOURCE_TO_ANSWER_LINK'
        reference_rows.append(row)
    require(identities==['H'+str(i) for i in range(47)]+['A'+str(i) for i in range(13)],'Original reference identities missing or reordered')
    require(reference_rows==expected['references'],'Original reference/current-answer reconciliation differs')
    src=answer['definition_sources'];review=answer['definition_remainder_review'];dep=answer['definition_dependency_review']
    original=unique(src['records'],'id','definition source');current_def=unique(review['records'],'id','definition record')
    deps=unique(dep['records'],'record','definition dependency');uses=review['uses']
    require(len(original)==len(current_def)==len(deps)==62 and len(uses)==612,'Definition denominator differs')
    require(list(original)==[r['id'] for r in data['definitions']['records']]==list(current_def)==list(deps),'Definition record identities differ')
    require(dep['source_review_sha256']==digest(review),'Definition source review identity differs')
    text=products['P2']['payload']['assembly']['continuous_text'];definition_rows=[]
    for identity,record in current_def.items():
        indices=[i for i,u in enumerate(uses) if u['record']==identity];d=deps[identity]
        require(record['use_indices']==d['use_indices']==indices,'Definition association missing, duplicated or reordered')
        require(record['original_record_sha256']==d['source_record_sha256']==digest(original[identity]),'Definition source record differs')
        occurrences=[];ordinary=[]
        for i in indices:
            u=uses[i];a,b=u['start'],u['end']
            require(type(a) is int and type(b) is int and 0<=a<b<=len(text) and text[a:b]==u['quote'],'Definition occurrence quotation differs')
            require(u['disposition']!='UNRECONCILED' and isinstance(u['remaining'],list)
                and (u['remaining'] or (u['disposition']=='BOUND_CONDITIONALLY' and u.get('binding'))),
                'Definition interpretation or qualification lost')
            if u['origin']=='ORIGINAL':
                interval=src['intervals'][u['interval']]
                require(all(u[k]==interval[k] for k in ('start','end','quote')),'Definition source interval differs')
                ordinary.append(u['interval'])
            else:
                require(u['origin']=='SUPPLEMENTAL' and u['interval'] is None,'Unknown definition origin')
                extra=src['application_supplement']['source_supplement']['new_occurrence']
                require(identity in extra['candidate_record_associations'] and all(u[k]==extra[k] for k in ('start','end','quote')),'Supplemental association differs')
            occurrences.append({'use_index':i,**{k:deepcopy(u[k]) for k in ('origin','interval','start','end','quote','disposition','remaining')}})
        require(ordinary==[u['interval'] for u in original[identity]['uses']],'Original definition uses differ')
        require(occurrences==d['occurrences'],'Downstream definition occurrences differ')
        reasons=sorted({r for i in indices for r in uses[i]['remaining']})
        require(d['remaining_premises']==[{'id':'definition-premise:'+identity+':'+str(n),'reason':r,
            'use_indices':[i for i in indices if r in uses[i]['remaining']]} for n,r in enumerate(reasons)],'Remaining definition premises differ')
        definition_rows.append({'id':identity,'original_record_sha256':record['original_record_sha256'],
            'use_indices':indices,'occurrences':occurrences})
    require(definition_rows==expected['definitions'],'Complete definition inventory differs')
    require(sum(u['origin']=='ORIGINAL' for u in uses)==610,'Original/supplemental denominator differs')
    for link in dep['question_links']:
        q=answer
        for k in link['path']:q=q[k]
        require(q['status']==link['retained_status'] and q['value']==link['retained_value'],'Current question status differs')
        original_links=[v for v in review['question_links'] if v['path']==link['path']]
        dependency_map={v['original_dependency']:v for v in dep['records']}
        require(len(original_links)==1 and link['replaced']==original_links[0]['unresolved_definition_ids']
            and len(link['replaced'])==len(set(link['replaced']))==len(dependency_map)
            and set(link['replaced'])==set(dependency_map),'Original question dependency order differs')
        expected_ids=[r['id'] for identity in link['replaced'] for r in dependency_map[identity]['remaining_premises']]
        require(link['replacement_ids']==expected_ids and all(v in q['unresolved'] for v in expected_ids)
            and link['discovery_limit']=='definition-discovery:finite-dossier'
            and link['discovery_limit'] in q['unresolved'],'Current question dependency lost')
    paths=[r['path'] for r in dep['question_links']]
    require(paths==expected['question_paths'] and len(paths)==5,'Question dependency paths differ')
    coverage=answer['residual_coverage_review']
    require(len(coverage['heading_units'])==24 and len(coverage['substantive_pending'])==7
        and len(coverage['default_conditionally_modeled_units'])==5 and len(coverage['missing_agent_units'])==2,
        'Original substantive residuals differ')
    require(tuple(r['id'] for r in expected['gaps'])==GAP_IDS
        and all(r['state']=='OPEN' and r['reason'] and r['next_action'] for r in expected['gaps']),
        'Original unfinished requirement missing')
    require(dep['general_recall_established'] is False and dep['whole_task_complete'] is False
        and coverage['whole_task_complete'] is False and expected['task_ready'] is False
        and expected['whole_build_complete'] is False,'False completeness')
    report={'version':VERSION,'task':'basf-references','status':'CONSISTENT_PARTIAL_EVIDENCE',
        'headings':headings,'reference_lines':lines,'markers':marker_rows,'references':reference_rows,
        'definitions':definition_rows,'question_paths':paths,'gaps':deepcopy(expected['gaps']),
        'task_ready':False,'whole_build_complete':False,'assessment_scope':'FINITE_ORIGINAL_INVENTORY',
        'actual_holdings_required_for_general_build':False,'external_adviser_required':False,
        'answer_sha256':digest(answer),'products_sha256':digest(products),
        'numbering_decision':'PRESERVE_PRINTED_LABELS_AND_DELIMITERS',
        'numbering_transformation_authorized':False,'new_full_consumer_execution':False}
    return {**report,'report_sha256':digest(report)}

def assess(root,evidence_path):
    root=Path(root).resolve();path=contained(root,evidence_path)
    require(EVIDENCE_SHA256 is not None and sha(path)==EVIDENCE_SHA256,'Unreviewed evidence manifest')
    evidence=read(path)
    for name,checksum in evidence['bindings'].items():
        require(sha(contained(root,name))==checksum,'Evidence file differs: '+name)
    data={k:read(contained(root,v)) for k,v in evidence['inputs'].items()}
    require({k:inventory_digest(v) for k,v in data.items()}==evidence['semantic_inputs'],'Evidence semantic identity differs')
    products={k:read(contained(root,r['path'])) for k,r in data['products']['products'].items()}
    expected_path=path.with_name('expected.json')
    require(sha(expected_path)==evidence['expected_sha256'],'Expected original requirement inventory differs')
    return inspect_evidence(data,products,read(expected_path),root)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',required=True);parser.add_argument('--evidence',required=True)
    parser.add_argument('--output',required=True);args=parser.parse_args()
    result=assess(args.repository,args.evidence)
    output=contained(args.repository,args.output)
    with output.open('x') as stream:json.dump(result,stream,indent=2,ensure_ascii=False)
    print(json.dumps({'status':result['status'],'task_ready':False,'report_sha256':result['report_sha256']}))

if __name__=='__main__':main()
