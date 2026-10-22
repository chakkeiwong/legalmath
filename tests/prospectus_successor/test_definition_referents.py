"""Adversarial source identity checks for the finite referent review."""
from copy import deepcopy
import pytest
from legalmath.prospectus.successor import definition_referents as module
from legalmath.prospectus.successor.contracts import digest

def fixture():
    text='BASF SE BASF'
    intervals=[{'start':0,'end':7,'quote':'BASF SE','source_piece_indices':[0]},
               {'start':0,'end':4,'quote':'BASF','source_piece_indices':[0]},
               {'start':8,'end':12,'quote':'BASF','source_piece_indices':[1]}]
    node={'id':'issuer','role':'OPERATIVE','quote':text,'spans':[{'unit':'source'}],
          'reading':{'issuer':'BASF SE','qualification':'No actual substitution established'}}
    row={'record':'D02-issuer','declarations':[deepcopy(intervals[0])],
         'meaning':{'node':'issuer','node_sha256':digest(node),'field':'reading',
                    'reading':deepcopy(node['reading']),'quote':text,'spans':deepcopy(node['spans'])},
         'support':[{'start':0,'end':12,'quote':text}],
         'uses':[{**deepcopy(v),'interval':i,'context':{'start':0,'end':12,'quote':text},
                  'kind':'NAME_COMPONENT' if i==1 else 'BOUND_REFERENT','referent':'NAMED_BASF_SE',
                  'reason':'Source company reference','qualification':'No actual substitution'}
                 for i,v in enumerate(intervals)]}
    record={'id':'D02-issuer','declarations':[0],'uses':[{'interval':i} for i in range(3)]}
    return row,record,intervals,text,{'issuer':node}

def test_full_interval_identity_allows_shared_start_without_collapsing():
    args=fixture();before=deepcopy(args);module._decision(*args);assert args==before

@pytest.mark.parametrize('kind',['missing-use','duplicate-use','reordered-use','wrong-end',
    'wrong-record','wrong-declaration','wrong-context','wrong-support','wrong-meaning',
    'lost-qualification','empty-reason','false-kind','wrong-provenance','nonoperative'])
def test_source_or_identity_corruption_is_refused(kind):
    row,record,intervals,text,nodes=fixture()
    if kind=='missing-use':row['uses'].pop()
    elif kind=='duplicate-use':row['uses'][1]=deepcopy(row['uses'][0])
    elif kind=='reordered-use':row['uses'].reverse()
    elif kind=='wrong-end':row['uses'][1]['end']=7
    elif kind=='wrong-record':row['record']='D01-notes'
    elif kind=='wrong-declaration':row['declarations']=[]
    elif kind=='wrong-context':row['uses'][2]['context']['end']=11
    elif kind=='wrong-support':row['support'][0]['quote']='changed'
    elif kind=='wrong-meaning':row['meaning']['reading']['issuer']='Other'
    elif kind=='lost-qualification':row['uses'][0]['qualification']=''
    elif kind=='empty-reason':row['uses'][0]['reason']='  '
    elif kind=='false-kind':row['uses'][0]['kind']='PROVED_HOLDER'
    elif kind=='wrong-provenance':row['uses'][1]['source_piece_indices']=[1]
    else:
        nodes['issuer']['role']='HEADER';row['meaning']['node_sha256']=digest(nodes['issuer'])
    with pytest.raises(ValueError):module._decision(row,record,intervals,text,nodes)
