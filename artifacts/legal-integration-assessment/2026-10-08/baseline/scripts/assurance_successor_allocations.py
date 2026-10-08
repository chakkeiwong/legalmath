"""Reviewed planning amendments preserve original allocations and spent slices."""
from pathlib import Path
import xml.etree.ElementTree as ET
from legalmath.canonical import raw_digest
from legalmath.errors import LegalMathError
from run_assurance_successor import read,save,sha


def effective_allocation(directory,budget,root):
    path=Path(directory)/'allocation-amendment-001.json'
    if not path.exists():return budget
    value=read(path)
    if (value['original_allocation_sha256']!=sha(Path(directory)/'allocation.json') or
        value['old_arm_ceiling']!=budget['arm_ceiling'] or value['new_arm_ceiling']!=120 or
        budget['global_ceiling']!=500 or budget['reserve_for_evaluation']!=40 or
        value['refund_reservations'] or not value['equal_ceiling_for_both_arms']):
        raise LegalMathError('E_AUTHORITY',details='Unreviewed allocation amendment')
    for field in ('review','focused_tests'):
        ref=value[field];p=Path(root)/ref['path']
        if sha(p)!=ref['sha256']:raise LegalMathError('E_INTEGRITY')
    tree=ET.parse(Path(root)/value['focused_tests']['path']).getroot()
    suites=[tree] if tree.tag=='testsuite' else list(tree)
    if not sum(int(s.get('tests','0')) for s in suites) or any(
        int(s.get(k,'0')) for s in suites for k in ('failures','errors','skipped')):
        raise LegalMathError('E_AUTHORITY',details='Allocation repair checks did not pass')
    return {**budget,'arm_ceiling':120,'original_arm_ceiling':budget['arm_ceiling'],
            'amendment':{'path':str(path),'sha256':sha(path)},
            'exploratory_capacity_amendment':True}


def amend_slice(path,budget,grant):
    """A slice is a planning limit within the existing grant, never a new grant."""
    path=Path(path)
    if not path.exists() or 'amendment' not in budget:return
    v=read(path);new=budget['arm_ceiling'];old=budget['original_arm_ceiling']
    if v['grant_hash']!=sha(grant):raise LegalMathError('E_INTEGRITY')
    amendment=budget['amendment']
    if sha(amendment['path'])!=amendment['sha256']:raise LegalMathError('E_INTEGRITY')
    if v['maximum']==new:
        receipt=v.get('planning_amendment')
        if not receipt:
            # Tasks first created after the amendment were never 60-call slices.
            # Check the existing shared reservations before recording that origin.
            history=path.parent/'allocation-history'
            prior_files=list(history.glob(path.stem+'-*.json')) if history.exists() else []
            if any(read(p).get('maximum')==old for p in prior_files):
                raise LegalMathError('E_INTEGRITY',details='Migrated slice lost its original receipt')
            g=read(grant);ledger=read(Path(grant).parent/g['ledger'])['calls'];slots=set()
            for row in v['reservations']:
                slot=row['global_slot']
                if (row['status']!='GLOBALLY_RESERVED' or type(slot)is not int or
                    not 1<=slot<=len(ledger) or slot in slots or ledger[slot-1]['request_hash']!=row['request_hash']):
                    raise LegalMathError('E_INTEGRITY',details='Native slice has detached or repeated reservations')
                slots.add(slot)
            if len(slots)>new:raise LegalMathError('E_INTEGRITY')
            raw=path.read_bytes();prior=history/(path.stem+'-'+raw_digest(raw)+'.json')
            history.mkdir(exist_ok=True);prior.write_bytes(raw)
            receipt={'amendment':amendment,'prior_path':str(prior.resolve()),'prior_sha256':raw_digest(raw),
                'reservations_preserved':len(v['reservations']),'origin':'CREATED_WITH_REVIEWED_LIMIT'}
            v['planning_amendment']=receipt;save(path,v)
        if receipt['amendment']!=amendment:raise LegalMathError('E_INTEGRITY')
        prior=Path(receipt['prior_path'])
        if sha(prior)!=receipt['prior_sha256']:raise LegalMathError('E_INTEGRITY')
        original=read(prior)
        prior_limit=new if receipt.get('origin')=='CREATED_WITH_REVIEWED_LIMIT' else old
        if (original['maximum']!=prior_limit or original['grant_hash']!=v['grant_hash'] or
            v['reservations'][:len(original['reservations'])]!=original['reservations']):
            raise LegalMathError('E_INTEGRITY',details='Spent slice history changed')
        return
    if v['maximum']!=old or len(v['reservations'])>old or 'planning_amendment' in v:
        raise LegalMathError('E_INTEGRITY')
    raw=path.read_bytes();prior=path.parent/'allocation-history'/(path.stem+'-'+raw_digest(raw)+'.json')
    prior.parent.mkdir(exist_ok=True)
    if prior.exists() and prior.read_bytes()!=raw:raise LegalMathError('E_INTEGRITY')
    prior.write_bytes(raw)
    v.update(maximum=new,planning_amendment={'amendment':amendment,'prior_path':str(prior.resolve()),
        'prior_sha256':raw_digest(raw),'reservations_preserved':len(v['reservations'])})
    save(path,v)
