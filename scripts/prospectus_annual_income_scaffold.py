"""Create new continuation helpers, retaining sealed annual-v5 methods unchanged."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def replace(text,old,new):
    assert old in text,old
    return text.replace(old,new)
def write(name,text):
    p=ROOT/name
    assert not p.exists(),name
    p.write_text(text)

text=(ROOT/'scripts/prospectus_annual_remaining_program.py').read_text()
for old,new in [
 ('annual-remaining','annual-income'),('prospectus_annual_remaining','prospectus_annual_income'),
 ('reviews/annual-income-443','reviews/annual-income-444'),
 ("HERE = SOURCE / 'attempt-019'","HERE = SOURCE / 'attempt-020'"),
 ("OLD = SOURCE / 'attempt-017'","OLD = SOURCE / 'attempt-019'"),
 ('prospectus-annual-income-policies-2026-10-22.md','prospectus-annual-income-integration-2026-10-22.md'),
 ('bes_annual2010_statement_cells_v5.json.gz','bes_annual2010_statement_cells_v6.json.gz'),
 ('bes_annual2010_statement_cells_v4.json.gz','bes_annual2010_statement_cells_v5.json.gz'),
 ('test_annual_remaining_policies.py','test_annual_income_notes.py'),
 ('scripts/prospectus_annual_income_prepare.py','scripts/prospectus_annual_income_source.py'),
 ('reviews/annual-policy-receipt-442/post-record.json','reviews/annual-remaining-443/post-record.json'),
 ('after-442.json','after-443.json'),('revisions/0443.json','revisions/0444.json'),
 ('< 3360','< 3760'),('< 760*1024**2','< 920*1024**2'),
 ("['revision'] == 442","['revision'] == 443"),('Baseline442required','Baseline443required'),
 ('442 evidence changed','443 evidence changed'),('verified442package','verified443package'),
 ("'consolidation_assets_subsequent_events', FIELD]","'consolidation_assets_subsequent_events', 'remaining_accounting_policies', FIELD]"),
 ("'consolidation_assets_subsequent_events')","'consolidation_assets_subsequent_events','remaining_accounting_policies')"),
 ('expected_442(digest)','expected_443(digest)'),('complete_442_answer_sha256','complete_443_answer_sha256'),
 ('old-v4','old-v5'),('Retain all five existing meaning fields; add historical Notes 2.8–2.23','Preserve six prior reading fields; add group introduction and numerical income Notes5–10'),
 ("names={'public-offset':'offset-and','public-credit':'eir-loss','public-awards':'prvif-no-awards'}","names={'public-credit':'own-credit','public-dash':'dash-imputed','public-loss':'displaced-loss'}"),
 ("'public-offset', 'public-credit', 'public-awards'","'public-credit', 'public-dash', 'public-loss'"),
 ('from scripts.prospectus_annual_income_checks import check, mutations, require','from scripts.prospectus_annual_income_checks import check, mutations, require, tieouts'),
]:text=replace(text,old,new)
start=text.index('def expected_443(digest):');end=text.index('\n\ndef base_products():',start)
text=text[:start]+'''def expected_443(digest):
    from scripts.prospectus_annual_remaining_program import expected_442
    expected=expected_442(digest)
    delta=read(OLD/'ordinary-answer/answer-delta.json.gz')
    require(digest(expected)==delta['baseline_answer_sha256'],'Annual-v5baseline changed')
    for row in delta['changes']:
        target=expected
        for key in row['path'][:-1]:target=target[key]
        target[row['path'][-1]]=row['value']
    require(digest(expected)==delta['actual_answer_sha256'],'Complete443answer reconstruction differs')
    return expected
''' +text[end:]
text=replace(text,"proof = check(combined[FIELD], graph)","proof = {**check(combined[FIELD], graph), 'statement_tieouts':tieouts(combined[FIELD],old)}")
text=replace(text,"proof = check(answer['source_statement_cells'][FIELD], graph)","proof = {**check(answer['source_statement_cells'][FIELD], graph), 'statement_tieouts':tieouts(answer['source_statement_cells'][FIELD],expected['source_statement_cells'])}")
text=replace(text,"'tests/prospectus_successor/test_annual_consolidation_events.py',", "'tests/prospectus_successor/test_annual_remaining_policies.py', 'tests/prospectus_successor/test_annual_consolidation_events.py',")
text=replace(text,"'docs/plans/prospectus-annual-income-integration-2026-10-22.md']", "'docs/plans/prospectus-annual-income-source-review-2026-10-22.md']")
write('scripts/prospectus_annual_income_program.py',text)

text=(ROOT/'scripts/prospectus_annual_remaining_submission.py').read_text()
for old,new in [
 ('prospectus_annual_remaining','prospectus_annual_income'),("old['revision']==442","old['revision']==443"),
 ('Fresh442baseline','Fresh443baseline'),("proposal['revision']=443","proposal['revision']=444"),
 ('annual_remaining_policy_review=','annual_income_review='),
 ('Integrate original Notes2.8–2.23; preserve complete prior five meaning fields and historical inconsistencies','Integrate Note1 introduction and original income Notes5–10 with exact source-cell arithmetic and prior six meaning fields'),
 ('==18','==19'),('Retain18admissions','Retain19admissions'),("['maximum_new_attempts']=19","['maximum_new_attempts']=20"),
 ("['baseline_revision']=443","['baseline_revision']=444"),
 ('Note1 and numerical notes','Note1 group tables, segments and remaining numerical notes'),
 ('Complete443ordinary/installed comparisons and actual-validator receipt; then continue original Note1 and numerical notes with full cumulative history.', 'Complete444ordinary/installed comparisons and actual-validator receipt; then continue original group tables, segments and remaining notes with cumulative history.'),
 ('19admissions;3360cumulative seconds760MiB','20admissions;3760cumulative seconds920MiB'),
 ('Optional annual-v5source readings for original remaining policies','Optional annual-v6original source income tables and group introduction'),
 ('Complete017annual-v4answer retained by018RECORD','Complete019annual-v5answer'),
 ('exact five old meaning fields and72adverse qualifier/order/table cases','exact six prior meaning fields and55adverse qualifier/table cases with independent statement tie-outs'),
 ("'previous_maximum':18,'new_maximum':19","'previous_maximum':19,'new_maximum':20"),
 ('Distinct original Notes2.8–2.23 missing meanings; retain18admissions,receipt rejection,and240conservative seconds; extend2960to3360seconds and600to760MiB','Distinct original income Notes5–10 and introductory group context; retain19admissions,all failures,and240conservative seconds; extend3360to3760seconds and760to920MiB'),
 ("'cumulative_seconds':3360","'cumulative_seconds':3760"),("'cumulative_bytes':760*1024**2","'cumulative_bytes':920*1024**2"),
 ('<760*1024**2','<920*1024**2'),
 ('reviews/annual-policy-receipt-442/post-record.json','reviews/annual-remaining-443/post-record.json'),
 ("'revision_required':443","'revision_required':444"),("program['revision']==443","program['revision']==444"),('Current443admission','Current444admission'),
]:
    # The remaining-scope phrase changes a longer next-action literal first.
    if old.startswith('Complete443') and old not in text:
        old=old.replace('Note1 and numerical notes','Note1 group tables, segments and remaining numerical notes')
    text=replace(text,old,new)
text=replace(text,"'scripts/prospectus_annual_policy_checks.py']", "'scripts/prospectus_annual_policy_checks.py', 'scripts/prospectus_annual_remaining_program.py', 'scripts/prospectus_annual_remaining_reading.py', 'scripts/prospectus_annual_remaining_checks.py']")
write('scripts/prospectus_annual_income_submission.py',text)

text=(ROOT/'tests/prospectus_successor/test_annual_remaining_policies.py').read_text()
for old,new in [
 ('prospectus_annual_remaining','prospectus_annual_income'),
 ('bes_annual2010_statement_cells_v5.json.gz','bes_annual2010_statement_cells_v6.json.gz'),
 ('bes_annual2010_statement_cells_v4.json.gz','bes_annual2010_statement_cells_v5.json.gz'),
 ("['policy_topics'] == 24","['tables'] == 6"),
 ("'consolidation_assets_subsequent_events')","'consolidation_assets_subsequent_events', 'remaining_accounting_policies')"),
 ('range(len(CASES) + 16)','range(len(CASES) + 39)'),('== 112','== 121'),('!= 112','!= 121'),
 ('Shares and options were attributed.','Credit risk contribution is positive in both years.'),
]:text=replace(text,old,new)
text += '''
def test_primary_statement_tieouts():
    from scripts.prospectus_annual_income_checks import tieouts
    graph, supplied_reading = supplied()
    reading = supplied_reading['reading']
    assert tieouts(reading[FIELD], reading)['two_year_tieouts'] == 9


def test_primary_comparator_corruption_refused():
    from scripts.prospectus_annual_income_checks import tieouts
    graph, supplied_reading = supplied()
    reading = deepcopy(supplied_reading['reading'])
    reading['primary_statements']['profile']['reading']['tables']['income']['rows'][0]['cells'][0]['value'] += 1
    with pytest.raises(ValueError, match='tie-out'):
        tieouts(reading[FIELD], reading)
'''
write('tests/prospectus_successor/test_annual_income_notes.py',text)
print('Created income integration helpers; sealed443methods unchanged.')
