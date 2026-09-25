"""One reviewed live assurance investigation, bounded by the existing allowance."""
from argparse import ArgumentParser
from pathlib import Path
from time import monotonic
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.evaluation import load_frozen,documents,source_packet
from legalmath.interpretation.assurance.engine import Assurance,AssuranceSettings
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.providers import Allowance,CodexProvider

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/'docs/implementation/interpretation-round5/contracts/feasibility.json'


def run(out):
    out=Path(out).resolve();contract=loads(CONTRACT.read_bytes())
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round5/C2'):
        raise ValueError('Use a fresh C2 attempt directory')
    frozen=ROOT/'.localresources/interpretation-round5/public-qa-v1/frozen'
    study=load_frozen(frozen)
    if digest(study)!=contract['study_hash']:raise LegalMathError('E_STALE_REVIEW')
    case=next(c for c in study['cases'] if c['case_id']==contract['case_id'])
    public={k:case[k] for k in ('roots','selected_slice','at')}
    if digest(public)!=contract['public_input_hash']:raise LegalMathError('E_STALE_REVIEW')
    ledger_path=ROOT/'artifacts/interpretation/round2/live-allowance.json'
    before=loads(ledger_path.read_bytes())
    if digest(before)!=contract['initial_allowance_hash'] or before['maximum']!=100:
        raise LegalMathError('E_STALE_REVIEW',details='Allowance changed since feasibility freeze; review remaining work')
    settings=AssuranceSettings.model_validate(contract['settings'])
    ceiling=len(before['calls'])+settings.total_model_calls
    if ceiling>before['maximum'] or settings.total_model_calls!=contract['maximum_new_calls']:
        raise LegalMathError('E_RESOURCE_LIMIT')
    out.mkdir(parents=True);save(out/'contract.json',contract);save(out/'allowance-before.json',before)
    save(out/'public-input.json',public);save(out/'packet.json',source_packet(public))
    # This provider receives only public source requests, never the study's hidden
    # scenarios, formula, accepted labels or authored reference dossier.
    provider=CodexProvider(allowance=Allowance(ledger_path,100,reservation_ceiling=ceiling))
    engine=Assurance(out/'investigation',provider,ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',case['at'],settings)
    began=monotonic();report=engine.drive(documents(public),public['selected_slice'])
    after=loads(ledger_path.read_bytes());save(out/'allowance-after.json',after)
    if after['calls'][:len(before['calls'])]!=before['calls'] or after['maximum']!=100:
        raise LegalMathError('E_INTEGRITY')
    used=len(after['calls'])-len(before['calls'])
    statuses=[loads(p.read_bytes()) for p in sorted((out/'investigation/calls').glob('call-*/status.json'))]
    requests=[loads(p.read_bytes()) for p in sorted((out/'investigation/calls').glob('call-*/request.json'))]
    issued=[c['request_hash'] for c in after['calls'][len(before['calls']):]]
    if not 0<used<=contract['maximum_new_calls'] or any(h not in [digest(r) for r in requests] for h in issued):
        raise LegalMathError('E_INTEGRITY',details='Paid action missing from the retained request journal')
    for request in requests:
        if any(k in request for k in ('reference','accepted','binding_reading','snapshots')):
            raise LegalMathError('E_INTEGRITY',details='Hidden study labels crossed the dispatch boundary')
    if report['release_eligible'] or report['legal_accuracy_evaluated'] or report['probability_of_legal_correctness'] is not None:
        raise LegalMathError('E_AUTHORITY')
    summary={'status':'LIVE_FEASIBILITY_RECORDED','case_id':case['case_id'],'new_live_calls':used,
        'remaining_allowance':100-len(after['calls']),'wall_seconds':str(monotonic()-began),
        'investigation_status':report['status'],'execution_complete':report['execution_complete'],
        'candidate_count':len(report['candidate_ids']),'findings':report['findings'],
        'failures':report['failures'],'task_counts':{t:sum(s['task']==t for s in statuses) for t in sorted({s['task'] for s in statuses})},
        'source_packet_hash':report.get('source_packet_hash'),'legal_accuracy_evaluated':False,
        'method_ranking_established':False,'review_cost_saving_measured':False,'release_eligible':False,
        'meaning':'One source family and one bounded assurance invocation; a recorded result is not a successful interpretation claim.'}
    save(out/'summary.json',summary)
    save(out/'manifest.json',{'contract_hash':digest(contract),'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
        for p in sorted(out.rglob('*')) if p.is_file() and '/work/' not in str(p) and p.name!='.lock'}})
    print(canonical({k:v for k,v in summary.items() if k not in ('findings','failures')}).decode())


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);run(parser.parse_args().out)
