from pathlib import Path
import sys,json
sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'scripts'),str(Path(__file__).resolve().parents[2]/'src'),'/home/chakwong/python/legalmath']
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from tests.assurance.support import packet,reading,inventory
from assurance_successor_partials import collect


def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v))


def fixture(root):
    directory=root/'ensemble';binding={'source':'original'};revision=digest(binding)
    save(directory/'current-state.json',{'revision':revision})
    save(directory/'revisions.json',[{'revision':revision,'binding':binding}])
    journal=EvidenceJournal(directory/'revisions'/revision/'core/actions',{},maximum_actions=10)
    def interpret(work):
        loc=work/'interpretation'
        for name,value in [('packet',packet()),('candidates',{'reading':reading()}),
            ('inventories-initial',{'atomic-reader':inventory(),'qualification-reader':inventory()}),('claims',[])]:
            save(loc/(name+'.json'),value)
        return {'directory':str(loc.resolve()),'report':{'execution_complete':False}}
    journal.execute('interpretation',{},interpret)
    task={'ensemble':{'evidence_directory':'ensemble'},'shared_packet_hash':digest(packet())}
    return task,journal


def test_partial_proposals_retain_lost_inventory_and_never_claim_completion(tmp_path):
    task,_=fixture(tmp_path);result=collect(tmp_path,task)
    assert len(result['candidates'])==1
    assert result['receipt']['initial_claims_retained']>0 and result['receipt']['active_claim_count']==0
    assert not result['receipt']['complete_investigation'] and not result['receipt']['source_fidelity_established']


@pytest.mark.parametrize('change',['source_identity','candidate_bytes','inventory_bytes','revision_binding','outside_root'])
def test_partial_evidence_rejects_detached_inputs(tmp_path,change):
    task,journal=fixture(tmp_path);loc=journal.directory/'action-0000/interpretation'
    if change=='source_identity':task['shared_packet_hash']='0'*64
    elif change=='candidate_bytes':save(loc/'candidates.json',{})
    elif change=='inventory_bytes':save(loc/'inventories-initial.json',{})
    elif change=='revision_binding':save(tmp_path/'ensemble/revisions.json',[])
    else:task['ensemble']['evidence_directory']='../outside'
    with pytest.raises(LegalMathError):collect(tmp_path,task)
