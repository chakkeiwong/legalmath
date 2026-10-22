"""Freeze original identities independently of the candidate evidence assessor."""
from collections import Counter
from pathlib import Path
import gzip, hashlib, json, sys, time

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/original-acceptance-338'
INPUTS = {
    'products': 'docs/implementation/prospectus-execution-authority/reviews/conditional-cli-311/products.json',
    'answer': 'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-076/ordinary-answer.json.gz',
    'inventory': 'docs/implementation/prospectus-basf-reference-repair/source-review-002/reference-inventory.json',
    'dispositions': 'docs/implementation/prospectus-basf-reference-repair/source-review-002/dispositions.json',
    'ledger': 'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-025/original-ledger-reconciliation.json.gz',
    'definitions': 'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-026/definition-dossier.json',
}
REPORTS = ('relative_call_notices', 'payment_method_references', 'original_reference_review',
           'governance_references', 'default_references', 'substitution_references',
           'financial_references', 'internal_references')
MARKERS = ('B12','B13','B16','B21','B31','B35','B36','B37','B40','B62','B66','B79','B80','B82')
STATUTES = ('H16','H28','H35','H38','H39','H40','A2','A3','A7','A8','A11','A12')
GAPS = [
 {'id':'general-reference-discovery','state':'OPEN','reason':'Finite supplied reference inventory does not prove linguistic recall','next_action':'Compare explicit, relative and implicit source-reference discovery with the original selected prose and adverse grammar cases'},
 {'id':'general-definition-discovery','state':'OPEN','reason':'Authored vocabulary and612 associations do not prove discovery of other declarations or uses','next_action':'Evaluate declaration, use and governing-scope proposals against independently retained missed and ambiguous forms'},
 {'id':'historical-law-and-onward-scope','state':'OPEN','reason':'Twelve statutory readings and H43 retain historical or onward/application uncertainty','next_action':'Bind the applicable historical editions and onward provisions before promoting a historical interpretation'},
 {'id':'default-f-meaning','state':'OPEN','reason':'Five residual source units have conditional modeling without exhaustive promoted meaning','next_action':'Discriminate remaining source interpretations while preserving all source conditions'},
 {'id':'definition-scope-and-missing-terms','state':'OPEN','reason':'Finite classification retains missing definitions and competing governing scopes','next_action':'Resolve Zinsperiode,U.S.-person status and calculation/payment-day scope from applicable sources'},
 {'id':'agent-designated-office','state':'OPEN','reason':'B54 retains missing role-specific office information','next_action':'Keep conditional role reasoning; seek an authoritative role-specific source without substituting dealer address'},
 {'id':'incorporation-and-question-scope','state':'OPEN','reason':'All dossier source units still receive Q1/Q2; source relevance is not established by inclusion','next_action':'Review incorporation and question-specific relevance without dropping unresolved annual-report sources'},
]

def read(path):
    path=Path(path)
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1048576),b''): h.update(part)
    return h.hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream: json.dump(value,stream,indent=2,ensure_ascii=False)

def freeze():
    started=time.monotonic()
    assert not (PREP/'candidate/reference_requirements.py').exists()
    data={k:read(ROOT/v) for k,v in INPUTS.items()}
    answer,inventory,ledger=data['answer'],data['inventory'],data['ledger']
    assert len(inventory['headings'])==49 and len(inventory['reference_candidates'])==47
    assert tuple(inventory['bracket_roles'])==MARKERS and len(ledger['records'])==60
    assert [r['id'] for r in answer['statutory_references']['records']]==list(STATUTES)
    references={}
    for key in REPORTS:
        for row in answer[key]['references']:
            assert row['id'] not in references
            references[row['id']]=(key,row)
    reference_rows=[]
    for row in ledger['records']:
        identity=('H' if row['family']=='historical_candidate_lines' else 'A')+str(row['index'])
        ref=row['current_reference']; entry={'id':identity,'historical_record_sha256':digest(row)}
        if ref:
            key,current=references[ref['id']]; assert current==ref
            entry.update(reference_id=ref['id'],answer_report=key,target_count=len(ref['targets']))
        else: entry.update(reference_id=None,answer_report='statutory_references',target_count=0)
        entry['current_evidence']='SOURCE_READING_APPLICATION_UNKNOWN' if identity in STATUTES else ('PUBLICATION_SOURCE_APPLICATION_UNKNOWN' if identity=='H43' else 'SOURCE_TO_ANSWER_LINK')
        reference_rows.append(entry)
    review=answer['definition_remainder_review']; dep=answer['definition_dependency_review']
    assert len(review['records'])==62 and len(review['uses'])==612
    definitions=[]
    for r in review['records']:
        items=[(i,u) for i,u in enumerate(review['uses']) if u['record']==r['id']]
        definitions.append({'id':r['id'],'original_record_sha256':r['original_record_sha256'],
            'use_indices':[i for i,u in items],
            'occurrences':[{'use_index':i,**{k:u[k] for k in ('origin','interval','start','end','quote','disposition','remaining')}} for i,u in items]})
    expected={'headings':[{'index':i,'section':r['section'],'source_sha256':digest(r['sources'])} for i,r in enumerate(inventory['headings'])],
        'reference_lines':[{'index':i,'section':r['section'],'source_sha256':digest(r['sources'])} for i,r in enumerate(inventory['reference_candidates'])],
        'markers':[{'id':k,'role':inventory['bracket_roles'][k],'decision':'PRESERVE_PRINTED_LABEL_AND_DELIMITERS'} for k in MARKERS],
        'references':reference_rows,'definitions':definitions,'question_paths':[r['path'] for r in dep['question_links']],
        'gaps':GAPS,'task_ready':False,'whole_build_complete':False}
    bindings={name:sha(ROOT/name) for name in INPUTS.values()}
    bindings.update({r['path']:sha(ROOT/r['path']) for r in data['products']['products'].values()})
    bindings.update({name:sha(ROOT/name) for name in (
        'docs/implementation/prospectus-basf-reference-repair/source-review-002/REVIEW.md',
        'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-076/outputs.json',
        'docs/plans/prospectus-original-acceptance-2026-10-19.md',
        'scripts/prospectus_requirement_inventory.py')})
    for r in ledger['records']:
        for piece in r['source_pieces']:
            if piece['kind']=='SCALAR_EXTRACTION_PROVENANCE':
                basis=piece['original']['substitution_basis']
                bindings.update({basis[k]:sha(ROOT/basis[k]) for k in ('original','text')})
    save(PREP/'expected.json',expected)
    save(PREP/'evidence.json',{'version':'original-reference-evidence.v1','inputs':INPUTS,'bindings':bindings,
        'semantic_inputs':{k:digest(v) for k,v in data.items()},'expected_sha256':sha(PREP/'expected.json')})
    save(PREP/'inventory-freeze.json',{'candidate_absent':True,'expected_sha256':sha(PREP/'expected.json'),
        'evidence_sha256':sha(PREP/'evidence.json'),'wall_seconds':time.monotonic()-started})
    print(json.dumps({'status':'PASS','headings':49,'reference_lines':47,'markers':14,'references':60,'definitions':62,'associations':612,'candidate_absent':True}))

if __name__=='__main__':freeze()
