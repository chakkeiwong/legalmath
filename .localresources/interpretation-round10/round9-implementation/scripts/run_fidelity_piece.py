"""One reviewed four-pair diagnostic, never completion of the parent matrix."""
from argparse import ArgumentParser
from pathlib import Path
from time import monotonic
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.assurance.journal import JournalProvider
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.semantics import Fidelity,fidelity_request,validate_fidelity
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import Allowance,CodexProvider

ROOT=Path(__file__).resolve().parents[1]


def run(out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round6/D1S'):
        raise ValueError('Use a new D1S attempt directory')
    contract=loads((ROOT/'docs/implementation/interpretation-round6/contracts/piece.json').read_bytes())
    ledger=ROOT/'artifacts/interpretation/round2/live-allowance.json';before=loads(ledger.read_bytes())
    if digest(before)!=contract['initial_allowance_hash'] or before['maximum']!=100:
        raise LegalMathError('E_STALE_REVIEW')
    prior=ROOT/contract['prior'];manifest=loads((prior/'manifest.json').read_bytes())
    if digest(manifest)!=contract['prior_manifest_hash']:raise LegalMathError('E_STALE_REVIEW')
    for name,expected in manifest['files'].items():
        p=(prior/name).resolve()
        if not p.is_relative_to(prior.resolve()) or raw_digest(p.read_bytes())!=expected:raise LegalMathError('E_INTEGRITY')
    packet=loads((prior/'packet.json').read_bytes());claims=loads((prior/'claims.json').read_bytes())
    candidates=loads((prior/'candidates.json').read_bytes())
    pairs=[(c['claim_id'],cid) for c in claims if c['relevance']!='CONTEXT' for cid in candidates]
    batch=pairs[:4];request=fidelity_request(packet,claims,candidates,batch)
    if digest(request)!=contract['request_hash'] or len(pairs)!=204:raise LegalMathError('E_STALE_REVIEW')
    out.mkdir(parents=True);save(out/'contract.json',contract);save(out/'allowance-before.json',before)
    encoded_pairs=[list(p) for p in pairs]
    save(out/'matrix.json',{'all_pairs':encoded_pairs,'selected_pairs':encoded_pairs[:4],'selection':'First four in retained claim-major order',
        'unchecked_pairs':encoded_pairs[4:],'full_matrix_complete':False})
    allowance=Allowance(ledger,100,reservation_ceiling=len(before['calls'])+1)
    provider=JournalProvider(CompactProvider(CodexProvider(allowance=allowance),out/'transport'),out/'calls',maximum=1,deadline_seconds=190)
    began=monotonic();checked=None;error=None
    try:
        answer=provider.complete(request,Fidelity.model_json_schema(),Settings(timeout_seconds=180,max_input_bytes=200000,max_output_bytes=200000))
        checked=validate_fidelity(answer.value,packet,claims,candidates,batch)
        save(out/'validated.json',checked)
    except Exception as exc:error={'error':getattr(exc,'code',type(exc).__name__),'details':str(getattr(exc,'details',None) or exc)}
    after=loads(ledger.read_bytes());save(out/'allowance-after.json',after)
    if (after['maximum']!=100 or after['calls'][:len(before['calls'])]!=before['calls'] or
        len(after['calls'])!=len(before['calls'])+1 or after['calls'][-1]['request_hash']!=digest(compact_request(request))):
        raise LegalMathError('E_INTEGRITY')
    summary={'engineering_status':'EVIDENCE_RECORDED','diagnostic_status':'VALIDATED_PARTIAL' if checked else 'FAILED_DIAGNOSTIC',
        'requested_pairs':4,'validated_pairs':len(checked['checks']) if checked else 0,'parent_pairs':len(pairs),
        'remaining_unchecked_pairs':len(pairs)-(len(checked['checks']) if checked else 0),'new_live_calls':1,
        'remaining_calls':100-len(after['calls']),'wire_request_bytes':len(canonical(compact_request(request))),
        'wall_seconds':str(monotonic()-began),'error':error,'execution_complete':False,
        'legal_accuracy_evaluated':False,'release_eligible':False}
    save(out/'summary.json',summary)
    save(out/'manifest.json',{'files':{str(p.relative_to(out)):raw_digest(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}})
    print(summary)


if __name__=='__main__':
    p=ArgumentParser(description=__doc__);p.add_argument('--out',required=True);run(p.parse_args().out)
