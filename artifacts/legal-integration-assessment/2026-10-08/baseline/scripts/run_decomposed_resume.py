"""Resume the checked inventories after repairing exact source-derivative import."""
from argparse import ArgumentParser
from pathlib import Path
from time import monotonic
from legalmath.canonical import digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.engine import Assurance,AssuranceSettings
from legalmath.interpretation.assurance.evaluation import documents,source_packet
from legalmath.interpretation.assurance.journal import RetainedProvider
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.search.providers import Allowance,CodexProvider

ROOT=Path(__file__).resolve().parents[1]


def run(out,phase='D1R'):
    out=Path(out).resolve()
    names={'D1R':'resume.json','D1F':'final.json'}
    if phase not in names or out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round6'/phase):
        raise ValueError('Use a new reviewed successor attempt directory')
    contract=loads((ROOT/'docs/implementation/interpretation-round6/contracts'/names[phase]).read_bytes())
    prior=ROOT/contract['prior'];ledger=ROOT/'artifacts/interpretation/round2/live-allowance.json'
    before=loads(ledger.read_bytes())
    if digest(before)!=contract['initial_allowance_hash'] or before['maximum']!=100:
        raise LegalMathError('E_STALE_REVIEW')
    if 100-len(before['calls'])<contract['maximum_new_calls']:raise LegalMathError('E_RESOURCE_LIMIT')
    public=loads((prior/'public-input.json').read_bytes());packet=source_packet(public)
    if digest(public)!=contract['public_hash'] or digest(packet)!=contract['packet_hash']:
        raise LegalMathError('E_STALE_REVIEW')
    if raw_digest((prior/'investigation/manifest.json').read_bytes())!=contract['prior_manifest_hash']:
        raise LegalMathError('E_INTEGRITY')
    config=AssuranceSettings.model_validate(contract['settings'])
    if config.total_model_calls>contract.get('replay_actions',8)+contract['maximum_new_calls']:raise LegalMathError('E_RESOURCE_LIMIT')
    out.mkdir(parents=True);save(out/'contract.json',contract);save(out/'allowance-before.json',before)
    save(out/'public-input.json',public);save(out/'packet.json',packet)
    allowance=Allowance(ledger,100,reservation_ceiling=len(before['calls'])+contract['maximum_new_calls'])
    compact=CompactProvider(CodexProvider(allowance=allowance),out/'transport')
    provider=RetainedProvider(compact,prior/'investigation',ledger,new_tasks=contract['new_tasks'])
    began=monotonic()
    report=Assurance(out/'investigation',provider,ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',
        public['at'],config).drive(documents(public),public['selected_slice'])
    after=loads(ledger.read_bytes());save(out/'allowance-after.json',after)
    used=len(after['calls'])-len(before['calls'])
    if after['maximum']!=100 or after['calls'][:len(before['calls'])]!=before['calls'] or not 0<=used<=contract['maximum_new_calls']:
        raise LegalMathError('E_INTEGRITY')
    hashes={digest(loads(p.read_bytes())) for p in (out/'transport').glob('call-*/request.json')}
    if any(c['request_hash'] not in hashes for c in after['calls'][len(before['calls']):]):
        raise LegalMathError('E_INTEGRITY')
    replayed=[]
    for p in sorted((out/'investigation/calls').glob('call-*/response.json')):
        v=loads(p.read_bytes());prov=v['provenance']
        if prov.get('new_live_invocation') is False:replayed.append(prov['allowance_slot'])
    summary={'engineering_status':'EVIDENCE_RECORDED','investigation_status':report['status'],
        'execution_complete':report['execution_complete'],'new_live_calls':used,'remaining_calls':100-len(after['calls']),
        'replayed_reservations':replayed,'candidate_count':len(report['candidate_ids']),
        'wall_seconds':str(monotonic()-began),'failures':report['failures'],'findings':report['findings'],
        'legal_accuracy_evaluated':False,'ranking_established':False,'release_eligible':False}
    save(out/'summary.json',summary)
    save(out/'manifest.json',{'files':{str(p.relative_to(out)):raw_digest(p.read_bytes()) for p in sorted(out.rglob('*'))
        if p.is_file() and '/work/' not in str(p) and p.name!='.lock'}})
    print({k:v for k,v in summary.items() if k not in ('failures','findings')})


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    parser.add_argument('--phase',choices=('D1R','D1F'),default='D1R');args=parser.parse_args();run(args.out,args.phase)
