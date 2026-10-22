"""Create continuation445 helpers without changing sealed methods."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def put(name,text):
    p=ROOT/name
    assert not p.exists(),name
    p.write_text(text)
def rep(t,a,b):
    assert a in t,a
    return t.replace(a,b)

t=(ROOT/'scripts/prospectus_annual_income_program.py').read_text()
for a,b in [
 ('annual-income','annual-group'),('prospectus_annual_income','prospectus_annual_group'),
 ('annual-group-444','annual-group-445'),("HERE = SOURCE / 'attempt-020'","HERE = SOURCE / 'attempt-021'"),("OLD = SOURCE / 'attempt-019'","OLD = SOURCE / 'attempt-020'"),
 ('bes_annual2010_statement_cells_v6.json.gz','bes_annual2010_statement_cells_v7.json.gz'),('bes_annual2010_statement_cells_v5.json.gz','bes_annual2010_statement_cells_v6.json.gz'),
 ('test_annual_income_notes.py','test_annual_group_disclosures.py'),('reviews/annual-remaining-443/post-record.json','reviews/annual-income-444/post-record.json'),('after-443.json','after-444.json'),('revisions/0444.json','revisions/0445.json'),
 ('< 600','< 650'),('< 3760','< 4360'),('< 160*1024**2','< 180*1024**2'),('< 920*1024**2','< 1100*1024**2'),
 ("['revision'] == 443","['revision'] == 444"),('Baseline443required','Baseline444required'),('443 evidence changed','444 evidence changed'),('verified443package','verified444package'),
 ("'remaining_accounting_policies', FIELD]","'remaining_accounting_policies', 'income_notes_and_group_context', FIELD]"),
 ("'remaining_accounting_policies')","'remaining_accounting_policies','income_notes_and_group_context')"),
 ('expected_443(digest)','expected_444(digest)'),('complete_443_answer_sha256','complete_444_answer_sha256'),('Complete443answer','Complete444answer'),('old-v5','old-v6'),
 ('Preserve six prior reading fields; add group introduction and numerical income Notes5–10','Preserve seven prior fields; add original Note1 group disclosures'),
 ("'public-credit', 'public-dash', 'public-loss'","'public-control', 'public-dash', 'public-scope'"),
 ("names={'public-credit':'own-credit','public-dash':'dash-imputed','public-loss':'displaced-loss'}","names={'public-control':'majority','public-dash':'dash-imputed','public-scope':'ascendi-scope'}"),
 ('import check, mutations, require, tieouts','import check, mutations, require'),
 ("{**check(combined[FIELD], graph), 'statement_tieouts':tieouts(combined[FIELD],old)}","check(combined[FIELD], graph)"),
 ("{**check(answer['source_statement_cells'][FIELD], graph), 'statement_tieouts':tieouts(answer['source_statement_cells'][FIELD],expected['source_statement_cells'])}","check(answer['source_statement_cells'][FIELD], graph)"),
 ]:t=rep(t,a,b)
s=t.index('def expected_444(digest):');e=t.index('\n\ndef base_products():',s)
t=t[:s]+'''def expected_444(digest):
    from scripts.prospectus_annual_income_program import expected_443
    expected=expected_443(digest)
    delta=read(OLD/'ordinary-answer/answer-delta.json.gz')
    require(digest(expected)==delta['baseline_answer_sha256'],'Annual-v6 baseline changed')
    for row in delta['changes']:
        target=expected
        for key in row['path'][:-1]:target=target[key]
        target[row['path'][-1]]=row['value']
    require(digest(expected)==delta['actual_answer_sha256'],'Complete444 reconstruction differs')
    return expected
''' + t[e:]
s=t.index('def tests():');e=t.index('\n\ndef expected_444',s)
t=t[:s]+'''def tests_suite(suite):
    suites={
      'new':[TEST],
      'previous':['tests/prospectus_successor/test_annual_income_notes.py','tests/prospectus_successor/test_annual_remaining_policies.py','tests/prospectus_successor/test_annual_consolidation_events.py'],
      'core':['tests/prospectus_successor/test_annual_basis_estimates.py','tests/prospectus_successor/test_statement_cells.py','tests/prospectus_successor/test_english_report_applicability.py']}
    argv=['-q','-p','no:cacheprovider',*suites[suite],'--junitxml='+str(WORK/('tests-'+suite+'.xml'))]
    code='import sys; from pathlib import Path; r=Path.cwd(); sys.path[:0]=[str(r/".localresources/prospectus-preparation/annual-group/candidate/src"),str(r)]; import pytest; raise SystemExit(pytest.main('+repr(argv)+'))'
    command('tests-'+suite,[str(ROOT/'.venv/bin/python'),'-I','-B','-c',code],PREP/'commands')
    return {'status':'PASS','suite':suite,'costs':costs()}
''' +t[e:]
t=rep(t,"parser.add_argument('--kind'","parser.add_argument('--suite',choices=['new','previous','core'])\n    parser.add_argument('--kind'")
t=rep(t,"else globals()[args.action]()","else tests_suite(args.suite) if args.action=='tests' else globals()[args.action]()")
put('scripts/prospectus_annual_group_program.py',t)

t=(ROOT/'scripts/prospectus_annual_income_submission.py').read_text()
for a,b in [
 ('prospectus_annual_income','prospectus_annual_group'),("old['revision']==443","old['revision']==444"),('Fresh443baseline','Fresh444baseline'),("proposal['revision']=444","proposal['revision']=445"),('annual_income_review=','annual_group_review='),
 ('Integrate Note1 introduction and original income Notes5–10 with exact source-cell arithmetic and prior six meaning fields','Integrate original group entity and transaction disclosures with prior seven meanings'),
 ('==19','==20'),('Retain19admissions','Retain20admissions'),("['maximum_new_attempts']=20","['maximum_new_attempts']=21"),("['baseline_revision']=444","['baseline_revision']=445"),
 ('Note1 group tables, segments and remaining numerical notes','segments and remaining numerical notes'),('Complete444ordinary','Complete445ordinary'),('original group tables, segments and remaining notes','original segments and remaining notes'),
 ('20admissions;3760cumulative seconds920MiB;600new seconds160MiB;single changed comparator recovery consumed;no further retry.','21admissions;4360cumulative seconds1100MiB;650new seconds180MiB;at most one changed diagnosed recovery;no unchanged retry.'),
 ('Optional annual-v6original source income tables and group introduction','Optional annual-v7 original group entities and transactions'),('Complete019annual-v5answer','Complete020annual-v6answer'),
 ('exact six prior meaning fields and55adverse qualifier/table cases with independent statement tie-outs','exact seven prior fields and43adverse controls, entity geometry and conditional integer checks'),
 ("'previous_maximum':19,'new_maximum':20","'previous_maximum':20,'new_maximum':21"),
 ('Distinct original income Notes5–10 and introductory group context; retain19admissions,all failures,and240conservative seconds; extend3360to3760seconds and760to920MiB','Distinct original Note1 group disclosures; retain20admissions,all failures,and240conservative seconds; extend3760to4360seconds and920to1100MiB'),
 ("'new_seconds':600","'new_seconds':650"),("'cumulative_seconds':3760","'cumulative_seconds':4360"),("'new_bytes':160*1024**2","'new_bytes':180*1024**2"),("'cumulative_bytes':920*1024**2","'cumulative_bytes':1100*1024**2"),
 ("'changed_recovery_consumed':True,'recovery_review':rel(PREP/'RECOVERY.md')","'changed_recovery_consumed':False"),
 ('<160*1024**2','<180*1024**2'),('<920*1024**2','<1100*1024**2'),('reviews/annual-remaining-443/post-record.json','reviews/annual-income-444/post-record.json'),
 ("'revision_required':444","'revision_required':445"),("program['revision']==444","program['revision']==445"),('Current444admission','Current445admission'),
 ("read(PREP/'commands/tests.json')['exit_code']==0","all(read(PREP/('commands/tests-'+s+'.json'))['exit_code']==0 for s in ('new','previous','core'))"),
 ]:t=rep(t,a,b)
t=rep(t,"'scripts/prospectus_annual_remaining_checks.py']","'scripts/prospectus_annual_remaining_checks.py','scripts/prospectus_annual_income_program.py','scripts/prospectus_annual_income_reading.py','scripts/prospectus_annual_income_checks.py']")
put('scripts/prospectus_annual_group_submission.py',t)

t=(ROOT/'tests/prospectus_successor/test_annual_income_notes.py').read_text()
t=t[:t.index('\ndef test_primary_statement_tieouts')]
for a,b in [('prospectus_annual_income','prospectus_annual_group'),('bes_annual2010_statement_cells_v6.json.gz','bes_annual2010_statement_cells_v7.json.gz'),('bes_annual2010_statement_cells_v5.json.gz','bes_annual2010_statement_cells_v6.json.gz'),("['tables'] == 6","['entities'] == 145"),("'remaining_accounting_policies')","'remaining_accounting_policies', 'income_notes_and_group_context')"),('range(len(CASES) + 39)','range(len(CASES) + 29)'),('== 121','== 100'),('!= 121','!= 100'),('Credit risk contribution is positive in both years.','Control is determined solely by majority ownership.')]:t=rep(t,a,b)
put('tests/prospectus_successor/test_annual_group_disclosures.py',t)
print('Created445 helpers; sealed methods unchanged')
