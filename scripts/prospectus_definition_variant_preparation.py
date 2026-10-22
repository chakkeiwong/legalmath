"""Source-only omission evidence and finite whitespace cases, before candidate."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_definition_integration as src

HERE=src.AUTH/'reviews/definition-scope-repair-289'
PLAN='docs/plans/prospectus-definition-scope-repair-2026-10-18.md'
METHOD='scripts/prospectus_definition_variant_preparation.py'


def main():
    started=time.monotonic()
    assert not (HERE/'source-supplement.json.gz').exists()
    spec=src.read(src.PREP/'expected-spec.json.gz')
    text=(src.SOURCE/'selected-text.txt').read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==spec['bindings']['selected_text_sha256']
    span=(21547,21576)
    assert text[slice(*span)]=='vorzeitige\nRückzahlungsbetrag'
    ids=('U06-tax-early-amount','U07-makewhole-early-amount')
    previous=[]
    for r in spec['records']:
        if r['id'] in ids:
            intervals=[spec['intervals'][u['interval']] for u in r['uses']]
            assert len(intervals)==4 and all((v['start'],v['end'])!=span for v in intervals)
            previous.append({'record':r['id'],'prior_use_intervals':[[v['start'],v['end']] for v in intervals]})
    pieces=[]
    for i,p in enumerate(spec['source_pieces']):
        a,b=max(span[0],p['start']),min(span[1],p['end'])
        if a<b:
            pieces.append({'source_piece_index':i,'start':a,'end':b,'quote':text[a:b],
                'kind':p['kind'],'original_piece':deepcopy(p)})
    assert sum(p['end']-p['start'] for p in pieces)==span[1]-span[0]
    supplement={'version':'definition-source-supplement.v1','selected_text_sha256':spec['bindings']['selected_text_sha256'],
        'original_records':62,'original_use_associations':610,'original_references':60,
        'source':src.rel(src.SOURCE/'selected-text.txt'),'prior_records':previous,
        'new_occurrence':{'start':span[0],'end':span[1],'quote':text[slice(*span)],'source_pieces':pieces,
            'source_context':{'start':21493,'end':21757,'quote':text[21493:21757]},
            'candidate_record_associations':list(ids),'governing_meaning':None,
            'reading':'Section5(10)(b) refers to5(5); it does not supply the tax-call equality.'},
        'omission_type':'Authored literal forms omit a split-line spelling','denominator_replaced':False,
        'prior_sealed_evidence_changed':False,'candidate_evaluated':False}
    src.save(HERE/'source-supplement.json.gz',supplement)
    src.save(HERE/'original-amount-gold.json',{'text_sha256':spec['bindings']['selected_text_sha256'],
        'forms':['vorzeitige Rückzahlungsbetrag','vorzeitigen Rückzahlungsbetrag'],
        'expected':[[10213,10243],[11831,11861],[19119,19149],[21403,21432],[21547,21576]],
        'meaning_admitted':False,'case_sensitive':True})
    cases=[
        ('ordinary','Alpha Beta',[[0,10]],[[0,10]]),
        ('line-break','Alpha\nBeta',[[0,10]],[[0,10]]),
        ('spaces','Alpha  Beta',[[0,11]],[[0,11]]),
        ('tab','Alpha\tBeta',[[0,10]],[[0,10]]),
        ('nbsp','Alpha\u00a0Beta',[[0,10]],[[0,10]]),
        ('crlf','Alpha\r\nBeta',[[0,11]],[[0,11]]),
        ('paragraph','Alpha\n\nBeta',[[0,11]],[]),
        ('spaced-paragraph','Alpha\n \nBeta',[[0,12]],[]),
        ('region-boundary','Alpha\nBeta',[[0,6],[6,10]],[]),
        ('prefix-compound','pre-Alpha Beta',[[0,14]],[]),
        ('suffix-compound','Alpha Beta-extra',[[0,16]],[]),
        ('word-prefix','XAlpha Beta',[[0,11]],[]),
        ('word-suffix','Alpha Betas',[[0,11]],[]),
        ('punctuation','(Alpha Beta),',[[0,13]],[[1,11]]),
        ('no-dehyphenation','Al-\npha Beta',[[0,12]],[]),
        ('case-sensitive','alpha Beta',[[0,10]],[]),
        ('formfeed','Alpha\fBeta',[[0,10]],[]),
        ('punctuation-gap','Alpha, Beta',[[0,11]],[]),
        ('two-occurrences','Alpha Beta / Alpha\nBeta',[[0,23]],[[0,10],[13,23]])]
    for label,value,regions,expected in cases:
        assert all(0<=a<b<=len(value) for a,b in regions),label
        assert all(0<=a<b<=len(value) for a,b in expected),label
    src.save(HERE/'variant-cases.json',[{'id':label,'text':value,'form':'Alpha Beta','regions':regions,
        'expected':expected} for label,value,regions,expected in cases])
    src.save(HERE/'source-preparation.json',{'status':'PASS','candidate_evaluated':False,
        'new_occurrences':1,'original_source_gold_intervals':5,'authored_variant_cases':len(cases),
        'wall_seconds':time.monotonic()-started,'at':datetime.now(timezone.utc).isoformat(),
        'command':['.venv/bin/python','-m','scripts.prospectus_definition_variant_preparation'],
        'method_sha256':src.sha(ROOT/METHOD),'plan_sha256':src.sha(ROOT/PLAN)})
    src.save(HERE/'source-freeze.json',{p.name:src.sha(p) for p in HERE.iterdir() if p.is_file()})
    print({'status':'PASS','candidate_evaluated':False,'new_source_occurrences':1,'finite_cases':len(cases)})


if __name__=='__main__':
    main()

