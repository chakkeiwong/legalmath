"""Freeze complete supplement expectations without the application candidate."""
from copy import deepcopy
import hashlib
import re
import sys

from scripts import prospectus_definition_integration as old

HERE=old.AUTH/'reviews/definition-scope-repair-289'
METHOD='scripts/prospectus_definition_application_expectations.py'
FORMS=[
    {'id':'amount-nominative','text':'vorzeitige Rückzahlungsbetrag'},
    {'id':'amount-accusative','text':'vorzeitigen Rückzahlungsbetrag'},
    {'id':'holder-day','text':'Rückzahlungstag'},
    {'id':'affiliate','text':'verbundenes Unternehmen'},
    {'id':'custodian','text':'Depotbank'}]
META={'version':'definition-application-supplement.v1','assistance':'EXACT_SOURCE_REVIEWED',
      'original_records':62,'original_use_associations':610,'original_references':60,
      'supplemental_occurrences':1,'supplemental_record_associations':2,
      'original_record_status_changes':False,'general_recall_established':False,
      'client_facts_established':False,'historical_law_resolved':False,
      'automatic_legal_interpretation_established':False}


def main():
    assert not (HERE/'expected-supplement.json.gz').exists()
    for name,expected in old.read(HERE/'application-expected-freeze.json').items():
        assert old.sha(HERE/name)==expected
    source=old.read(HERE/'application-spec.json.gz')
    candidate={'profile':source['profile'],'bindings':source['bindings'],
        'rules':[{**r,'group':'amount' if r['id'] in ('tax','makewhole') else r['id']}
                 for r in source['rules']],
        'occurrences':[{k:c[k] for k in ('id','group','start','end','quote','role')}
                       for c in source['cases']],
        'forms':deepcopy(FORMS),'source_supplement':source['source_supplement'],
        'preserve_unresolved_records':source['preserve_unresolved_records']}
    checksum=hashlib.sha256(old.json.dumps(candidate,sort_keys=True,
                                ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    # contracts.digest uses precisely this canonical JSON serialization.
    from legalmath.prospectus.successor.contracts import digest
    assert digest(candidate)==checksum
    text=(old.SOURCE/'selected-text.txt').read_text()
    proposals=[]
    for case in source['cases']:
        if case['role']=='COMPOUND_COMPONENT':
            continue
        a,b=case['start'],case['end']
        raw=text[a:b]
        label=' '.join(raw.split())
        supplied=[r['id'] for r in FORMS if r['text']==label]
        assert supplied,(case['id'],label)
        # Independent regex partition; do not import the candidate normalizer.
        spans=[[a+m.start(),a+m.end()] for m in re.finditer(r'\s+|[^\s]',raw)]
        assert len(spans)==len(label)
        proposals.append({'start':a,'end':b,'raw':raw,'normalized_form':label,
            'normalization_map':spans,'region':0,'supplied_form_ids':supplied,
            'review_required':True,'governing_scope':None,'meaning':None})
    proposals.sort(key=lambda r:(r['start'],r['end'],r['normalized_form'],r['region']))
    assert len(proposals)==18
    lexical={'version':'supplied-form-discovery.v1','text_sha256':source['bindings']['selected_text_sha256'],
        'uses':proposals,'scope_admitted':False,'meaning_admitted':False,
        'general_recall_established':False,
        'excluded':['morphology','dehyphenation','paragraph crossing','region crossing',
                    'legal scope inference','implicit or missing definitions']}
    expected={**META,'profile':source['profile'],'profile_sha256':checksum,
        'bindings':source['bindings'],'source_supplement':source['source_supplement'],
        'rules':candidate['rules'],'form_discovery':lexical,'applications':source['cases'],
        'preserve_unresolved_records':source['preserve_unresolved_records']}
    old.save(HERE/'candidate-spec.json.gz',candidate)
    old.save(HERE/'expected-supplement.json.gz',expected)
    old.save(HERE/'supplement-expectation-freeze.json',{
        'candidate_implementation_existed':False,'candidate_evaluated':False,
        'method_sha256':old.sha(old.ROOT/METHOD),
        'bindings':{name:old.sha(HERE/name) for name in
                    ('candidate-spec.json.gz','expected-supplement.json.gz')}})
    assert 'legalmath.prospectus.successor.definition_applications' not in sys.modules
    print({'status':'PASS','expected_decisions':25,'expected_lexical_proposals':18,
           'candidate_evaluated':False})


if __name__=='__main__':
    main()
