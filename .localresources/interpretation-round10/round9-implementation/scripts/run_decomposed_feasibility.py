"""Counted small service probe, then optional complete decomposed investigation."""
from argparse import ArgumentParser
from pathlib import Path
from time import monotonic,sleep
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.decomposition import partition,compact_request,piece_request
from legalmath.interpretation.assurance.evaluation import load_frozen,documents,source_packet
from legalmath.interpretation.assurance.engine import Assurance,AssuranceSettings
from legalmath.interpretation.assurance.journal import JournalProvider
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.transport import CompactProvider,transient_service_failure
from legalmath.interpretation.search.providers import Allowance,CodexProvider
from legalmath.interpretation.search.models import Settings

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/'docs/implementation/interpretation-round6/contracts/live.json'
PROBE={'protocol':'legalmath.availability.v1','task':'SERVICE_PROBE',
       'instructions':'Return the structured object with status READY. This tests service availability only; no tools or legal interpretation.'}
SCHEMA={'type':'object','properties':{'status':{'type':'string','enum':['READY']}},
        'required':['status'],'additionalProperties':False}


def run(out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round6/D1'):
        raise ValueError('Use a new D1 attempt directory')
    contract=loads(CONTRACT.read_bytes());ledger=ROOT/'artifacts/interpretation/round2/live-allowance.json'
    before=loads(ledger.read_bytes())
    if digest(before)!=contract['initial_allowance_hash'] or before['maximum']!=100:
        raise LegalMathError('E_STALE_REVIEW')
    if before['maximum']-len(before['calls'])<contract['maximum_new_calls']:raise LegalMathError('E_RESOURCE_LIMIT')
    study=load_frozen(ROOT/'.localresources/interpretation-round5/public-qa-v1/frozen')
    if digest(study)!=contract['study_hash']:raise LegalMathError('E_STALE_REVIEW')
    case=next(c for c in study['cases'] if c['case_id']==contract['case_id'])
    public={k:case[k] for k in ('roots','selected_slice','at')}
    if digest(public)!=contract['public_hash']:raise LegalMathError('E_STALE_REVIEW')
    config=AssuranceSettings.model_validate(contract['settings'])
    if config.total_model_calls+contract['maximum_probes']>contract['maximum_new_calls']:
        raise LegalMathError('E_RESOURCE_LIMIT')
    packet=source_packet(public);pieces=partition(packet,config.inventory_piece_characters,config.inventory_piece_units)
    if 2*(len(pieces)+1)+5>config.total_model_calls:
        raise LegalMathError('E_RESOURCE_LIMIT',details='Cannot admit inventory, three readers, fidelity and criticism')
    out.mkdir(parents=True);save(out/'contract.json',contract);save(out/'allowance-before.json',before)
    save(out/'public-input.json',public);save(out/'packet.json',packet)
    compact_sizes=[len(canonical(compact_request(piece_request(p,'atomic-reader',i,len(pieces),digest(packet))))) for i,p in enumerate(pieces)]
    save(out/'decomposition.json',{'piece_count':len(pieces),'piece_characters':[sum(len(u['text']) for u in p['units']) for p in pieces],
        'compact_piece_request_bytes':compact_sizes,'all_original_units_preserved':True,'probe_bytes':len(canonical(PROBE))})
    allowance=Allowance(ledger,100,reservation_ceiling=len(before['calls'])+contract['maximum_new_calls'])
    provider=CodexProvider(allowance=allowance);probe_settings=Settings(timeout_seconds=90,max_output_bytes=1000)
    probes=JournalProvider(provider,out/'probes',maximum=contract['maximum_probes'],deadline_seconds=210)
    ready=False;errors=[];began=monotonic()
    for i in range(contract['maximum_probes']):
        try:
            value=probes.complete(PROBE,SCHEMA,probe_settings)
            if value.value!={'status':'READY'}:raise LegalMathError('E_SCHEMA')
            ready=True;break
        except Exception as exc:
            errors.append({'attempt':i,'error':getattr(exc,'code',type(exc).__name__),'details':getattr(exc,'details',str(exc))})
            save(out/'probe-errors.json',errors)
            if not transient_service_failure(exc):break
            if i+1<contract['maximum_probes']:sleep(10)
    report=None
    if ready:
        transport=CompactProvider(provider,out/'transport')
        engine=Assurance(out/'investigation',transport,ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',case['at'],config)
        report=engine.drive(documents(public),public['selected_slice'])
    after=loads(ledger.read_bytes());save(out/'allowance-after.json',after)
    if after['maximum']!=100 or after['calls'][:len(before['calls'])]!=before['calls']:
        raise LegalMathError('E_INTEGRITY')
    used=len(after['calls'])-len(before['calls'])
    requests=[loads(p.read_bytes()) for p in [*sorted((out/'probes').glob('call-*/request.json')),
                                              *sorted((out/'transport').glob('call-*/request.json'))]]
    if not 0<used<=contract['maximum_new_calls'] or any(c['request_hash'] not in {digest(r) for r in requests}
            for c in after['calls'][len(before['calls']):]):raise LegalMathError('E_INTEGRITY')
    summary={'engineering_status':'EVIDENCE_RECORDED','service_probe_ready':ready,'new_live_calls':used,
        'remaining_calls':100-len(after['calls']),'wall_seconds':str(monotonic()-began),
        'investigation_status':report['status'] if report else 'NOT_RUN_PROVIDER_UNAVAILABLE',
        'execution_complete':report['execution_complete'] if report else False,
        'candidate_count':len(report['candidate_ids']) if report else 0,
        'findings':report['findings'] if report else [],'probe_failures':errors,
        'failures':report['failures'] if report else [],'legal_accuracy_evaluated':False,
        'ranking_established':False,'release_eligible':False,'source_packet_hash':digest(packet)}
    save(out/'summary.json',summary)
    save(out/'manifest.json',{'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
        for p in sorted(out.rglob('*')) if p.is_file() and '/work/' not in str(p) and p.name!='.lock'}})
    print(canonical({k:v for k,v in summary.items() if k not in ('findings','failures')}).decode())


if __name__=='__main__':
    p=ArgumentParser(description=__doc__);p.add_argument('--out',required=True);run(p.parse_args().out)
