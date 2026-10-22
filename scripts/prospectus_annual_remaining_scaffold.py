"""Create new bounded continuation helpers without changing sealed prior scripts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(text, old, new):
    assert old in text, old
    return text.replace(old, new)


def write(name, text):
    path = ROOT / name
    assert not path.exists(), name
    path.write_text(text)


text = (ROOT / 'scripts/prospectus_annual_policy_program.py').read_text()
for old, new in [
    ('from scripts.prospectus_annual_policy_source import WORK', "WORK = ROOT / '.localresources/prospectus-preparation/annual-remaining'"),
    ('prospectus_annual_policy_reading', 'prospectus_annual_remaining_reading'),
    ('prospectus_annual_policy_checks', 'prospectus_annual_remaining_checks'),
    ('reviews/annual-policy-441', 'reviews/annual-remaining-443'),
    ("HERE = SOURCE / 'attempt-017'", "HERE = SOURCE / 'attempt-019'"),
    ("OLD = SOURCE / 'attempt-016'", "OLD = SOURCE / 'attempt-017'"),
    ('prospectus-annual-consolidation-events-2026-10-22.md', 'prospectus-annual-remaining-policies-2026-10-22.md'),
    ('prospectus_annual_policy_program.py', 'prospectus_annual_remaining_program.py'),
    ('bes_annual2010_statement_cells_v4.json.gz', 'bes_annual2010_statement_cells_v5.json.gz'),
    ('bes_annual2010_statement_cells_v3.json.gz', 'bes_annual2010_statement_cells_v4.json.gz'),
    ('test_annual_consolidation_events.py', 'test_annual_remaining_policies.py'),
    ("'scripts/prospectus_annual_policy_source.py', 'scripts/prospectus_annual_policy_render.py',", "'scripts/prospectus_annual_remaining_prepare.py', 'scripts/prospectus_annual_remaining_scaffold.py',"),
    ('prospectus-annual-policy-source-review-2026-10-22.md', 'prospectus-annual-remaining-policies-2026-10-22.md'),
    ('reviews/annual-basis-440/post-record.json', 'reviews/annual-policy-receipt-442/post-record.json'),
    ('after-440.json', 'after-442.json'), ('source-review.json', 'preparation.json'),
    ('prospectus_annual_policy_submission.py', 'prospectus_annual_remaining_submission.py'),
    ('revisions/0441.json', 'revisions/0443.json'), ('< 2960', '< 3360'), ('< 600*1024**2', '< 760*1024**2'),
    ("['revision'] == 440", "['revision'] == 442"), ('Baseline440required', 'Baseline442required'),
    ('verified440package', 'verified442package'),
    ("'capital_notes', 'basis_estimates_pronouncements', FIELD]", "'capital_notes', 'basis_estimates_pronouncements', 'consolidation_assets_subsequent_events', FIELD]"),
    ('annual-policies/candidate/src', 'annual-remaining/candidate/src'),
    ("'tests/prospectus_successor/test_annual_basis_estimates.py'", "'tests/prospectus_successor/test_annual_consolidation_events.py', 'tests/prospectus_successor/test_annual_basis_estimates.py'"),
    ('expected_440(digest)', 'expected_442(digest)'),
    ('complete_440_answer_sha256', 'complete_442_answer_sha256'), ('old-v3', 'old-v4'),
    ('Retain existing meanings; add Note 2.2–2.7 and Note 47 attributed source statements', 'Retain all five existing meaning fields; add historical Notes 2.8–2.23'),
    ("('primary_statements','eps_cash_notes','capital_notes','basis_estimates_pronouncements')", "('primary_statements','eps_cash_notes','capital_notes','basis_estimates_pronouncements','consolidation_assets_subsequent_events')"),
    ("names={'public-control':'control','public-loan':'no-double-count','public-event':'opening'}", "names={'public-offset':'offset-and','public-credit':'eir-loss','public-awards':'prvif-no-awards'}"),
    ("'public-control', 'public-loan', 'public-event'", "'public-offset', 'public-credit', 'public-awards'"),
]:
    text = replace(text, old, new)
start = text.index('def expected_442(digest):')
end = text.index('\n\ndef base_products():', start)
text = text[:start] + '''def expected_442(digest):
    from scripts.prospectus_annual_policy_program import expected_440
    expected = expected_440(digest)
    delta = read(OLD/'ordinary-answer/answer-delta.json.gz')
    require(digest(expected) == delta['baseline_answer_sha256'], 'Annual-v4 baseline changed')
    for row in delta['changes']:
        target = expected
        for key in row['path'][:-1]:
            target = target[key]
        target[row['path'][-1]] = row['value']
    require(digest(expected) == delta['actual_answer_sha256'], 'Complete442 answer reconstruction differs')
    return expected
''' + text[end:]
text = replace(text, "require(not (WORK / 'candidate').exists(), 'No unchanged candidate retry')", """require(not (WORK / 'candidate').exists(), 'No unchanged candidate retry')
    from legalmath.prospectus.execution_authority import Authority
    a = Authority(ROOT)
    require(a.retained_evidence_valid(read(AUTH/'reviews/annual-policy-receipt-442/post-record.json')['event']), '442 evidence changed')""")
# This helper needs the authority import during preparation; worker inserts its own target first.
text = replace(text, "from legalmath.prospectus.execution_authority import Authority\n    a = Authority(ROOT)", "sys.path.insert(0, str(ROOT/'src'))\n    from legalmath.prospectus.execution_authority import Authority\n    a = Authority(ROOT)")
write('scripts/prospectus_annual_remaining_program.py', text)

text = (ROOT/'tests/prospectus_successor/test_annual_consolidation_events.py').read_text()
for old,new in [
    ('prospectus_annual_policy_reading','prospectus_annual_remaining_reading'),
    ('prospectus_annual_policy_checks','prospectus_annual_remaining_checks'),
    ('bes_annual2010_statement_cells_v4.json.gz','bes_annual2010_statement_cells_v5.json.gz'),
    ('bes_annual2010_statement_cells_v3.json.gz','bes_annual2010_statement_cells_v4.json.gz'),
    ("['events'] == 3","['policy_topics'] == 24"),
    ("'capital_notes', 'basis_estimates_pronouncements')", "'capital_notes', 'basis_estimates_pronouncements', 'consolidation_assets_subsequent_events')"),
    ('range(len(CASES) + 2)', 'range(len(CASES) + 16)'),
    ("== 187", "== 112"), ("!= 187", "!= 112"),
    ('The branch opened.', 'Shares and options were attributed.'),
]:
    text=replace(text,old,new)
write('tests/prospectus_successor/test_annual_remaining_policies.py',text)

text=(ROOT/'scripts/prospectus_annual_policy_submission.py').read_text()
for old,new in [
    ('prospectus_annual_policy_program','prospectus_annual_remaining_program'),
    ('prospectus_annual_policy_submission.py','prospectus_annual_remaining_submission.py'),
    ("old['revision']==440", "old['revision']==442"), ('Fresh440baseline', 'Fresh442baseline'),
    ("proposal['revision']=441", "proposal['revision']=443"),
    ('annual_policy_review=', 'annual_remaining_policy_review='),
    ('Integrate original Note2.2–2.7 conditions and Note47 events; preserve complete prior annual meanings', 'Integrate original Notes2.8–2.23; preserve complete prior five meaning fields and historical inconsistencies'),
    ('==16', '==18'), ('Retain16admissions', 'Retain18admissions'),
    ("['maximum_new_attempts']=17", "['maximum_new_attempts']=19"),
    ("['baseline_revision']=441", "['baseline_revision']=443"),
    ('remaining Note2 policies, Note1 and numerical notes', 'Note1 and numerical notes'),
    ('Complete441ordinary/installed comparisons and record; then read remaining original policies and numerical notes with full cumulative history.', 'Complete443ordinary/installed comparisons and actual-validator receipt; then continue original Note1 and numerical notes with full cumulative history.'),
    ('17admissions;2960cumulative seconds600MiB', '19admissions;3360cumulative seconds760MiB'),
    ('Optional annual-v4source readings for original missing policies/events', 'Optional annual-v5source readings for original remaining policies'),
    ('Complete016annual-v3answer with historical annual-v2preservation', 'Complete017annual-v4answer retained by018RECORD'),
    ('exact old meanings and38adverse qualifier/order cases', 'exact five old meaning fields and72adverse qualifier/order/table cases'),
    ("'previous_maximum':16,'new_maximum':17", "'previous_maximum':18,'new_maximum':19"),
    ('Distinct original Note2.2–2.7 and47missing meanings; retain all costs; explicit2560to2960seconds and448to600MiB extension', 'Distinct original Notes2.8–2.23 missing meanings; retain18admissions,receipt rejection,and240conservative seconds; extend2960to3360seconds and600to760MiB'),
    ("'cumulative_seconds':2960", "'cumulative_seconds':3360"),
    ("'cumulative_bytes':600*1024**2", "'cumulative_bytes':760*1024**2"),
    ('<600*1024**2', '<760*1024**2'),
    ('reviews/annual-basis-440/post-record.json','reviews/annual-policy-receipt-442/post-record.json'),
    ("'revision_required':441", "'revision_required':443"),
    ("program['revision']==441", "program['revision']==443"), ('Current441admission', 'Current443admission'),
    ("{'status':'PASS','task_complete':False", "{'task':TASK,'status':'PASS','task_complete':False"),
]:
    text=replace(text,old,new)
text=replace(text, "'scripts/prospectus_2010_capital_product_cases.py', 'scripts/prospectus_2010_annual_cases.py']", "'scripts/prospectus_2010_capital_product_cases.py', 'scripts/prospectus_2010_annual_cases.py', 'scripts/prospectus_annual_policy_program.py', 'scripts/prospectus_annual_policy_reading.py', 'scripts/prospectus_annual_policy_checks.py']")
text=replace(text,"from legalmath.prospectus.execution_authority import Authority, digest, file_hash", "from legalmath.prospectus.execution_authority import Authority, digest, file_hash\nfrom legalmath.prospectus.execution_workers import validate")
where=text.index('\ndef freeze():')
text=text[:where]+'''
def preflight(tasks):
    cases = {'valid-partial': {'task':TASK,'status':'PASS','task_complete':False,'whole_program_complete':False},
             'missing-task': {'status':'PASS'}, 'wrong-task': {'task':'wrong','status':'PASS'},
             'failed': {'task':TASK,'status':'FAIL'}}
    checks=[]
    for name,value in cases.items():
        folder=PREP/'preflight'/name
        save(folder/'result.json',value)
        try:
            disposition=validate(ROOT,folder,tasks[TASK])
        except ValueError as exc:
            require(name!='valid-partial' and str(exc)=='Worker result failed or belongs to another task','Unexpected receipt refusal')
            checks.append({'case':name,'refused':True})
        else:
            require(name=='valid-partial' and disposition is False,'Receipt must yield partial RECORD only')
            checks.append({'case':name,'partial_record_only':True})
    save(PREP/'preflight.json',{'status':'PASS','checks':checks})

''' + text[where:]
text=replace(text,"candidate=read(PREP/'candidate.json')", "preflight(tasks)\n    candidate=read(PREP/'candidate.json')")
text=replace(text,"save(HERE/'run-manifest.json'", "require(validate(ROOT,HERE,Authority(ROOT).spec()[1][TASK]) is False,'Actual receipt must be partial')\n    save(HERE/'run-manifest.json'")
write('scripts/prospectus_annual_remaining_submission.py',text)
print('Created new continuation helpers and tests; sealed helpers unchanged.')
