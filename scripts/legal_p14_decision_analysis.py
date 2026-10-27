"""Preserve and classify every non-ACCEPT decision without changing its verdict."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ARM = Path('artifacts/legal-mission-control/2026-10-21/review-repair/recovered-live/arms/p14/baseline')
OUT = Path('artifacts/legal-mission-control/2026-10-23/p14-decisions')

# Individually inspected correspondence-only requests. This is a reviewed exact
# set, not a keyword classifier; mixed and substantive needs retain source routing.
MAPPING_QUERIES = {
    'Supply the dependency text and origin-reading reference corresponding to the assignment identifier permitted by the response schema, or correct the schema to identify the intended supplied assignment.',
    'Supply the dependency text and origin-reading reference associated with assignment dependency-40689d9b8e04128b97504d0a, or its explicit mapping to an item in the delivered assignment list.',
    'Supply the dependency statement and review scope corresponding to the assignment identifier required by the response schema, or provide a response schema mapping the delivered assignment identifiers.',
    'Supply the dependency statement and origin-reading reference for the assignment identified by the required output mapping.',
    'Supply the dependency statement, origin passage and review scope corresponding to the assignment identifier required by the response schema.',
    'Supply the dependency assignment corresponding to the assignment identifier required by the response schema, or identify its exact counterpart in the delivered assignment list.',
    'Supply the correspondence between the opaque dependency assignment keys in the required response schema and the individually identified dependency assignments in the request.',
    'Supply the association between each dependency assignment selector in the required output schema and the individually identified dependency assignments in the request.',
    'Supply the dependency text, origin and assigned scope associated with the required response assignment identifier, or an explicit mapping to an assignment delivered in this request.',
    'Supply the correspondence between each opaque dependency assignment key in the required response schema and each dependency item identifier in the request.',
    'Supply the exact association between each opaque dependency assignment key required by the response schema and each dependency item identified in the request payload.',
}


def read(path):
    return json.loads((ROOT/path).read_text())


def reference(path):
    return dict(path=str(path), sha256=sha256((ROOT/path).read_bytes()).hexdigest())


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def run():
    saved = read(ARM/'contextual-group-review-p14.json')
    old = read(Path('artifacts/legal-mission-control/2026-10-21/review-repair/checkpoints/arms/p14/baseline.json'))
    cached = {}
    rows, rationales = [], {}
    for index, review in enumerate(saved['reviews']):
        value = review.get('value', {})
        if review['status'] != 'VALIDATED' or value['verdict'] == 'ACCEPT':
            continue
        identity, = value['considered']
        evidence = review.get('group_evidence') or review['repair_evidence']
        key = evidence['key']
        if key not in cached:
            folder = ARM/'calls'/key
            if (ROOT/folder/'request.json').exists():
                pointers = {n:reference(folder/(n+'.json')) for n in ('request', 'schema', 'result')}
            else:
                pointers = old['review_groups'][key]
            request = read(Path(pointers['request']['path']))
            result = read(Path(pointers['result']['path']))
            assert result and evidence['result_hash'] == fingerprint(result)
            cached[key] = request, pointers
        request, pointers = cached[key]
        assignments = {r['id']:r for r in request['payload']['assignments']}
        assert identity in assignments and identity in request['required_considered']
        decision = {k:v for k,v in value.items() if k != 'considered'}
        rationale = fingerprint(decision)
        kinds = sorted({n['kind'] for n in value.get('context_needs', [])})
        text = json.dumps(decision, ensure_ascii=False).lower()
        flags = []
        for name, terms in {
            'conditional_scope': ('as written','conditional','question actually asked','outside the question'),
            'client_application': ('client','correspondence','particular provider','actual arrangement'),
            'judicial_transfer': ('gatecoin','judgment','judicial','holding'),
            'extraction_fidelity': ('extract','ocr','truncat','fragment','page break'),
            'stale_absence_claim': ('incorrectly','inaccurate','blanket absence','absence claim','missing-source statement'),
            'p14_attachment': ('request trigger','request condition','footnote','confirmation','demonstration'),
            'standards_and_fulfilment': ('sufficien','fulfil','fulfill','standard','compliance'),
        }.items():
            if any(t in text for t in terms):
                flags.append(name)
        action = ('ASSESS_EACH_ADVERSE_ISSUE_WARRANT' if value['verdict']=='REJECT' else
            'JOINT_SOURCE_CONTEXT_REVIEW' if 'SOURCE_TEXT' in kinds else
            'ASSESS_NECESSITY_AND_PRESERVE_CONDITIONS' if kinds else
            'CLARIFY_UNTYPED_NEED_AGAINST_ORIGINAL_ANSWER')
        row = dict(index=index, id=identity, verdict=value['verdict'], rationale=rationale,
            need_kinds=kinds, needs_class='+'.join(kinds) or 'NO_TYPED_NEED',
            full_decision=decision, assignment=assignments[identity],
            answer_hash=fingerprint(request['payload']['answer']),
            delivered_record_ids=[r['id'] for r in request['records']],
            delivered_records_hash=fingerprint(request['records']),
            original_request=pointers['request'], original_result=pointers['result'],
            original_schema=pointers['schema'], result_hash=evidence['result_hash'],
            review_key=key, analysis_id=evidence.get('analysis_id'), flags=flags,
            proposed_action=action, legal_disposition_changed=False)
        rows.append(row)
        rationales.setdefault(rationale, dict(decision=decision, ids=[], keys=[], flags=flags))['ids'].append(identity)
        if key not in rationales[rationale]['keys']:
            rationales[rationale]['keys'].append(key)
    assert len(rows)==697 and len({r['id'] for r in rows})==697
    counts=Counter(r['verdict'] for r in rows)
    assert counts==dict(UNRESOLVED=672,REJECT=25)
    summary=dict(profile='exhaustive-p14-decision-analysis.v1', original=reference(ARM/'contextual-group-review-p14.json'),
        decisions=len(rows), verdicts=dict(counts), distinct_full_rationales=len(rationales),
        unresolved_needs=dict(Counter(r['needs_class'] for r in rows if r['verdict']=='UNRESOLVED')),
        rejected_issue_occurrences=sum(len(r['full_decision']['issues']) for r in rows if r['verdict']=='REJECT'),
        actions=dict(Counter(r['proposed_action'] for r in rows)),
        provider_calls=0, original_verdicts_unchanged=True, legal_acceptance=False,
        classifier_scope='Deterministic routing and text flags only; no semantic verdict is inferred from keywords.')
    folder=ROOT/OUT
    folder.mkdir(parents=True,exist_ok=True)
    for name,value in [('summary',summary),('decisions',rows),('rationales',rationales)]:
        (folder/(name+'.json')).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    mapped = []
    for row in rows:
        for need in row['full_decision'].get('context_needs', []):
            if need['query'] in MAPPING_QUERIES:
                assert need['kind']=='SOURCE_TEXT' and not need['record_ids'] and not need['locators']
                mapped.append(dict(assignment_id=row['id'], need_hash=fingerprint(need),
                    decision_hash=fingerprint({**row['full_decision'], 'considered':[row['id']]}),
                    original_need=need, reason='Inspected request solely asks for implementation correspondence.'))
    assert len(mapped)==95 and {r['original_need']['query'] for r in mapped}==MAPPING_QUERIES
    (folder/'mapping-only-needs.json').write_text(json.dumps(dict(profile='reviewed-p14-mapping-needs.v1',
        original=reference(ARM/'contextual-group-review-p14.json'), exact_queries=sorted(MAPPING_QUERIES),
        needs=mapped, substantive_requests_not_reclassified=True),indent=2,ensure_ascii=False)+'\n')
    row = next(r for r in rows if r['id']=='dependency-eb360cda6c4325f36b4a1cfd')
    need, = row['full_decision']['context_needs']
    assert need['kind']=='EXTERNAL_AUTHORITY' and need['query']==(
        'Verify the cited Handbook provisions on its legal effect and consequences of non-compliance, '
        'including the stated distinction between evidential or regulatory consequences and automatic liability.')
    (folder/'retained-source-needs.json').write_text(json.dumps(dict(profile='reviewed-p14-retained-source-needs.v1',
        needs=[dict(assignment_id=row['id'], need_hash=fingerprint(need),
            decision_hash=fingerprint({**row['full_decision'], 'considered':[row['id']]}), original_need=need,
            record_ids=['source:handbook.oct2024.page7:0','source:handbook.oct2024.page8:0',
                'source:handbook.oct2024.page9:0'],
            reason='Inspected request asks to verify the already-retained October 2024 Handbook legal-status '
                'provisions on pages 7–9, including the page-8 continuation of paragraph 1.6. This delivers '
                'those passages; it does not establish extraction fidelity, current applicability or client facts.')],
        review=reference(Path('docs/plans/p14-decision-followup-2026-10-23.md')),
        original_verdicts_unchanged=True),indent=2,ensure_ascii=False)+'\n')
    lines=[]
    for i, (key, row) in enumerate(rationales.items()):
        v=row['decision']
        lines.append(dict(n=i, hash=key, members=len(row['ids']), verdict=v['verdict'],
            reason=v['reason'], issues=v['issues'], needs=v.get('context_needs',[]), source_gaps=v['source_gaps']))
    (folder/'reading.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in lines))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    run()
