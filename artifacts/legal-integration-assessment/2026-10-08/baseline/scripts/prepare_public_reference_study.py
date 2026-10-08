"""Freeze prospective SFC interpretation cases from complete retained public pages.

Run once after official retrieval. No model call, external decision or publication.
The independently written expected tables are checked against reference programs;
their agreement is an engineering check, not independent legal adjudication.
"""
from argparse import ArgumentParser
from copy import deepcopy
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
import re

from legalmath.canonical import canonical, digest, raw_digest
from legalmath.interpretation.assurance.evaluation import freeze, source_packet
from legalmath.interpretation.assurance.sources import extract_document
from legalmath.sources.extract import TextParser

ROOT=Path(__file__).resolve().parents[1]
AT='2026-09-24T04:20:00.000000Z'
SOURCES={
    'family-offices':'https://www.sfc.hk/en/faqs/intermediaries/licensing/Family-Offices',
    'client-money':'https://www.sfc.hk/en/faqs/intermediaries/supervision/Client-Money-Rules/30-Sep-2024---Client-Money-Rules',
    'professional-investors':'https://www.sfc.hk/en/faqs/intermediaries/supervision/Professional-Investors/Professional-Investors',
    'suitability':'https://www.sfc.hk/en/faqs/intermediaries/supervision/Triggering-of-Suitability-Obligations/Triggering-of-Suitability-Obligations',
}


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def document(name,raw):
    doc={'url':SOURCES[name],'media_type':'text/html','data':raw}
    e=extract_document(doc);text=e['text']
    title=re.search(r'<div class="headline">(.*?)</div>',raw.decode(),re.S).group(1)
    parser=TextParser();parser.feed(title);title=''.join(parser.parts)
    first=re.search(r'\bQ1\s*:',text).start()
    a=text.rfind(title,0,first);m=re.search(r'Last update: [^\r\n]+',text[first:])
    b=first+m.end()
    if a<0 or b<=a:raise ValueError('Cannot anchor complete FAQ body')
    region={'anchor':{'start':a,'end':b,'quote':text[a:b]}}
    selection={'raw_sha256':e['raw_sha256'],'text_sha256':e['text_sha256'],
               'ranges':[[a,b]],'regions':[region]}
    return {'url':doc['url'],'media_type':doc['media_type'],'raw_hex':raw.hex(),
            'sha256':e['raw_sha256'],'selection':selection},e


def quote(packet,text):
    found=[{'unit_id':u['unit_id'],'quote':text} for u in packet['units'] if text in u['text']]
    if len(found)!=1:raise ValueError('Missing/ambiguous exact quote: '+text)
    return found[0]


def snapshot(values):
    return {'subject_id':'hypothetical.reference.scenario','facts':{
        k:({'type':'bool','status':'unknown','reason':'MISSING'} if v is None else
           {'type':'bool','status':'known','value':v,'evidence_ids':['curated.hypothetical'],
            'valid_from':AT,'valid_until':None,'recorded_at':AT}) for k,v in values.items()}}


def prepare(output):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'.localresources/interpretation-round5'):
        raise ValueError('Use a new round5 source directory')
    output.mkdir(parents=True);docs={};acquisition=[]
    for name,url in SOURCES.items():
        raw=Path('/tmp/legalmath-c1-'+name+'.html').read_bytes()
        doc,e=document(name,raw);docs[name]=(doc,e)
        (output/(name+'.html')).write_bytes(raw);(output/(name+'.txt')).write_text(e['text'])
        save(output/(name+'.extraction.json'),e)
        acquisition.append({'family':name,'url':url,'raw_sha256':raw_digest(raw),
            'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'method':'curl --fail --location --max-time 40; linked from official FAQ indexes',
            'full_page_retained':True,'temporal_claim':'Observed version; historic/current legal applicability not adjudicated',
            'selected_body_sha256':raw_digest(doc['selection']['regions'][0]['anchor']['quote'].encode())})
    save(output/'acquisition.json',acquisition)
    cases=[];provenance=[]
    for name in ('family-offices','client-money'):
        clean=bytes.fromhex(docs[name][0]['raw_hex'])
        before,after=(('all of which must be present','at least one of which must be present') if name=='family-offices'
            else ('regardless of the role played by such LC','only when such LC is not acting as a Transfer Agent'))
        if clean.count(before.encode())!=1:raise ValueError('Mutation source is not unique')
        for altered in (False,True):
            raw=clean.replace(before.encode(),after.encode()) if altered else clean
            doc,_=document(name,raw);suffix='altered' if altered else 'clean'
            selected=('Selected control: the three conditions in Family Offices Q3, after any regulated-activity carve-out has been resolved. '
                'The requested Boolean is whether the stated licensing trigger is satisfied, not whether the office holds a licence. '
                'Retain facts requiring judgment and all qualifications.' if name=='family-offices' else
                'Selected control: the RA13 Client Money Rules Q1 applicability trigger for scheme money received or held in Hong Kong in the course of RA13. '
                'Distinguish the transfer-agent role and the continuing Schedule 11 duties. This Boolean concerns only Q1 applicability, not whole-law compliance.')
            selected+=' Controlled text-interpretation study: supplied pages may be experimental variants. Do not infer legal authority from the URL alone.'
            c={'case_id':name+'.'+suffix,'family_id':'sfc.'+name+'.qa','variant':'ALTERED' if altered else 'CLEAN',
               'roots':[doc],'selected_slice':selected,'at':AT,'reference':{}}
            packet=source_packet(c)
            if name=='family-offices':
                evidence=quote(packet,after if altered else before)
                fact_data=[('regulated','Services constitute regulated activity after applicable carve-outs'),
                    ('business','Provision of the services constitutes carrying on a business'),
                    ('hong_kong','That business is carried on in Hong Kong')]
                expression='(or regulated business hong_kong)' if altered else '(and regulated business hong_kong)'
                values=list(product((False,True),repeat=3))+[(True,None,True),(None,False,False)]
                # Explicit truth tables are not calculated from the expression under test.
                expected=([False,True,True,True,True,True,True,True,True,None] if altered else
                          [False,False,False,False,False,False,False,True,None,False])
                uncertainty=['Whether activities are regulated, the intra-group carve-out and carrying on business require judgments.',
                    'The source presents necessary licensing factors; completeness beyond the selected trigger is not adjudicated.']
            else:
                evidence=quote(packet,after if altered else before)
                fact_data=[('ra13_context','RA13 licensed corporation or associated entity handling funds in the course of RA13'),
                    ('scheme_money','The funds are scheme money under the incorporated legal definition'),
                    ('in_hong_kong','The scheme money is received or held in Hong Kong'),
                    ('transfer_agent','The licensed corporation is acting as a Transfer Agent')]
                expression='(and ra13_context scheme_money in_hong_kong'+(' (not transfer_agent))' if altered else ')')
                values=[(True,True,True,True),(True,True,True,False),(True,False,True,True),
                        (True,True,False,True),(False,True,True,False),(True,None,True,False),(True,True,True,None)]
                expected=([False,True,False,False,False,None,None] if altered else [True,True,False,False,False,None,True])
                uncertainty=['Scheme-money classification incorporates legislation not adjudicated in this study.',
                    'A false Q1 trigger does not waive Schedule 11 duties or answer Q3 about REIT accounts.']
            names=[f[0] for f in fact_data]
            reading={'local_id':'reference.trigger','family':'scope','subject':name,
                'statement':'[TRUE_IS_COMPLIANT] True means the selected applicability trigger is satisfied, not general compliance.',
                'distinction':'Source-bound proposed reference for a finite semantic test.',
                'citations':[evidence],'assumptions':uncertainty,'questions':uncertainty,
                'formalization':{'facts':[{'name':n,'type':'bool','meaning':m,'unit':'truth value',
                    'source_unit_ids':[evidence['unit_id']],'requires_judgment':True} for n,m in fact_data],
                    'scope':'true','result':expression,'result_type':'bool'}}
            answers=[{'status':'UNKNOWN','type':'bool'} if v is None else
                     {'status':'TRUE' if v else 'FALSE','type':'bool','value':v} for v in expected]
            c['reference']={'basis':'SEEDED_TRANSFORMATION' if altered else 'PUBLIC_QA_INTERPRETATION',
                'evidence':[evidence],'binding_reading':reading,
                'snapshots':[snapshot(dict(zip(names,v))) for v in values],
                'accepted':[answers],'limitations':uncertainty+[
                    'Reference authored during prospective study preparation; not an independently adjudicated answer.',
                    'A seeded page is a counterfactual test input and is not an SFC statement.' if altered else
                    'The retained page is official; our finite reference interpretation has no additional authority.']}
            cases.append(c)
            provenance.append({'case_id':c['case_id'],'original_source_sha256':raw_digest(clean),
                'case_source_sha256':raw_digest(raw),'official_bytes_unchanged':not altered,
                'mutation':{'before':before,'after':after,'occurrences':1,'kind':'COUNTERFACTUAL_TEXT'} if altered else None,
                'reference_basis':c['reference']['basis'],'scenario_count':len(values),
                'corpus_role':'PROSPECTIVE_FEASIBILITY_SET_NOT_POPULATION_SAMPLE',
                'model_pretraining_exposure':'UNKNOWN','author_exposure':'Reference construction only; no model outcomes inspected'})
    contract={'version':'paired-evaluation.v1','study_id':'sfc-public-qa-prospective.v1','task':'CONTROLLED_SEMANTIC_TESTS',
        'call_cap':18,'seconds_per_arm':1800,'bytes_per_input':200000,'bytes_per_output':200000,'seed':924,
        'development_families':['gift.fixture','sfc.23ec46','sfc.24ec16'],
        'minimum_families':2,'iid_family_sampling_attested':False,'confidence_error_ppm':50000,
        'maximum_coverage_loss_ppm':0,'criterion_basis':
            'Engineering feasibility only. The convenience sample and proposed references prohibit population ranking or legal-accuracy claims.'}
    save(output/'contract.json',contract);save(output/'cases.json',cases);save(output/'provenance.json',provenance)
    save(output/'qualification-cases.json',[
        {'family':'professional-investors','source_sha256':docs['professional-investors'][0]['sha256'],
         'question':'Q4: a written representation alone is insufficient; Q1-Q3 require holistic product-specific judgment.',
         'status':'RETAINED_NO_COMPLETE_OUTCOME_LABEL','reason':'A written declaration is not a positive CPI assessment oracle; full exemptions require other Code conditions.'},
        {'family':'suitability','source_sha256':docs['suitability'][0]['sha256'],
         'question':'Q1 Annex: likely/unlikely suitability triggers and the sequence of communications.',
         'status':'RETAINED_NO_CATEGORICAL_OUTCOME_LABEL','reason':'Likely/unlikely is defeasible guidance, not a truth-valued full-law trigger.'}])
    study=freeze(contract,cases,output/'frozen')
    save(output/'manifest.json',{'study_hash':digest(study),'files':{str(p.relative_to(output)):raw_digest(p.read_bytes())
        for p in sorted(output.rglob('*')) if p.is_file()}})
    print(f"Prepared {len(cases)} cases in {len(study['families'])} families; reservation {study['required_call_reservation']} calls; 2 additional qualified families retained without invented outcomes.")


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);prepare(parser.parse_args().out)
