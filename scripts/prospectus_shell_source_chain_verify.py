"""Inspect complete source-chain evidence without calling its production reader."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/shell-source-chain-380'
BASE = AUTH / 'attempts/finance-conventions/attempt-013'
CASES = ('global-plain', 'definitive-plain', 'global-principal-only')
ADVERSE = ('false-succession', 'false-publication', 'missing-agreement', 'universal-precedence',
           'boolean-as-zero', 'missing-qualifier', 'omitted-review',
           'null-review', 'empty-review', 'generic-profile')


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()


def hashed(value):
    return hashlib.sha256(value if isinstance(value, bytes) else encoded(value)).hexdigest()


def same(left, right):
    assert encoded(left) == encoded(right), 'Complete typed values differ'


def report_check(report, graph):
    spec = read(PREP / 'source-spec.json')
    units = {u['id']: u for u in graph['units']}
    sources = {}
    for name, anchors in spec['groups'].items():
        sources[name] = []
        for source in anchors:
            unit = units[source['unit']]
            assert unit['visible'] is True and source['source_sha256'] == unit['source_sha256']
            assert unit['raw'][source['start']:source['end']] == source['quote']
            sources[name].append({**source, 'page': unit['page'], 'bbox': unit.get('bbox')})
    same(report['sources'], sources)
    assert report['source_graph_sha256'] == hashed(graph)
    assert report['version'] == 'shell-contract-source-chain.v1'
    assert report['scope'] == 'NAMED_SUPPLIED_SHELL_2030_SOURCE_PAIR'
    assert report['reading_kind'] == 'EXPOSED_SOURCE_INTERPRETATION'
    expected_docs = [{'document': d['id'], 'sha256': d['sha256'],
                      'printed_document_date': d['document_date'][:10],
                      'date_basis': 'PRINTED_DOCUMENT_DATE', 'authenticity': 'NOT_ESTABLISHED',
                      'first_publication': 'NOT_ESTABLISHED'} for d in spec['documents']]
    same(report['documents'], expected_docs)
    same(report['instrument'], {'issuer': 'Shell International Finance B.V.', 'guarantor': 'Royal Dutch Shell plc',
         'currency': 'GBP', 'nominal': '500000000', 'annual_rate': '1.000 per cent.', 'maturity': '2030-12-10'})
    link = report['edition_link']
    assert (link['status'], link['from_document'], link['to_document'], link['referenced_date']) == (
        'PRINTED_REFERENCE_MATCH', 'shell-2030-final', 'shell-2020-base', '2020-08-13')
    assert link['historical_publication'] == 'NOT_ESTABLISHED'
    assert 'document statement' in link['publication_statement']
    construction = report['construction']
    assert construction['part_a_relation'] == 'SUPPLEMENTS_CONDITIONS'
    assert construction['all_source_roles_established'] is False
    assert 'permission' in construction['definitive_note'] and 'otherwise' in construction['definitive_note']
    assert 'Exempt Notes' in construction['exempt_note_branch'] and 'not selected' in construction['exempt_note_branch']
    precedence = report['precedence']
    assert precedence['condition'] == 'ONLY_IN_THE_EVENT_OF_INCONSISTENCY'
    same(precedence['rules'], [{'prevails': 'TRUST_DEED', 'over': 'AGENCY_AGREEMENT'},
                              {'prevails': 'APPLICABLE_FINAL_TERMS', 'over': 'AGENCY_AGREEMENT'},
                              {'prevails': 'APPLICABLE_FINAL_TERMS', 'over': 'TRUST_DEED'}])
    assert precedence['mandatory_law_overridden'] is False and precedence['actual_inconsistency_decided'] is False
    history = report['trustee_history']
    assert history['original_deed_date'] == '2005-07-22'
    assert history['original_deed_named_trustee'] == 'Citicorp Trustee Company Limited'
    assert history['programme_named_trustee'] == 'Deutsche Trustee Company Limited'
    assert history['office_statement_date'] == '2020-08-13'
    assert history['successors_included_in_definition'] is True
    assert history['relationship'] == 'DIFFERENT_DATED_CONTEXTS_WITH_SUCCESSOR_DEFINITION'
    assert history['actual_succession_established'] is False and history['contradiction_established'] is False
    onward = report['onward_documents']
    assert [(r['document'], r['described_date']) for r in onward] == [
        ('TRUST_DEED', '2005-07-22'), ('AGENCY_AGREEMENT', '2020-08-13'), ('GLOBAL_NOTE', None)]
    assert all(r['status'] == 'EXECUTED_CONTENT_NOT_SUPPLIED_IN_REVIEWED_PAIR' for r in onward)
    assert onward[1]['named_agent'] == 'Deutsche Bank AG, London Branch'
    assert report['note_form']['definitive_exchange'] == 'AT_ISSUER_REQUEST_AND_IN_LIMITED_CIRCUMSTANCES_SET_OUT_IN_NOTE'
    assert report['note_form']['actual_exchange_established'] is False
    f = report['financial_selections']
    assert f['final_redemption_amount_per_calculation_amount'] == f['early_redemption_amount_per_calculation_amount'] == 'GBP 1000'
    assert f['equal_amounts_make_triggers_equivalent'] is False
    assert f['alternative_payment_day_definition'] == 'NOT_APPLICABLE'
    assert f['issuer_call_option'] == f['noteholder_put_option'] == 'NOT_APPLICABLE'
    assert f['interest_payment_basis'] == 'FIXED_RATE'
    assert report['payment_recipient']['printed_rule'] == 'GLOBAL_NOTE_HOLDER_OR_TRUSTEE_AS_PROVIDED_IN_TRUST_DEED'
    assert report['payment_recipient']['actual_recipient_established'] is False
    assert len(report['unresolved']) == 4
    assert report['legal_applicability_established'] is False
    assert report['assembly_roles_changed'] is False and report['independent_legal_acceptance'] is False


def verify(attempt):
    freeze = read(PREP / 'freeze.json')
    for name, checksum in freeze['bindings'].items():
        assert hashed((ROOT / name).read_bytes()) == checksum, name
    for name, checksum in read(BASE / 'outputs.json').items():
        assert hashed((BASE / name).read_bytes()) == checksum, name
    for stage in ('tests', 'ordinary', 'package', 'installed'):
        assert not (attempt / 'stages' / stage / 'failure.json').exists()
        assert read(attempt / 'stages' / stage / 'result.json')['status'] == 'PASS'
    cases = ET.parse(attempt / 'tests.xml').getroot().findall('.//testcase')
    assert cases and all(not list(c) for c in cases)
    assert any(c.attrib['name'].startswith('test_rehashed_review_corruption') for c in cases)
    package = read(attempt / 'package.json')
    same(package['files'], freeze['production'])
    wheel = list((attempt / 'wheel').glob('*.whl'))
    assert len(wheel) == 1 and hashed(wheel[0].read_bytes()) == package['wheel_sha256']
    with zipfile.ZipFile(wheel[0]) as archive:
        same({n.removeprefix('legalmath/'): hashed(archive.read(n)) for n in archive.namelist()
              if n.startswith('legalmath/') and not n.endswith('/')}, package['files'])
    installed = attempt / 'installed/legalmath'
    same({str(p.relative_to(installed)): hashed(p.read_bytes()) for p in installed.rglob('*') if p.is_file()}, package['files'])
    stable = lambda a: {k: v for k, v in a.items() if k not in
                       ('contract_source_chain', 'report_sha256', 'consumed_products', 'request_sha256')}
    for mode in ('ordinary', 'installed'):
        summary = read(attempt / (mode + '-summary.json'))
        assert summary['status'] == 'PASS' and summary['whole_task_complete'] is False
        assert [r['id'] for r in summary['cases']] == list(CASES)
        origins = read(attempt / (mode + '-imports.json'))
        basepath = ROOT / 'src' if mode == 'ordinary' else attempt / 'installed'
        assert origins and 'legalmath.prospectus.successor.shell_source_chain' in origins
        assert all(Path(p).resolve().is_relative_to(basepath.resolve()) for p in origins.values())
        for name in CASES:
            folder = attempt / mode
            ps = read(folder / (name + '-products.json.gz'))
            legacy = read(folder / (name + '-legacy-products.json.gz'))
            a = read(folder / (name + '-answer.json.gz'))
            old = read(folder / (name + '-legacy-answer.json.gz'))
            same(old, read(BASE / 'ordinary' / (name + '-answer.json.gz')))
            same(legacy['P5'], read(BASE / 'ordinary' / (name + '-P5.json.gz')))
            same(a['questions'], old['questions'])
            same(stable(a), stable(old))
            same(ps['P5']['payload'], legacy['P5']['payload'])
            same(ps['P2']['payload']['assembly'], legacy['P2']['payload']['assembly'])
            same(ps['P1']['payload']['graph'], legacy['P1']['payload']['graph'])
            r = a['contract_source_chain']
            same(r, ps['P2']['payload']['contract_source_chain'])
            report_check(r, ps['P1']['payload']['graph'])
            assert a['report_sha256'] == hashed({k: v for k, v in a.items() if k != 'report_sha256'})
            assert a['may_execute_transaction'] is False
            for key, product in ps.items():
                assert product['sha256'] == hashed({k: v for k, v in product.items() if k != 'sha256'})
                assert a['consumed_products'][key] == product['sha256']
            if mode == 'installed':
                same(a, read(attempt / 'ordinary' / (name + '-answer.json.gz')))
                same(ps, read(attempt / 'ordinary' / (name + '-products.json.gz')))
        refusals = summary['cases'][0]['refusals']
        assert [r['id'] for r in refusals] == list(ADVERSE)
        assert not any(r['refusals'] for r in summary['cases'][1:])
        for row in refusals:
            bad = read(attempt / mode / 'adverse' / (row['id'] + '.json.gz'))
            assert row['input_sha256'] == hashed(bad) and row['reason']
            if 'P2' in bad:
                assert bad['P2']['sha256'] == hashed({k: v for k, v in bad['P2'].items() if k != 'sha256'})
                assert bad['P3']['inputs']['P2'] == bad['P2']['sha256']
    return {'status': 'PASS', 'cases_per_runtime': len(CASES), 'refusals_per_runtime': len(ADVERSE),
            'source_groups': len(read(PREP / 'source-spec.json')['groups']),
            'financial_and_assembly_preservation': True, 'whole_task_complete': False}


if __name__ == '__main__':
    attempt = Path(sys.argv[1])
    result = verify(attempt)
    with (attempt / 'verification.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
