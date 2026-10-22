"""Prepare a bounded source-definition harness; never evaluate its candidate."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / 'scripts/prospectus_unquoted_definitions.py'
assert not target.exists()
text = (ROOT / 'scripts/prospectus_standalone_sections.py').read_text()


def replace(old, new, count=1):
    global text
    assert text.count(old) == count, old
    text = text.replace(old, new)


replace('from scripts import prospectus_reference_label_grammar as prior',
        'from scripts import prospectus_standalone_sections as prior')
text = text.replace('prospectus_standalone_sections', 'prospectus_unquoted_definitions')
# Restore the predecessor import after changing this runner's module names.
replace('from scripts import prospectus_unquoted_definitions as prior',
        'from scripts import prospectus_standalone_sections as prior')
text = text.replace('standalone-sections-348', 'unquoted-definitions-349')
text = text.replace('attempt-087', 'attempt-088')
text = text.replace('prospectus-standalone-sections-2026-10-19.md',
                    'prospectus-unquoted-definitions-2026-10-19.md')
text = text.replace('test_standalone_sections.py', 'test_unquoted_definitions.py')
text = text.replace('standalone_sections_spec.json', 'unquoted_definitions_spec.json')
text = text.replace('standalone_sections.py', 'unquoted_definitions.py')
text = text.replace('standalone-sections.v1', 'unquoted-definitions.v1')
replace('PRODUCTS = prior.previous.PRODUCTS', 'PRODUCTS = prior.PRODUCTS')
replace('BYTES_BOUND = 3456 * 1024**2', 'BYTES_BOUND = 3584 * 1024**2')
replace("'revisions/0348.json'", "'revisions/0349.json'")
replace("program['revision'] == 347", "program['revision'] == 348")
replace('len(attempts) == 86', 'len(attempts) == 87')
replace("proposal['revision'] = 348", "proposal['revision'] = 349")
replace("maximum_new_attempts'] = 87", "maximum_new_attempts'] = 88")
replace("routes['baseline_revision'] = 348", "routes['baseline_revision'] = 349")
replace("'previous_maximum': 86, 'new_maximum': 87", "'previous_maximum': 87, 'new_maximum': 88")
replace("'revision': 348", "'revision': 349")
replace("pre_admission_review=PLAN", "pre_admission_review=rel(PREP / 'METHOD-REVIEW.md')")
replace("'review': PLAN, 'forecast': forecast", "'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast")
replace("'target_claim': 'Unique structural containers under the declared source hierarchy'",
        "'target_claim': 'Exact syntactic unquoted naming events with printed restrictions; no legal meaning admission'")

# Append an ordinary optional profile after the complete predecessor answer.
begin = text.index('    signature = ')
end = text.index("    profile = {k: spec[k]", begin)
text = text[:begin] + '''    signature = 'standalone_sections_profile=None, expected_standalone_sections_profile_sha256=None):'
    assert service.count(signature) == 1
    service = service.replace(signature, 'standalone_sections_profile=None, expected_standalone_sections_profile_sha256=None,\\n'
                              '            unquoted_definitions_profile=None, expected_unquoted_definitions_profile_sha256=None):')
    marker = '    return {**result, "report_sha256": digest(result)}\\n'
    assert service.count(marker) == 1
    block = """    if unquoted_definitions_profile is not None:
        from .unquoted_definitions import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, unquoted_definitions_profile, root,
            expected_profile_sha256=expected_unquoted_definitions_profile_sha256))
    elif expected_unquoted_definitions_profile_sha256 is not None:
        raise ValueError('Unquoted-definition profile pin supplied without a profile')
"""
    service = service.replace(marker, block + marker)
    (PREP / 'candidate/service.py').write_text(service)
    profiles = (ROOT / TARGETS[3]).read_text()
    old = "'reference_addresses', 'standalone_sections')"
    assert profiles.count(old) == 1
    (PREP / 'candidate/conditional_profiles.py').write_text(profiles.replace(
        old, "'reference_addresses', 'standalone_sections', 'unquoted_definitions')"))
''' + text[end:]
# The remaining occurrences identify the new profile, not the service baseline.
replace("{'name': 'standalone_sections'", "{'name': 'unquoted_definitions'")
replace('standalone_section_review=', 'unquoted_definition_review=')
replace('Account for standalone section references and statutory chains while preserving original answers and legal uncertainty',
        'Discover explicit unquoted naming events from selected source text without supplied vocabulary; retain legal uncertainty')
replace('Verify50section signs and18standalone expressions; continue original definition and historical-law requirements',
        'Verify seven exact naming/scope/value readings without vocabulary; continue original scope,implicit-reference and historical-law requirements')
replace('87 admissions; 24000 accounted seconds and 3456 MiB including 4 MiB reserve; no unchanged retry',
        '88 admissions; 24000 accounted seconds and 3584 MiB including 4 MiB reserve; no unchanged retry')
replace('Resolve declared structural addresses without using reviewed semantic destinations',
        'Discover source naming events without supplied terms and preserve separate printed restrictions')
replace('Independent frozen source destinations, adverse controls, complete ordinary/installed answer equality',
        'Seven independent exact naming/scope/value intervals,unfamiliar-term controls,and complete ordinary/installed equality')
replace("'Wrong parent/range/source'", "'Wrong naming/value/restriction/source'")
replace('Paragraph addressing leaves19standalone section signs without dedicated source classification',
        'Quoted discovery and supplied-vocabulary forms do not discover explicit unquoted naming events')
replace('50sign partition,18standalone expressions and complete installed equality',
        'Seven source naming events,separate amount restrictions,unfamiliar terms and complete installed equality')
replace('24000 seconds / 3456 MiB cumulative with 4 MiB reserve; no unchanged retry',
        '24000 seconds / 3584 MiB cumulative with 4 MiB reserve; no unchanged retry')
replace("'limits_extended': False", "'limits_extended': True")
replace('Current cumulative allowance fits the bounded forecast; preserve all earlier costs',
        'Extend only storage3456to3584MiB for paired answers and package; retain24000seconds and all prior costs')
replace("'scripts/prospectus_reference_label_grammar.py',", "'scripts/prospectus_standalone_sections.py',")
replace("'scripts/prospectus_unquoted_definitions_draft.py')",
        "'scripts/prospectus_unquoted_definitions_draft.py', 'docs/implementation/prospectus-execution-authority/reviews/unquoted-definitions-349/METHOD-REVIEW.md')")
begin = text.index('def testfiles():')
end = text.index('\ndef prepare():', begin)
text = text[:begin] + '''def testfiles():
    return [TEST, 'tests/prospectus_successor/test_standalone_sections.py',
            'tests/prospectus_successor/test_reference_scope.py',
            'tests/prospectus_successor/test_reference_scope_headers.py',
            'tests/prospectus_successor/test_paragraph_references.py',
            'tests/prospectus_successor/test_conditional_profiles_cli.py']

''' + text[end:]
begin = text.index('def controls():')
end = text.index('\ndef installed():', begin)
text = text[:begin] + '''def controls():
    products, old = baseline()
    actual = read(HERE / 'ordinary-answer.json.gz')
    refused = {}
    for kind in ('delete-name', 'wrong-term', 'swap-scopes', 'drop-scope', 'drop-condition',
                 'wrong-value', 'source-map-delete', 'invent-missing', 'false-meaning',
                 'false-completion', 'source-identity', 'prior-answer'):
        bad = deepcopy(actual)
        report = bad[oracle.KEY]
        row = report['candidates'][0]
        amounts = [r for r in report['candidates'] if r['kind'] == 'PURPOSE_CONDITIONED_AMOUNT']
        if kind == 'delete-name': report['candidates'].pop()
        elif kind == 'wrong-term': row['term']['start'] += 1
        elif kind == 'swap-scopes': amounts[0]['scope'], amounts[1]['scope'] = amounts[1]['scope'], amounts[0]['scope']
        elif kind == 'drop-scope': amounts[0]['scope'] = None
        elif kind == 'drop-condition': next(r for r in report['candidates'] if r['condition'])['condition'] = None
        elif kind == 'wrong-value': amounts[1]['value'] = deepcopy(amounts[0]['value'])
        elif kind == 'source-map-delete': row['term']['source_projection'].pop()
        elif kind == 'invent-missing': row['label'] = 'Zinsperiode'
        elif kind == 'false-meaning': row['meaning'] = 'A legally admitted definition'
        elif kind == 'false-completion': report['whole_task_complete'] = True
        elif kind == 'source-identity': report['text_sha256'] = '0' * 64
        else: bad['questions']['Q1']['status'] = 'YES'
        bad['report_sha256'] = digest({k: v for k, v in bad.items() if k != 'report_sha256'})
        try: oracle.verify(bad, old, products, read(PREP / 'expected.json'))
        except AssertionError: refused[kind] = True
        else: raise AssertionError('Accepted ' + kind)
    save(HERE / 'controls.json', {'status': 'PASS', 'refused': refused})
    return {'status': 'PASS', 'refused': len(refused)}

''' + text[end:]
replace("'result_kind':'SOURCE_STANDALONE_SECTIONS'", "'result_kind':'SOURCE_UNQUOTED_DEFINITIONS'")
replace('Structural reference stage bound', 'Unquoted definition stage bound')
replace('Cumulative structural reference bound', 'Cumulative unquoted definition bound')
begin = text.index('RESULT_NOTE = ')
end = text.index("if __name__ == '__main__':", begin)
note = '''# Source naming events preserve printed restrictions

Seven explicit unquoted naming events are discovered from selected source text
without a supplied vocabulary or reviewed record IDs. Exact expression, term,
scope, value and applicability spans agree with the independent source freeze.
The two early-redemption amounts remain distinct despite identical names.
No definition for Zinsperiode is invented. All pre-existing answer fields remain
equal, and the fresh installed consumer matches the complete ordinary answer.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain finite unquoted syntax support|Exact independent spans,unfamiliar terms,complete installed equality|Naming,scope,value,condition,provenance and false-acceptance mutations refused|Unlisted grammar and governing use scope|Continue original reference/definition/statutory requirements|General recall,legal meaning,whole build|

The strongest alternative explanation is an unlisted naming convention or an
incorrect independently read span. A source mismatch would require reviewed
repair. Success on seven events does not establish exhaustive legal analysis;
the original task remains incomplete. No PDF/OCR package conclusion follows.
'''
text = text[:begin] + 'RESULT_NOTE = ' + repr(note) + '\n\n' + text[end:]
ast.parse(text)
target.write_text(text)
worker = ROOT / 'scripts/prospectus_unquoted_definitions_installed.py'
assert not worker.exists()
worker.write_text((ROOT / 'scripts/prospectus_standalone_sections_installed.py').read_text().replace(
    'successor.standalone_sections', 'successor.unquoted_definitions').replace(
    'structural-reference consumer', 'unquoted-definition consumer'))
print('Created unquoted-definition runner and isolated worker; candidate unevaluated')
