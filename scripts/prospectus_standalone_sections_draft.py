"""Create the reviewed standalone-section execution harness without evaluating it."""
from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
AUTH=ROOT/'docs/implementation/prospectus-execution-authority'
PREP=AUTH/'reviews/standalone-sections-348'
target=ROOT/'scripts/prospectus_standalone_sections.py';assert not target.exists()
text=(ROOT/'scripts/prospectus_reference_addresses.py').read_text()
text=text.replace('from scripts import prospectus_reference_scope_header_repair as prior',
    'from scripts import prospectus_reference_label_grammar as prior')
text=text.replace('prospectus_reference_addresses','prospectus_standalone_sections')
text=text.replace('prospectus-reference-addresses-2026-10-19.md','prospectus-standalone-sections-2026-10-19.md')
text=text.replace('reference-addresses-345','standalone-sections-348')
text=text.replace('attempt-084','attempt-087')
text=text.replace('test_reference_addresses.py','test_standalone_sections.py')
text=text.replace('reference_addresses_spec.json','standalone_sections_spec.json')
text=text.replace('reference_addresses.py','standalone_sections.py')
text=text.replace('reference-addresses.v1','standalone-sections.v1')
text=text.replace('reference_addresses','standalone_sections')
text=text.replace('PRODUCTS = prior.PRODUCTS','PRODUCTS = prior.previous.PRODUCTS')
text=text.replace("'revisions/0345.json'","'revisions/0348.json'")
text=text.replace("program['revision'] == 344","program['revision'] == 347")
text=text.replace('len(attempts) == 83','len(attempts) == 86')
text=text.replace("proposal['revision'] = 345","proposal['revision'] = 348")
text=text.replace("maximum_new_attempts'] = 84","maximum_new_attempts'] = 87")
text=text.replace("routes['baseline_revision'] = 345","routes['baseline_revision'] = 348")
text=text.replace("'previous_maximum': 83, 'new_maximum': 84","'previous_maximum': 86, 'new_maximum': 87")
text=text.replace("'revision': 345","'revision': 348")
text=text.replace('84 admissions;','87 admissions;')
text=text.replace('reference_scope_profile=None, expected_reference_scope_profile_sha256=None',
    'reference_addresses_profile=None, expected_reference_addresses_profile_sha256=None')
text=text.replace("'paragraph_references', 'reference_scope')",
    "'reference_scope', 'reference_addresses')")
text=text.replace("'paragraph_references', 'reference_scope', 'standalone_sections')",
    "'reference_scope', 'reference_addresses', 'standalone_sections')")
text=text.replace("prior.METHOD,","'scripts/prospectus_reference_label_grammar.py',")
text=text.replace("pre_admission_review=rel(PREP / 'METHOD-REVIEW.md')",'pre_admission_review=PLAN')
text=text.replace("'review': rel(PREP / 'METHOD-REVIEW.md')","'review': PLAN")
text=text.replace("reference_address_review=","standalone_section_review=")
text=text.replace('Resolve source-bound structural reference addresses, parents and ranges while retaining legal meaning uncertainty',
    'Account for standalone section references and statutory chains while preserving original answers and legal uncertainty')
text=text.replace('Verify 29 structural reference readings; reconcile original target/definition/statutory gaps against exact evidence',
    'Verify50section signs and18standalone expressions; continue original definition and historical-law requirements')
text=text.replace("snapshot['combined_accounted_seconds'] + 1150","snapshot['combined_accounted_seconds'] + 1000")
text=text.replace('128 * 1024**2','96 * 1024**2')
text=text.replace('Current citation contexts still contain no destinations or parent/range resolution',
    'Paragraph addressing leaves19standalone section signs without dedicated source classification')
text=text.replace('29 independent structural readings and complete installed equality',
    '50sign partition,18standalone expressions and complete installed equality')
text=text.replace("'limits_extended': True,","'limits_extended': False,")
text=text.replace("'previous_seconds_bound': 21600, 'previous_bytes_bound': 3200 * 1024**2,",
    "'previous_seconds_bound': 24000, 'previous_bytes_bound': 3456 * 1024**2,")
text=text.replace('Old remaining allowance cannot fit a full paired consumer/package trial; preserve all costs',
    'Current cumulative allowance fits the bounded forecast; preserve all earlier costs')
begin=text.index('def controls():');end=text.index('\ndef installed():',begin)
text=text[:begin]+'''def controls():
    products,old=baseline();actual=read(HERE/'ordinary-answer.json.gz');refused={}
    for kind in ('sign-delete','wrong-heading','chain-member-delete','target-change','source-map-delete',
                 'statute-as-contract','false-history','false-completion','prior-answer'):
        bad=deepcopy(actual);report=bad[oracle.KEY];row=report['references'][0]
        if kind=='sign-delete':report['signs'].pop()
        elif kind=='wrong-heading':report['signs'][0]['classification']='STANDALONE_EXPRESSION'
        elif kind=='chain-member-delete':next(r for r in report['references'] if r['start']==35946)['members'].pop()
        elif kind=='target-change':row['targets'][0]['section']='99'
        elif kind=='source-map-delete':row['targets'][0]['source_projection'].pop()
        elif kind=='statute-as-contract':
            r=next(r for r in report['references'] if r['statute']=='AktG');r['targets']=row['targets'];r['status']='STRUCTURAL_SECTION'
        elif kind=='false-history':row['historical_application_established']=True
        elif kind=='false-completion':report['whole_task_complete']=True
        else:bad['questions']['Q1']['status']='YES'
        bad['report_sha256']=digest({k:v for k,v in bad.items() if k!='report_sha256'})
        try:oracle.verify(bad,old,products,read(PREP/'expected.json'))
        except AssertionError:refused[kind]=True
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused})
    return {'status':'PASS','refused':len(refused)}

''' + text[end:]
begin=text.index('def seal():');end=text.index('\ndef main():',begin)
text=text[:begin]+'''def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SOURCE_STANDALONE_SECTIONS',**read(HERE/'independent-verification.json'),
        'ordinary_installed_equal':True,'resources':costs(),
        'next_action':'Continue original definition discovery,implicit-reference review and historical-law scope'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(PRODUCTS),'wall_time':costs(),
        'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text(RESULT_NOTE)
    return result

''' + text[end:]
note='''# Standalone sections retain source and statutory scope

All fifty printed section-sign occurrences are accounted for: fifteen headings,
sixteen signs within prior paragraph contexts, and nineteen standalone signs.
Those nineteen signs form eighteen expressions: fifteen structural section
references and three statutory expressions, including the two-member SchVG
chain. Exact source projections and complete prior answers remain preserved.
The fresh installed consumer matches the normal complete answer.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain finite standalone-section capability|Frozen source partition,destinations and installed equality|Scope/source/false-acceptance mutations refused|Implicit grammar,semantic subsets,historical applicability|Continue original definition and statutory requirements|General recall,legal truth or whole build|

The strongest alternative explanation is an unlisted drafting convention. A
source mismatch would require reviewed repair; finite exact coverage does not
establish exhaustive legal interpretation. All previous answers remain equal.
'''
text=text.replace("if __name__ == '__main__':",'RESULT_NOTE = '+repr(note)+"\n\nif __name__ == '__main__':")
ast.parse(text);target.write_text(text)
worker=ROOT/'scripts/prospectus_standalone_sections_installed.py';assert not worker.exists()
worker.write_text((ROOT/'scripts/prospectus_reference_addresses_installed.py').read_text().replace('successor.reference_addresses','successor.standalone_sections'))
print('Created standalone-section runner and isolated worker; candidate unevaluated')
