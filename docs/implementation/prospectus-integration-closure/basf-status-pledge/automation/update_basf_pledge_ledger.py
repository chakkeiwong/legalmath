"""Record the inspected pledge evidence only after its actual checks pass."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/home/chakwong/python/legalmath/.worktrees/bond-gap-closure')
BASE = ROOT/'docs/implementation/prospectus-integration-closure'
PREFIX = str(BASE.relative_to(ROOT))+'/'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def main():
    consumer = read(BASE/'basf-status-pledge/attempt-001/result.json')
    installed = read(BASE/'installed/attempt-014/result.json')
    focused = read(BASE/'checks/basf-pledge-001-manifest.json')
    aggregate = read(BASE/'checks/successor-013-manifest.json')
    for record in (consumer, installed, focused, aggregate):
        assert record['status']=='PASS'
        assert all(sha(ROOT/p)==h for p,h in record['method'].items())
    for record, count in ((focused,23),(aggregate,599)):
        assert record['counts']==dict(tests=count,failures=0,errors=0,skipped=0)
        assert record['method_unchanged']
    outcome = consumer['outcome']
    assert outcome['reviewed_references']==6 and outcome['mapped_scalar_operations']==6
    assert outcome['target_occurrences']==[34,30,4,15,15,42]
    assert outcome['status_pledge']['reviewed_units']==32
    assert outcome['status_pledge']['definition_edge']['resolved'] is True
    assert outcome['status_pledge']['source_comparison']['selected_option']=='I'
    assert outcome['questions']==dict(Q1='UNKNOWN',Q2='UNKNOWN',Q3='PARTIAL')
    effects = {k:r['reviewed_nonspace_characters'] for k,r in consumer['matched_omission'].items()}
    assert len(effects)==3
    for row in consumer['matched_omission'].values():
        assert row['unknown_with_reading']==0
        assert row['unknown_without_reading']==row['reviewed_nonspace_characters']>0
        assert row['outside_unknown_characters_equal']
    missing = consumer['matched_missing_definition']
    assert missing['other_meanings_equal'] and missing['direct_dependencies_equal']
    assert missing['edge']['resolved'] is False
    assert set(missing['question_evidence'])=={'Q1','Q2','Q2.compulsory_common','Q2.possible_common','Q2.common_only'}
    findings = {
        'G03': 'Six exact scalar maps and six raw references survive the twenty-three-meaning BASF status/pledge consumer and installed CLI. Target counts remain 34/30/4/15/15/42 and construction is unchanged. The new typed definition edge is separate from those six raw links.',
        'G12': 'Complete selected German status, issuer negative pledge and capital-market-debt definition reach real P3 and all installed stages with twenty earlier supplied meanings equal. Admission 47, P3 smoke 2 and remaining controls 23 pass. The corrected English comparison binds Option I; statutory priority, covenant compliance and recovery remain unevaluated.',
        'G13': 'The pledge has a resolved typed dependency on its complete debt definition. Actual definition omission preserves the pledge and all earlier meanings, retains six raw dependencies, and exposes the exact unresolved edge and missing target in Q1, Q2 and every Q2 subquestion.',
        'G17': f'Installed attempt 014 passes nine fresh, relocated and offline-restored CLI cases, retaining twenty-three supplied BASF meanings, six raw references, six scalar maps, the definition edge and corrected Option I comparison. Full question/meaning identities agree; {installed["evidence_payload_bytes"]:,} payload bytes pass the 200-MB bound with metadata reserve.',
        'G20': f'R4 binds the status/pledge packet, source correction and real definition-omission effect with all prior consumers. Admission 47, smoke 2 and remaining controls 23 pass. The aggregate passes {aggregate["counts"]["tests"]} controls in {aggregate["wall_seconds"]:.3f} seconds. Aggregate/R4 limits are reviewed at 4500 seconds; engineering checks remain distinct from legal completion.'}
    remaining = {
        'G12': 'Fifteen markers and 537 construction intervals remain unchanged. Other meanings/dispositions, B54 office authority, incorporation, actual facts, statutory priority, covenant compliance, recovery, bilingual redemption wording and independent adjudication remain open.',
        'G13': 'Other onward references, broad automatic discovery and authority/priority adjudication remain open. Correcting the English option citation does not settle the German/English wording discrepancy.',
        'G17': 'OS portability and unlisted optional profiles remain untested. Preserved contractual readings do not establish actual balances, ownership, standing, custody, payment, security creation, covenant compliance or recovery.'}
    actions = {
        'G12': 'Continue coherent source-meaning packages and exact interval dispositions under original authority; first execute the separately reviewed R5 original-coupon-anchor repair after this package is committed.',
        'G13': 'Continue source-specific dependencies and authority review while retaining the tested definition edge, six raw links and unresolved statutory/bilingual questions.'}
    additions = {
        'G03':['basf-status-pledge/attempt-001/result.json','installed/attempt-014/result.json'],
        'G12':['basf-status-pledge/review.json','basf-status-pledge/SOURCE-REVIEW.md','basf-status-pledge/OPTION-COMPARISON-CORRECTION.md','basf-status-pledge/attempt-001/result.json','basf-status-pledge/attempt-001/meaning-evidence.json','checks/basf-pledge-001.xml','installed/attempt-014/result.json'],
        'G13':['basf-status-pledge/attempt-001/consumer.json','basf-status-pledge/attempt-001/result.json'],
        'G17':['installed/attempt-014/result.json','installed/attempt-014/installed-results.json','installed/attempt-014/relocated-results.json','installed/attempt-014/restored-results.json'],
        'G20':['checks/basf-pledge-admission-001-manifest.json','checks/basf-pledge-smoke-001-manifest.json','checks/basf-pledge-001-manifest.json','checks/successor-013.xml','checks/successor-013-manifest.json']}
    ledger, review = read(BASE/'gap-status.json'), read(BASE/'attribution-review.json')
    for rows in (ledger['gaps'],review['gaps']):
        for row in rows:
            key = row['id']
            if key not in findings:
                continue
            row['finding']=findings[key]
            if key in remaining:
                row['remaining']=remaining[key]
            if key in actions:
                row['next_action']=actions[key]
            paths=[PREFIX+p for p in additions[key]]
            if rows is ledger['gaps']:
                row['evidence']=list(dict.fromkeys(row['evidence']+paths))
            else:
                existing={e['path'] for e in row['evidence']}
                row['evidence'].extend({'path':p,'sha256':sha(ROOT/p)} for p in paths if p not in existing)
    for row in review['gaps']+review['packages']:
        for item in row['evidence']:
            if sha(ROOT/item['path'])!=item['sha256']:
                assert item['path']=='src/legalmath/prospectus/successor/closure_program.py',item['path']
                item['sha256']=sha(ROOT/item['path'])
    ledger['last_review']='2026-10-10 Hong Kong; twenty-three supplied meanings, pledge consumer 001, 72 controls across three suites, 599 aggregate checks and installed 014 pass. Currentness is separately reported by closure status; independent legal acceptance remains absent.'
    ledger['regression'].update(path=PREFIX+'checks/successor-013.xml',passed=aggregate['counts']['tests'],wall_seconds=aggregate['wall_seconds'])
    ledger['basf_consumer'].update(path=PREFIX+'basf-status-pledge/attempt-001/result.json',references=6,status_pledge_readings=3,status_pledge_meaning_units=32,status_pledge_review=PREFIX+'basf-status-pledge/review.json',definition_edge=outcome['status_pledge']['definition_edge'],english_comparison_option='I')
    request=json.loads(gzip.decompress((BASE/'basf-status-pledge/attempt-001/request.json.gz').read_bytes()))
    ledger['basf_consumer']['selected_line_uses']=sum(r['role']=='OPERATIVE' for r in request['reviewed_dispositions']['units'])
    ledger['basf_consumer']['selected_headers']=sum(r['role']=='HEADER' for r in request['reviewed_dispositions']['units'])
    ledger['installed_application'].update(path=PREFIX+'installed/attempt-014/result.json',retained_bytes=installed['evidence_payload_bytes'])
    ledger['basf_status_pledge_checks']={'paths':[PREFIX+'checks/'+s+'.xml' for s in ('basf-pledge-admission-001','basf-pledge-smoke-001','basf-pledge-001')], 'passed':72,'omission_characters':effects,'matched_missing_definition':missing}
    save(BASE/'gap-status.json',ledger)
    save(BASE/'attribution-review.json',review)
    sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
    from scripts.prospectus_closure_attribution import report
    save(BASE/'final-attribution.json',report(ROOT))
    print(json.dumps({'status':'UPDATED_INSPECTED_SUMMARIES','gaps':list(findings),'omissions':effects}))

if __name__=='__main__':
    main()
