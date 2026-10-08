"""Both study arms must receive the same complete selected source set."""
from pathlib import Path
import copy
import shutil
import sys
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from assurance_successor_sources import prepare,read_source
from run_assurance_successor import read,OUT


def copied_study(tmp_path):
    tasks=[read(ROOT/r['path']) for r in read(OUT/'task-freeze.json')['tasks']]
    frozen=read(OUT/'study-source-freeze.json');out=tmp_path/OUT.relative_to(ROOT)
    files=[OUT/'study-source-freeze.json',OUT/'S1/attempt-01/appendix/input.json']
    files += [ROOT/ref['path'] for row in frozen['tasks'] for ref in row['sources']]
    for source in files:
        target=tmp_path/source.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    return out,tasks,frozen


def test_moved_checkout_keeps_original_appendix_receipt_and_identical_packets(tmp_path):
    out,tasks,frozen=copied_study(tmp_path)
    receipt=out/'S1/attempt-01/appendix/input.json';before=receipt.read_bytes()
    prepared=prepare(tmp_path,out,tasks)
    assert receipt.read_bytes()==before
    assert read(out/'study-source-freeze.json')==frozen
    for row in frozen['tasks']:
        assert prepared[row['task_id']]['task']['packet']==row['packet']
        assert [s['data'] for s in prepared[row['task_id']]['sources']]==[
            (ROOT/ref['path']).read_bytes() for ref in row['sources']]


@pytest.mark.parametrize('mutation',['task','hash','url','media','escape','symlink','duplicate','missing','bytes'])
def test_moved_checkout_rejects_detached_or_changed_appendix(tmp_path,mutation):
    from legalmath.canonical import canonical
    out,tasks,frozen=copied_study(tmp_path)
    row=next(r for r in frozen['tasks'] if r['task_id']=='26ec35')
    ref=next(r for r in row['sources'] if r['media_type']=='application/pdf')
    if mutation=='task':row['original_task_hash']='0'*64
    elif mutation=='hash':ref['sha256']='0'*64
    elif mutation=='url':ref['url']='https://example.invalid/another-appendix.pdf'
    elif mutation=='media':ref['media_type']='text/plain'
    elif mutation=='escape':ref['path']='../outside.pdf'
    elif mutation=='symlink':
        source=tmp_path/ref['path'];source.unlink();source.symlink_to(ROOT/ref['path'])
    elif mutation=='duplicate':row['sources'].append(copy.deepcopy(ref))
    elif mutation=='bytes':(tmp_path/ref['path']).write_bytes(b'changed appendix')
    frozen_path=out/'study-source-freeze.json'
    if mutation=='missing':frozen_path.unlink()
    else:frozen_path.write_bytes(canonical(frozen))
    with pytest.raises(LegalMathError):prepare(tmp_path,out,tasks)


def test_retained_authentication_appendix_is_an_explicit_root_for_both_arms():
    tasks=[read(ROOT/r['path']) for r in read(OUT/'task-freeze.json')['tasks']]
    prepared=prepare(ROOT,OUT,tasks)
    auth=prepared['26ec35'];original=next(t for t in tasks if t['task_id']=='26ec35')
    assert len(auth['sources'])==2
    assert len(auth['task']['packet']['units'])>len(original['packet']['units'])
    selected={u['unit_id']:u['text'] for u in auth['task']['packet']['units']}
    assert all(selected[u['unit_id']]==u['text'] for u in original['packet']['units'])
    assert all(u['text']==selected[u['unit_id']] for u in original['packet']['units'])
    for case in read(OUT/'conditional-case-reference.json')['cases']:
        units={u['unit_id']:u['text'] for u in prepared[case['task_id']]['task']['packet']['units']}
        assert all(q['quote'] in units[q['unit_id']] for q in case['evidence'])


def test_changed_source_is_rejected_before_it_can_enter_either_arm(tmp_path):
    p=tmp_path/'source.txt';p.write_text('original')
    from legalmath.canonical import raw_digest
    ref={'path':'source.txt','sha256':raw_digest(p.read_bytes()),'url':'https://apps.sfc.hk/example','media_type':'text/plain'}
    p.write_text('changed')
    with pytest.raises(LegalMathError):read_source(tmp_path,ref)


def test_compact_v2_preserves_document_identity_and_exact_source_content():
    from legalmath.interpretation.assurance.decomposition import compact_request
    row=read(OUT/'study-source-freeze.json')['tasks'][-1]
    request={'source_packet':row['packet']}
    legacy=compact_request(request,profile='v1');current=compact_request(request,profile='v2')
    assert 'source_packet_document_locators' not in legacy
    assert len(current['source_packet_document_locators'])==2
    assert compact_request(current,profile='v2')==current
    fields=lambda v:[(u['unit_id'],u['text'],u['normative']) for u in v['source_packet']['units']]
    assert fields(request)==fields(current)==fields(legacy)
    expected={u['locator'].rsplit(' chars ',1)[0] for u in row['packet']['units']}
    actual={url for urls in current['source_packet_document_locators'].values() for url in urls}
    assert expected==actual


@pytest.mark.parametrize('profile',['v1','v2'])
def test_historical_and_current_transport_receipts_reconstruct_their_own_bytes(tmp_path,profile):
    from legalmath.canonical import canonical
    from legalmath.interpretation.assurance.decomposition import compact_request
    from legalmath.interpretation.assurance.checkpoints import receipt,verify_receipt
    packet=read(OUT/'study-source-freeze.json')['tasks'][0]['packet']
    request={'task':'SOURCE_INVENTORY','source_packet':packet};wire=compact_request(request,profile=profile)
    ledger=tmp_path/'ledger.json';ledger.write_bytes(canonical({'maximum':1,
        'calls':[{'request_hash':digest(wire),'issued_at_ns':'1'}]}))
    response={'value':{'synthetic_only':True},'provenance':{'allowance_slot':1,
        'request_hash':digest(wire),'provider_route_hash':'a'*64,'original_request_hash':digest(request),
        'wire_request_hash':digest(wire),'compact_request':wire,'transport_profile':'exact-source-text.compact.'+profile}}
    value=receipt(request,response,ledger,'a'*64)
    verify_receipt(value,request,response,'a'*64)
