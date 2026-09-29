"""Local execution against preserved round-15 evidence; no provider access."""
from copy import deepcopy
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from resolution_support import read, save, sha, JDK, AT
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import fidelity_v2, temporal_inputs, editions
from legalmath.ir.evaluate import evaluate
from legalmath.java import decimal_boundary

OLD = ROOT/'artifacts/interpretation/round15'
OUT = ROOT/'artifacts/interpretation/round16'


def pytest_check(out, expression=None, full=False):
    command = [str(ROOT/'.venv/bin/python'), '-m', 'pytest', 'tests' if full else 'tests/assurance/test_round16.py',
               '-q', '-o', 'faulthandler_timeout=0', '--junitxml='+str(out/'tests.xml')]
    if expression:
        command += ['-k', expression]
    save(out/'test-command.json', {'argv': command, 'cpu_gpu': 'CPU; CUDA_VISIBLE_DEVICES=-1',
         'execution_context': 'trusted' if full else 'workspace', 'random_seeds': 'N/A: deterministic fixtures'})
    with (out/'tests.log').open('w') as log:
        p = subprocess.run(command, cwd=ROOT, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'HF_HUB_OFFLINE': '1'},
                           stdout=log, stderr=subprocess.STDOUT, timeout=1800 if full else 600)
    if p.returncode:
        raise LegalMathError('E_INTEGRITY', details=f'Regression failed ({p.returncode}); preserved {out}/tests.log')
    suites = ET.parse(out/'tests.xml').getroot()
    counts = {key: sum(int(s.get(key, 0)) for s in suites.iter('testsuite'))
              for key in ('tests', 'failures', 'errors', 'skipped')}
    if not counts['tests'] or any(counts[k] for k in ('failures', 'errors', 'skipped')):
        raise LegalMathError('E_INTEGRITY', details=counts)
    return counts


def n1(out):
    remaining = read(OLD/'remaining-work.json'); rows = remaining['restored_pair_rows']
    migrated = []
    for row in rows:
        original = row.get('assessment')
        migrated.append({'pair': deepcopy(row), 'scoped_assessment': fidelity_v2.migrate_legacy(original,
            provenance={'path': str((OLD/'remaining-work.json').relative_to(ROOT)), 'sha256': sha(OLD/'remaining-work.json')})
            if original else None, 'status': 'SCOPED_REASSESSMENT_REQUIRED' if original else 'ORIGINAL_PENDING_RETAINED'})
    ids = lambda values: {(r['case_id'], r['claim_id'], r['candidate_id']) for r in values}
    assert len(rows) == len(migrated) == len(ids(rows)) == 232
    assert ids(rows) == ids([r['pair'] for r in migrated])
    for old, new in zip(rows, migrated):
        assert old == new['pair']
        if new['scoped_assessment']:
            assert new['scoped_assessment']['legacy'] == old['assessment']
    save(out/'lossless-migration.json', migrated)
    save(out/'fidelity-v2.schema.json', fidelity_v2.FidelityV2.model_json_schema())
    counts = pytest_check(out, 'separate_advertising or relevant_omitted or missing_authority or relational_disagreement or legacy_migration or v2_rejects')
    return {'status': 'LOSSLESS_SCOPED_CONTRACT_IMPLEMENTED', 'total_pairs': len(migrated),
            'legacy_assessments_preserved': sum(r['scoped_assessment'] is not None for r in migrated),
            'new_source_judgments': 0, 'tests': counts, 'pruned_pairs': [], 'release_eligible': False}


def n2(out):
    from assurance_round15_witnesses import fixtures, world_pairs
    repairs = read(ROOT/'artifacts/interpretation/round14/live-reviewed/repairs.json')
    children = [c for p in repairs for c in p['record']['encodings'] if c.get('bundle')]
    original_rows = []
    for child in children:
        for c in fixtures(child):
            result = evaluate(c['bundle'], c['snapshot'], c['rule_id'], c['valid_at'], c['known_at'])
            assert result['status'] == c['expected']['status']
            original_rows.append({'case': c, 'result': result})
    start='2026-01-28T00:00:00.000000Z'; cutoff='2026-01-29T04:00:00.000000Z'
    early='2026-01-29T03:00:00.000000Z'; late='2026-01-29T05:00:00.000000Z'
    cover = {'str_id': 'str.s', 'kinds': ['CONTACT'], 'from_inclusive': start,
             'through_inclusive': cutoff, 'recorded_at': cutoff, 'evidence_ids': ['history.assertion']}
    rows=[]
    for name, when, subject, recorded, expected in (
        ('earlier_same_report',early,'str.s',early,'TRUE'), ('at_cutoff',cutoff,'str.s',cutoff,'TRUE'),
        ('later_same_report',late,'str.s',late,'FALSE'), ('other_report',early,'str.other',early,'FALSE'),
        ('not_yet_known',early,'str.s',late,'FALSE')):
        event = {'event_id':'contact.'+name, 'str_id':subject,'kind':'CONTACT','related_event_id':None,
                 'occurred_at':when,'recorded_at':recorded,'status':'CONFIRMED','evidence_ids':['event.evidence']}
        inputs={'events':[event],'coverage':[cover],'str_id':'str.s','kind':'CONTACT','since':start,
                'assessment_at':cutoff,'known_at':cutoff}
        result=temporal_inputs.project(**inputs);assert result['status']==expected
        rows.append({'name':name,'input':inputs,'expected':expected,'result':result})
    contexts = [temporal_inputs.context(bundle_interval={k:c['bundle'][k] for k in ('valid_from','valid_until')},
        source_interval=None, documents={}, assessment_at=cutoff, known_at=AT) for c in children]
    assert all(c['status']=='BUNDLE_TIME_UNSUPPORTED' for c in contexts)
    save(out/'retained-child-cases.json',original_rows);save(out/'contact-projections.json',rows)
    save(out/'retained-world-pairs.json',world_pairs());save(out/'time-contexts.json',contexts)
    counts=pytest_check(out,'contact_same or absence_needs or resubmission_needs or historical_bundle')
    return {'status':'EVENT_DISTINCTIONS_IMPLEMENTED','original_child_cases':len(original_rows),
            'historical_refusals_retained':sum(r['result']['status']=='ERROR' for r in original_rows),
            'contact_projections':len(rows),'tests':counts,'source_effectiveness':'NOT_ESTABLISHED',
            'performance_children':'UNENCODED','release_eligible':False}


def decimal_fixtures():
    def request(value, objective=False):
        def known(typ, v):return {'type':typ,'status':'known','value':v,'valid_from':AT,'valid_until':None,
                                  'recorded_at':AT,'evidence_ids':['fixture.host']}
        return {'profile':decimal_boundary.PROFILE,'subject_id':'host.case','valid_at':AT,'known_at':AT,'mode':'draft',
                'facts':{'fund_manager':known('bool',True),'va_objective':known('bool',objective),
                         'intended_va_percent':known('decimal_percent',value)}}
    specs=[('9.999',False,'FALSE'),('10',False,'TRUE'),('10.001',False,'TRUE'),
           ('9.999999999999',False,'FALSE'),('10.000000000001',False,'TRUE'),('0',True,'TRUE'),('0',False,'FALSE'),
           ('9.'+'9'*62,False,'FALSE'),('10.'+'0'*60+'1',False,'TRUE'),('-1',False,'FALSE'),('-0.000',False,'FALSE')]
    rows=[{'id':'valid.'+str(i),'request':request(v,obj),'expected':{'boundary_status':'ACCEPTED','status':s}}
          for i,(v,obj,s) in enumerate(specs)]
    for i,v in enumerate(['1e1','NaN','Infinity','+10','01',' 10','10.','.1','1,0','1'*65,True,10,'１０']):
        rows.append({'id':'malformed.'+str(i),'request':request(v),'expected':{'boundary_status':'REJECTED'}})
    absent=request('10');absent['facts'].pop('intended_va_percent')
    conflict=request('10');conflict['facts']['intended_va_percent']={
        'type':'decimal_percent','status':'conflict','evidence_ids':['first','second']}
    rows.extend([{'id':ident,'request':value,'expected':{'boundary_status':'ACCEPTED','status':expected}}
                 for ident,value,expected in [('missing',absent,'UNKNOWN'),('conflict',conflict,'CONFLICT')]])
    for i,denom in enumerate(['0','-1','1.5','01']):
        value=request('10');value['facts']['va_bps_denominator']={'value':denom}
        rows.append({'id':'bypass.'+str(i),'request':value,'expected':{'boundary_status':'REJECTED'}})
    return rows


def n3(out):
    old=read(OLD/'phase-results.json')['P5']['result']['rational_extension']
    bundle=old['cases'][0]['bundle'];cases=decimal_fixtures();save(out/'cases-before-execution.json',cases)
    built=decimal_boundary.build(bundle,out/'java',JDK,profile=decimal_boundary.PROFILE)
    actual=decimal_boundary.run(built,[c['request'] for c in cases],JDK);rows=[]
    for c,j in zip(cases,actual):
        p=decimal_boundary.evaluate_request(bundle,c['request']);expected=c['expected']
        assert j['boundary_status']==p['boundary_status']==expected['boundary_status'],c['id']
        if expected['boundary_status']=='ACCEPTED':
            assert j['result']['status']==p['result']['status']==expected['status'],c['id']
            assert j['snapshot']==p['snapshot'],c['id']
            omit={'engine_version','result_hash'}
            assert {k:v for k,v in j['result'].items() if k not in omit}=={k:v for k,v in p['result'].items() if k not in omit}
        rows.append({'case_id':c['id'],'java':j,'python':p})
    save(out/'results.json',rows);save(out/'build.json',built)
    counts=pytest_check(out,'packaged_java')
    return {'status':'PACKAGED_JAVA_DECIMAL_BOUNDARY_VERIFIED','cases':len(cases),
        'rejected':sum(r['java']['boundary_status']=='REJECTED' for r in rows),'tests':counts,
        'entrypoint':built['manifest']['entry_class'],'jar':built['jar'],
        'raw_snapshot_api_migrated':False,'permissible_exposure_domain':'NOT_ESTABLISHED','release_eligible':False}


def n4(out):
    from pypdf import PdfReader
    import pypdf
    old=read(OLD/'source-edition-review/review.json');pdf=ROOT/old['source_pdf']
    assert sha(pdf)==old['source_sha256']
    pages=[p.extract_text() for p in PdfReader(pdf).pages];assert len(pages)==135
    assert 'Appendix 7' in pages[73] and 'Appendix 7a' in pages[94]
    assert '2019 2023' in pages[94] and '2023' in pages[73]
    text=pages[75];cut=text.index('1  These Terms and Conditions');nextpage=pages[76];application=nextpage.index('Application')
    def provision(ident,edition,page,start,end,links,relationship):
        return {'provision_id':ident,'edition_id':edition,'page':page,'start':start,'end':end,
                'quote':pages[page-1][start:end],'required_links':links,'relationship':relationship}
    m={'source_sha256':sha(pdf),'page_hashes':[raw_digest(p.encode()) for p in pages],
       'editions':[{'edition_id':'appendix7.oct2023','kind':'CLEAN','first_page':74,'last_page':94,'printed_edition':'October 2023'},
                   {'edition_id':'appendix7a.revisions','kind':'MARKED_CHANGES','first_page':95,'last_page':135,'printed_edition':'October 2019 2023'}],
       'provisions':[provision('definitions','appendix7.oct2023',76,0,cut,['structure.footnote','persistence.notice','application'],'SECTION'),
                     provision('structure.footnote','appendix7.oct2023',76,cut,len(text),[],'FOOTNOTE'),
                     provision('persistence.notice','appendix7.oct2023',77,0,application,[],'CONTINUATION'),
                     provision('application','appendix7.oct2023',77,application,len(nextpage),[],'APPLICATION'),
                     provision('marked.definitions','appendix7a.revisions',99,0,len(pages[98]),[],'SECTION')],
       'structural_review':'Page partition retained from round-15 rendered inspection; paragraph/footnote offsets inspected in round 16.',
       'unresolved_authority_questions':[q['proposition_missing'] for q in read(OLD/'remaining-work.json')['authority_questions']]+
           ['This historical pack carries a supersession notice; establish applicable source edition and effective interval for the selected assessment.']}
    save(out/'pages.json',pages);save(out/'edition-manifest.json',m)
    chosen=['definitions','structure.footnote','persistence.notice','application']
    value=editions.select(pdf,pages,m,expected_manifest_hash=digest(m),edition_id='appendix7.oct2023',provision_ids=chosen)
    negatives=[]
    for label,selection,edition in [('mixed',chosen+['marked.definitions'],'appendix7.oct2023'),
        ('missing_footnote',[i for i in chosen if i!='structure.footnote'],'appendix7.oct2023'),
        ('missing_continuation',[i for i in chosen if i!='persistence.notice'],'appendix7.oct2023'),
        ('marked_active',['marked.definitions'],'appendix7a.revisions')]:
        try:editions.select(pdf,pages,m,expected_manifest_hash=digest(m),edition_id=edition,provision_ids=selection)
        except LegalMathError as e:negatives.append({'case':label,'error':e.code})
        else:raise LegalMathError('E_INTEGRITY',details=label)
    save(out/'selected-packet.json',value);save(out/'contamination-tests.json',negatives)
    counts=pytest_check(out,'edition_')
    return {'status':'CLEAN_EDITION_PACKET_BOUND','selected_units':len(value['packet']['units']),
            'negative_cases':negatives,'extractor':'pypdf '+pypdf.__version__,'source_pdf_sha256':sha(pdf),
            'supersession_notice':pages[0],'tests':counts,'source_effectiveness':'NOT_ESTABLISHED','release_eligible':False}


def n5(out):
    counts=pytest_check(out,full=True)
    pending=read(OLD/'remaining-work.json');save(out/'remaining-work.json',pending)
    return {'status':'FULL_REGRESSION_PASSED','tests':counts,'remaining_work_unchanged':True,
            'remaining_work_sha256':sha(OLD/'remaining-work.json'),'legal_accuracy_established':False,'release_eligible':False}


if __name__=='__main__':
    phase, directory=sys.argv[1:];out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    result={'N1':n1,'N2':n2,'N3':n3,'N4':n4,'N5':n5}[phase](out)
    save(out/'phase-output.json',result)
    print(json.dumps(result))
