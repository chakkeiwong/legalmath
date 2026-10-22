"""Small explicit source for testing phase forwarding, not legal generalization."""
import json
from pathlib import Path


def create(root):
    from legalmath.prospectus.successor import service, source_graph
    from legalmath.prospectus.successor.contracts import VERSION, digest, write
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    source=root/'source.txt'
    source.write_text('The Notes are unsecured obligations of the Issuer. The Notes will be redeemed at 100 per cent of their principal amount at maturity.')
    date='2026-01-01T00:00:00Z'
    bundle={'instrument_id':'preparation-synthetic','purpose':'review','issue_date':date,'effective_at':date,'known_at':date,
        'documents':[{'id':'source','path':'source.txt','sha256':digest(source.read_bytes()),'format':'text',
                      'language':'en','authority':'Explicit synthetic control','document_date':date,'known_from':date}],
        'dependencies':[]}
    graph=source_graph.build(bundle,root)
    request={'version':VERSION,'bundle':bundle,'assembly':{'operations':[
        {'unit':u['id'],'role':'OPERATIVE','reason':'Synthetic source','source_text_sha256':u['text_sha256'],'context':'whole'}
        for u in graph['units']]},'scope':{q:{'complete':True,'reason':'Synthetic finite input'} for q in ('Q1','Q2')}}
    inputs={'request':request,'interpretation':{'scope':{'Q1':{'complete':False,'reason':'Explicit later scope is incomplete'}}},
            'law':{'law_input':{'law_bases':[],'facts':[]},'cases':[{'id':'forwarded-law-case'}]},
            'financial':{'scenario_input':None,'cases':[{'id':'forwarded-financial-case'}]}}
    refs={}
    for name,value in inputs.items():
        p=root/(name+'.json');write(p,value);refs[name]={'path':p.name,'sha256':digest(p.read_bytes())}
    recipe={'version':'prospectus-preparation.v1','inputs':refs};write(root/'recipe.json',recipe)
    p1=service.source_product(request,root);p2=service.construction_product(p1,root)
    p3=service.interpretation_product(p1,p2,inputs['interpretation'])
    p4=service.law_product(p1,p3,inputs['law']['cases'],inputs['law']['law_input'])
    p5=service.financial_product(p1,p2,p3,inputs['financial']['cases'],inputs['financial']['scenario_input'])
    return recipe,digest((root/'recipe.json').read_bytes()),dict(zip(('P1','P2','P3','P4','P5'),(p1,p2,p3,p4,p5)))
