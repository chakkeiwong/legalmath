"""A completed mechanism probe permits scheduling, never study promotion."""
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from run_assurance_successor import read,sha
from assurance_successor_audit import journal_receipt
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.complete_investigation import verify
from legalmath.interpretation.assurance import fidelity_v2
from legalmath.interpretation.assurance.integration_contract import read_evidence
from legalmath.canonical import raw_digest


def historical_replay(root, prior, archive):
    """Check old evidence in an isolated tree containing its exact old sources.

    The current verifier checks the recorded replay. This is historical evidence,
    not a conformance result for today's implementation. Only implementation
    bytes may come from the reviewed archive; all other evidence must still match.
    """
    root=Path(root)
    archive_bytes=read_evidence(archive,root,json_value=False)
    replay=read_evidence(prior['replay']['dossier'],root)
    refs={}
    for ref in [*prior['evidence'],prior['replay']['dossier'],*replay['upstream_inputs']]:
        if ref['path'] in refs and refs[ref['path']]!=ref:
            raise LegalMathError('E_INTEGRITY',details='Conflicting historical input hashes')
        refs[ref['path']]=ref
    changed=[]
    with TemporaryDirectory(prefix='legalmath-historical-pilot-') as temporary:
        snapshot=Path(temporary)
        with ZipFile(root/archive['path']) as zipped:
            for name,ref in refs.items():
                relative=Path(name)
                if relative.is_absolute() or '..' in relative.parts:
                    raise LegalMathError('E_REFERENCE')
                if name.startswith('src/legalmath/'):
                    try:data=zipped.read(name)
                    except KeyError as exc:raise LegalMathError('E_REFERENCE',details=name) from exc
                    if raw_digest(data)!=ref['sha256']:raise LegalMathError('E_HASH_MISMATCH',details=name)
                    if not (root/name).is_file() or sha(root/name)!=ref['sha256']:changed.append(name)
                else:data=read_evidence(ref,root,json_value=False)
                destination=snapshot/name;destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(data)
        checked=verify(snapshot,prior)
    return {'verification':checked,'implementation_archive':archive,
        'archive_bytes_sha256':raw_digest(archive_bytes),'changed_current_sources':changed,
        'current_implementation_conformance':False}


def reviewed_pilot(directory,root):
    path=Path(directory)/'pilot-scheduling.json'
    if not path.exists():return None
    receipt=read(path)
    def load(name):
        return read_evidence(receipt[name],root)
    read_evidence(receipt['review'],root,json_value=False)
    prior=load('replay_dossier')
    replay_check=historical_replay(root,prior,receipt['implementation_archive'])
    packet=load('packet');candidates=load('candidates');claims=load('claims');questions=load('questions')
    if (read(Path(root)/prior['packet']['path'])!=packet or read(Path(root)/prior['candidates']['path'])!=candidates or
        read(Path(root)/prior['claims']['path'])!=claims or prior['questions']!=questions or
        not prior['core']['execution_complete'] or not prior['replay']):
        raise LegalMathError('E_INTEGRITY',details='Pilot replay and live source/readings differ')
    frozen=load('source_freeze')
    task=next((t for t in frozen['tasks'] if t['task_id']==receipt['task_id']),None)
    if task is None or task['packet']!=packet or task['packet_hash']!=digest(packet):
        raise LegalMathError('E_INTEGRITY',details='Pilot is not the frozen source task')
    load('scoped_journal')
    journal,state=journal_receipt(Path(root)/receipt['scoped_journal']['path'])
    mapping={r['candidate_id']:r['question'] for r in questions['assignments']}
    batches=defaultdict(dict);pairs={}
    for action in state['actions']:
        if action['status']!='EXECUTED':continue
        request=action['spec']['inputs']['request'];spec=request['investigation']
        result=read(journal.directory/action['result_file'])
        if result['status']!='VALIDATED_PROPOSAL':continue
        required=[(p['claim_id'],p['candidate_id']) for p in request['required_pairs']]
        fidelity_v2.validate(result['value'],packet,claims,candidates,mapping,required)
        batches[spec['batch']][(spec['round'],spec['perspective'])]=True
        pairs[spec['batch']]=set(required)
    expected={(r,p) for r in (1,2) for p in ('source-first','qualification-first')}
    complete=[b for b,actions in batches.items() if set(actions)==expected]
    addressed=set().union(*(pairs[b] for b in complete)) if complete else set()
    if len(complete)<3 or len(addressed)<36 or receipt['study_promotion'] is not False or receipt['workers']!=4:
        raise LegalMathError('E_REFERENCE',details='Insufficient measured mechanism pilot')
    return {'receipt':{'path':str(path),'sha256':sha(path)},'completed_probe_batches':len(complete),
        'probe_pairs':len(addressed),'scope':'Scheduling only; entire study criteria remain unchanged',
        'workers':4,'continuation_id':'reviewed-breadth.'+sha(path),'study_promotion':False,
        'historical_replay':replay_check}
