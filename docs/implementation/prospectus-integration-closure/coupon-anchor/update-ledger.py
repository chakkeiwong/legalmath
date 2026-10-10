"""Update attribution only from passing coupon consumer/installed/regression evidence."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'docs/implementation/prospectus-integration-closure'
PACKAGE=BASE/'coupon-anchor'
PREFIX=str(BASE.relative_to(ROOT))+'/'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,row):
    path.write_text(json.dumps(row,indent=2,ensure_ascii=False)+'\n')

def main():
    if sys.flags.optimize:
        raise RuntimeError('Attribution requires Python assertions enabled')
    consumer=read(PACKAGE/'attempt-001/result.json')
    installed=read(BASE/'installed/attempt-015/result.json')
    coverage=read(PACKAGE/'validation-001/coverage.json')
    for record in (consumer,installed,coverage):
        assert record['status']=='PASS'
        assert all(sha(ROOT/p)==h for p,h in record['method'].items())
    assert coverage['covered']==coverage['unique_tests'] and not coverage['missing'] and not coverage['unexpected']
    assert coverage['method_unchanged'] and consumer['method_unchanged']
    assert consumer['outcomes']['selected']['regular_due_dates']==['2024-08-30','2025-02-28','2025-08-30']
    assert [r['actual'] for r in consumer['exact_fractions']]==['1/2','1','1/6','137/183','91/366','137/182']
    stages=[read(BASE/'installed/attempt-015'/name) for name in ('installed-results.json','relocated-results.json','restored-results.json')]
    assert len(stages[0]['questions'])==11
    assert stages[0]['questions']==stages[1]['questions']==stages[2]['questions']
    assert stages[0]['anchor_controls']==stages[1]['anchor_controls']==stages[2]['anchor_controls']
    for folder in (PACKAGE/'attempt-001',BASE/'installed/attempt-015'):
        manifest=read(folder/'manifest.json')
        assert {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'}==set(manifest['files'])
        assert all(sha(folder/p)==h for p,h in manifest['files'].items())
    findings={
        'G14':'Selected-coupon-terms.v3 admits an exact operative English-date anchor, consumed by fixed-coupon.v2 through selected P5; the direct financial scenario route also recognizes v2. Source/evidence/version/override controls and installed source identities pass. Historical v1/v2 term paths remain preserved; Compass remains conditional.',
        'G15':'The reproduced 30-August/February mismatch is repaired in explicit anchored v2: original-day schedule and reference validation agree at exact fractions 1/2 and 1. Independent date/day enumeration and short/long first/final fractions pass. Both service routes and installed stages preserve the source-bound anchor and reject wrong dates/classifications. The old v1 rejection remains historical behavior; no third-party package was involved in this repair.',
        'G17':f'Installed attempt 015 passes eleven cases fresh, relocated and offline-restored, adding direct/selected synthetic original-anchor coupons to the nine prior cases. Full answer/source identities and anchor negative controls agree. Pledge meanings, six raw references, six scalar maps and Compass are preserved. Payload {installed["evidence_payload_bytes"]:,} bytes passes the 200-MB bound with metadata reserve.',
        'G20':f'Coupon validation uses actual serial R0–R7 receipts plus a frozen node inventory and exact uncovered-test run; {coverage["unique_tests"]} unique regression cases pass without missing or unexpected identities. Source methods are unchanged. R8 follows reviewed attribution update. Grouped coverage is reported explicitly rather than as a single-process aggregate; legal completion remains separate.'}
    remaining={
        'G14':'Independent real-instrument convention review, actual entitlement, clearing and settlement remain open. The new source-bound anchor examples are synthetic development inputs.',
        'G15':'Real-source irregular schedules, source-reviewed transfer/entitlement events, identical-input optional-package comparisons and broader settlement remain open. Full selected-contract calculations remain regular-only.',
        'G17':'Second-host portability and unlisted optional profiles remain untested. Conditional source preservation does not establish actual ownership, events, compliance, priority or payment.'}
    actions={
        'G14':'Independently review real-source coupon dates and conventions, then carry them through the same source/term bindings without replacing actual events with assumptions.',
        'G15':'Next freeze a real source-backed coupon convention case with independently listed schedule and exact reference periods; compare identical inputs with the retained QuantLib environment. Continue actual entitlement/event controls separately.',
        'G20':'Finalize actual phase evidence and the next substantive source/recovery plan. Continue passing tasks; do not rerun current checks merely because the broader program remains partial.'}
    additions={
        'G14':['coupon-anchor/attempt-001/result.json','coupon-anchor/attempt-001/selected/report.json','installed/attempt-015/result.json'],
        'G15':['coupon-anchor/attempt-001/exact-fractions.json','coupon-anchor/attempt-001/result.json','coupon-anchor/validation-001/focused.xml','coupon-anchor/validation-001/coverage.json'],
        'G17':['installed/attempt-015/result.json','installed/attempt-015/installed-results.json','installed/attempt-015/relocated-results.json','installed/attempt-015/restored-results.json'],
        'G20':['coupon-anchor/validation-001/coverage.json','coupon-anchor/validation-001/inventory.json']}
    ledger,review=read(BASE/'gap-status.json'),read(BASE/'attribution-review.json')
    for rows in (ledger['gaps'],review['gaps']):
        for row in rows:
            key=row['id']
            if key not in findings:
                continue
            row['finding']=findings[key]
            if key in remaining: row['remaining']=remaining[key]
            if key in actions: row['next_action']=actions[key]
            paths=[PREFIX+p for p in additions[key]]
            if rows is ledger['gaps']:
                row['evidence']=list(dict.fromkeys(row['evidence']+paths))
            else:
                existing={r['path'] for r in row['evidence']}
                row['evidence'].extend({'path':p,'sha256':sha(ROOT/p)} for p in paths if p not in existing)
    for row in review['gaps']+review['packages']:
        for item in row['evidence']:
            if sha(ROOT/item['path'])!=item['sha256']:
                assert item['path']=='src/legalmath/prospectus/successor/closure_program.py',item['path']
                item['sha256']=sha(ROOT/item['path'])
    ledger['last_review']='Explicit original-anchor integration passes local/source/service/installed controls; exact partitioned regression coverage retained. Historical profile behavior and hypothetical entitlement remain explicit.'
    ledger['regression']={'path':PREFIX+'coupon-anchor/validation-001/coverage.json','passed':coverage['unique_tests'],
        'execution':'PARTITIONED_NODE_UNION','method_unchanged':True,'single_process_aggregate':False}
    ledger['installed_application'].update(path=PREFIX+'installed/attempt-015/result.json',retained_bytes=installed['evidence_payload_bytes'])
    ledger['coupon_anchor_checks']={'consumer':PREFIX+'coupon-anchor/attempt-001/result.json',
        'exact_fractions':PREFIX+'coupon-anchor/attempt-001/exact-fractions.json','installed':PREFIX+'installed/attempt-015/result.json',
        'actual_entitlement':'NOT_ESTABLISHED','real_instrument_anchor':'NOT_ESTABLISHED'}
    save(BASE/'gap-status.json',ledger)
    save(BASE/'attribution-review.json',review)
    sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
    from scripts.prospectus_closure_attribution import report
    save(BASE/'final-attribution.json',report(ROOT))
    print(json.dumps({'status':'UPDATED_VERIFIED_ATTRIBUTION','gaps':list(findings),'unique_tests':coverage['unique_tests']}))

if __name__=='__main__':
    main()
