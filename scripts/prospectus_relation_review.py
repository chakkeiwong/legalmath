"""Bounded, retained execution for admitted relation review003."""
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import file_hash, read, write
from legalmath.prospectus.relation_review import VERSION, validate_review_packet
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/relation-discovery'
HERE = BASE / 'attempt-003'
PLAN = 'docs/plans/prospectus-relation-candidate-review-2026-10-15.md'
METHODS = ['src/legalmath/prospectus/relation_review.py',
           'tests/prospectus/test_relation_review.py', 'scripts/prospectus_relation_review.py']


def inputs():
    products = json.load(gzip.open(BASE / 'attempt-002/v2-products.json.gz'))
    answer = json.load(gzip.open(BASE / 'attempt-002/v2-answer.json.gz'))
    targets = read(BASE / 'attempt-001/protected-targets.json')['bes']
    return products, answer, targets


def save(name, value):
    write(HERE / name, value, exclusive=True)


def bindings():
    bound = read(HERE / 'admission.json')['binding']
    changed = [p for p, h in bound.items() if file_hash(ROOT / p) != h]
    if changed:
        raise ValueError('Admission input changed: ' + repr(changed))


def prepare():
    products, answer, targets = inputs()
    graph = products['P1']['payload']['graph']
    discovery = answer['relation_candidates']
    units = {u['id']: u for u in graph['units']}
    descriptions = {
        '063a67754c91': ('Page1 item7(i) gives issue/interest commencement on15 July2011. The candidate also includes item8 maturity on15 July2016.', 'Stop the row at the next Arabic item and retain maturity separately.'),
        '33dcd447e044': ('Page6 item5(ii) pairs Common Code with064529170.', 'Keep the printed row as an unaccepted suggestion.'),
        '3819af8fbb30': ('Page3 item33(i) gives Not Applicable for syndicated managers; its wrapped label belongs to one row.', 'Retain the complete wrapped label and value for review.'),
        '417f2beda397': ('Page6 item5(vi) gives Yes for intended Eurosystem-eligible holding. The following qualification is separately suggested.', 'Retain alongside the complete qualification; do not infer actual eligibility.'),
        '55f1066b6a2c': ('Page6 item5(iv) pairs Delivery with Delivery against payment.', 'Retain as a printed delivery statement without transaction authorization.'),
        '5df4f1d47579': ('Page3 item25(i) pairs Form of Notes with Book-entry form registered Notes (Interbolsa Notes).', 'Retain the row; preserve the raw merged label ofNotes.'),
        '64ce20228cd4': ('Page3 item25(ii) answers New Global Note with No. Not Applicable belongs to item26 payment-day provisions.', 'Stop the row at Arabic item26; do not attach its value to item25(ii).'),
        '697cf23eefdb': ('Page6 item5(iii) associates the clearing-system label with Interbolsa, but raw Liquidacdoe and Mobilidrios differ from the visible Portuguese spelling.', 'Retain row association and raw OCR; obtain an explicit source-linked transcription before exact name use.'),
        '74ec03dc251d': ('Page6 item5(i) is the ISIN row. Raw PTBEQBOMO0010 has an unresolved extra/O-zero sequence relative to the printed identifier.', 'Do not certify the identifier from endpoint matching; require source-linked transcription review.'),
        '774a457810e2': ('Page2 item15(iv) gives Not Applicable for Broken Amount(s).', 'Retain as a printed row suggestion.'),
        '83fff16320c0': ('Page6 item5(vi) qualifies Yes with the entire Note that paragraph through satisfaction of Eurosystem eligibility criteria.', 'Keep the full negative qualification; do not equate intended holding with recognized collateral.'),
        '8c8076181790': ('Page2 item15(v) gives Actual/Actual (ICMA) for Day Count Fraction.', 'Retain the row; calculation and governing scope need their separate evidence.'),
        '98ec9968e07b': ('Page2 item15(i) gives6.875 per cent per annum payable annually in arrear.', 'Retain the complete rate/payment-convention text.'),
        '9b29e9834246': ('Page2 item13(ii) Status of the Notes is Senior. The candidate merges item13(iii) board-approval label and27 June2011.', 'Treat a malformed marker-column token as a boundary/ambiguity rather than merging through it.'),
        'ab4b6559fd4b': ('Page5 item1(i) records an application for listing/trading with effect from15 July2011; the five value lines stay within that row.', 'Retain the application wording; do not turn it into proof that listing occurred.'),
        'b2c23f6badd4': ('Page5 Ratings contains a regulatory-use restriction and the full unless exception ending registration is not refused; the candidates target both printed grades.', 'Retain the full qualification as a suggestion; legal applicability and current law require separate analysis.'),
        'c74a8b85c019': ('Page1 item6(ii) pairs Calculation Amount with EUR100,000.', 'Retain the row and currency symbol without deriving an amount schedule.'),
        'c83aaf19b8fd': ('Page6 item5(v) gives Not Applicable for additional paying-agent names and addresses.', 'Retain the wrapped label and value; do not infer absence of all agents.'),
        'd2066dbdd998': ('Page2 item15(vii) gives None for other terms relating to fixed-rate interest calculation.', 'Retain the complete wrapped label and None; it does not negate terms elsewhere.'),
        'daeaa57f1599': ('Page2 item15(ii) gives15 July in each year up to and including the Maturity Date.', 'Retain the full maturity qualification; do not truncate the payment-date rule.'),
        'eef3092272a8': ('Page2 item15(iii) gives EUR6,875 per Calculation Amount for Fixed Coupon Amount(s).', 'Retain the amount and denominator together.'),
        'f1e70aafe475': ('Page3 item33(ii) gives Not Applicable for Stabilising Manager(s), including the wrapped if-any qualifier.', 'Retain the complete printed label/value pair.'),
        'f644de241141': ('Page1 item6(i) gives EUR100,000 for Specified Denominations.', 'Retain the denomination row separately from Calculation Amount.'),
        'f81c9c687311': ('Page2 item15(vi) visibly gives15 July in each year. The proposed value also contains raw p2:ocr55 t from the far-right scan edge.', 'Preserve raw OCR, flag the extraneous endpoint and test finite horizontal row boundaries before reuse.'),
    }
    extras = {
        '063a67754c91': ['p1:ocr68'],
        '64ce20228cd4': ['p3:ocr24'],
        '9b29e9834246': ['p2:ocr25', 'p2:ocr26', 'p2:ocr27', 'p2:ocr28', 'p2:ocr30', 'p2:ocr29'],
    }
    disputed = {'697cf23eefdb': ['p6:ocr15', 'p6:ocr21'],
                '74ec03dc251d': ['p6:ocr5'], 'f81c9c687311': ['p2:ocr55']}
    context = {'063a67754c91': ['p1:ocr66', 'p1:ocr67'],
               '64ce20228cd4': ['p3:ocr22', 'p3:ocr23', 'p3:ocr25', 'p3:ocr27'],
               '9b29e9834246': ['p2:ocr24']}
    resolve = lambda ids: [anchor(units['bes-final-terms-2011:' + i]) for i in ids]
    rows = []
    for c in discovery['candidates']:
        prefix = c['id'].split(':')[1][:12]
        reason, repair = descriptions.pop(prefix)
        evidence = c['from'] + c['to'] + [c[k] for k in ('row_marker', 'scope_marker') if k in c] + resolve(context.get(prefix, []))
        rows.append({'candidate_id': c['id'], 'candidate_sha256': digest(c),
            'protected_target_ids': sorted(t['id'] for t in targets if all(t[k] == c[k] for k in ('kind','from','to'))),
            'disposition': 'WRONG_PRINTED_SCOPE' if prefix in extras else 'UNRESOLVED_TRANSCRIPTION' if prefix in disputed else 'REVIEWABLE_PRINTED_RELATION',
            'reason': reason, 'repair': repair, 'excess': resolve(extras.get(prefix, [])),
            'omitted': [], 'transcription_anchors': resolve(disputed.get(prefix, [])),
            'evidence_anchors': evidence,
            'transcription_note': 'Raw OCR retained character-for-character. Disposition concerns printed relation scope; it does not certify every glyph. Explicit uncertain endpoints are separately listed.'})
    assert not descriptions and len(rows) == 24
    render = read(HERE / 'pages/render.json')
    source = {'document': 'bes-final-terms-2011', 'source_path': render['source'],
              'source_sha256': render['sha256'], 'pages': [
                  {'page': p['page'], 'path': str((HERE/'pages'/p['file']).relative_to(ROOT)),
                   'sha256': file_hash(HERE/'pages'/p['file'])} for p in render['pages']]}
    packet = {'version': VERSION, 'source_graph_sha256': digest(graph),
              'discovery_sha256': digest(discovery), 'protected_targets_sha256': digest(targets),
              'reviewer': {'identity': 'Codex agent source review2026-10-15',
                          'basis': 'AGENT_EXPOSED_DEVELOPMENT_REVIEW', 'independent': False},
              'sources': [source], 'reviews': rows, 'accepted_relations': [], 'legal_scope_inferred': False}
    result = validate_review_packet(graph, discovery, targets, packet, ROOT)
    save('review-ledger.json', packet)
    save('validated-packet.json', result)
    save('candidate-snapshot.json', discovery)
    save('protected-targets.json', targets)
    save('source-neighborhoods.json', [u for u in graph['units'] if
         (u['page']==1 and 58<=u['order']<=68) or
         (u['page']==2 and (20<=u['order']<=31 or 52<=u['order']<=59)) or
         (u['page']==3 and 19<=u['order']<=27)])
    save('method-identities.json', {p: file_hash(ROOT/p) for p in METHODS})
    for path in METHODS:
        target = HERE/'method'/path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream: stream.write((ROOT/path).read_bytes())
    return {k:v for k,v in result.items() if k != 'packet'}


def tests():
    import pytest
    xml = 'tests-complete.xml' if (HERE/'tests.xml').exists() else 'tests.xml'
    code = pytest.main(['-q', 'tests/prospectus/test_relation_review.py',
                        '--junitxml=' + str(HERE/xml)])
    if code:
        raise ValueError('Focused review tests failed: ' + str(code))
    return {'pytest_exit': int(code)}


def controls():
    products, original, targets = inputs()
    graph = products['P1']['payload']['graph']
    discovery = original['relation_candidates']
    packet = read(HERE/'review-ledger.json')
    results = []
    for case in ('missing', 'duplicate', 'foreign', 'changed_graph', 'changed_candidate',
                 'forged_anchor', 'independent', 'governing', 'empty_reason', 'changed_render'):
        g, d, t, p = deepcopy((graph, discovery, targets, packet))
        if case == 'missing': p['reviews'].pop()
        elif case == 'duplicate': p['reviews'].append(deepcopy(p['reviews'][0]))
        elif case == 'foreign': p['reviews'][0]['candidate_id'] = 'foreign'
        elif case == 'changed_graph': g['units'][0]['raw'] += 'changed'
        elif case == 'changed_candidate': d['candidates'][0]['scope'] = 'changed'
        elif case == 'forged_anchor': p['reviews'][0]['evidence_anchors'][0]['quote'] = 'forged'
        elif case == 'independent': p['reviewer']['independent'] = True
        elif case == 'governing': p['legal_scope_inferred'] = True
        elif case == 'empty_reason': p['reviews'][0]['reason'] = ' '
        elif case == 'changed_render': p['sources'][0]['pages'][0]['sha256'] = '0'*64
        try: validate_review_packet(g,d,t,p,ROOT)
        except ValueError as error: results.append({'case':case,'refused':True,'reason':str(error)})
        else: results.append({'case':case,'refused':False})
    save('actual-controls.json', results)
    assert all(r['refused'] for r in results)
    return {'refused':len(results),'native_starts':0}


def consume():
    from legalmath.prospectus.successor import service
    products, original, targets = inputs()
    before = digest(products)
    packet = read(HERE/'review-ledger.json')
    checked = validate_review_packet(products['P1']['payload']['graph'], original['relation_candidates'], targets, packet, ROOT)
    result = service.consume(products, ROOT, include_artifacts=True)
    with gzip.open(HERE/'reconsumed-answer.json.gz', 'wt') as stream: json.dump(result, stream)
    # Historical assess labels itself fresh after consuming the same products.
    # Retain actual frozen replay separately; compare only this declared metadata
    # normalization and its derived checksum. This stage does not claim fresh OCR.
    normalized = deepcopy(result)
    normalized['assessment_mode'] = original['assessment_mode']
    normalized['report_sha256'] = digest({k:v for k,v in normalized.items() if k != 'report_sha256'})
    checks = {'full_answer_identical_after_declared_mode_normalization': normalized == original,
              'products_unchanged': before == digest(products),
              'relations_still_unaccepted': result['relation_candidates']['accepted_relations'] == [],
              'no_legal_scope_inferred': result['relation_candidates']['legal_scope_inferred'] is False,
              'packet_isolated': checked['may_change_answer'] is False,
              'all_candidates_reviewed': checked['candidate_count'] == 24,
              'all_targets_accounted': checked['protected_target_count'] == 8 and checked['additional_candidate_count'] == 16}
    report = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
              'actual_mode': result['assessment_mode'], 'historical_mode': original['assessment_mode'],
              'actual_report_sha256': result['report_sha256'], 'historical_report_sha256': original['report_sha256'],
              'normalized_report_sha256': normalized['report_sha256'],
              'changed_top_level_fields': [k for k in set(normalized)|set(original) if normalized.get(k)!=original.get(k)],
              'native_starts': 0, 'fresh_assessment': False}
    save('comparison.json', report)
    if not all(checks.values()): raise ValueError('Actual downstream comparison failed')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare','tests','tests-complete','controls','consume'])
    args = parser.parse_args()
    def expired(signum, frame): raise TimeoutError('120-second stage bound; no automatic restart')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(120)
    if (HERE/'outputs.json').exists(): raise ValueError('Attempt already sealed')
    bindings()
    invocation = HERE/'invocations'/args.stage
    invocation.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    write(invocation/'started.json', {'command': ['.venv/bin/python','-m','scripts.prospectus_relation_review',args.stage],
         'environment': sys.executable, 'cpu_gpu': 'CPU-only pure Python; no GPU framework imported',
         'plan': PLAN, 'git_commit': read(HERE/'admission.json')['git_commit']}, exclusive=True)
    try:
        result = (tests if args.stage == 'tests-complete' else globals()[args.stage])()
        result = {'status':'PASS', 'stage':args.stage, 'result':result}
    except BaseException as error:
        result = {'status':'FAIL','stage':args.stage,'error':repr(error)}
        raise
    finally:
        result['wall_seconds'] = time.monotonic()-start
        write(invocation/'result.json',result,exclusive=True)
        signal.alarm(0)
    print(json.dumps(result))


if __name__ == '__main__': main()
