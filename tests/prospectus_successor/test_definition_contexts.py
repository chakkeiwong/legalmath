"""Adverse source-context checks separate from the complete-answer oracle."""
from copy import deepcopy
import pytest
from legalmath.prospectus.successor import definition_contexts as module
from legalmath.prospectus.successor.contracts import digest


def fixture():
    text='ICSD ICSDs'
    intervals=[{'start':0,'end':4,'quote':'ICSD','source_piece_indices':[0]},
               {'start':5,'end':10,'quote':'ICSDs','source_piece_indices':[1]}]
    node={'id':'clearing','role':'OPERATIVE','quote':text,'spans':[{'unit':'source'}],
          'reading':{'meaning':'each and both systems','qualification':'Actual custody not established'}}
    meaning={'node':'clearing','node_sha256':digest(node),'field':'reading',
             'reading':deepcopy(node['reading']),'quote':text,'spans':deepcopy(node['spans'])}
    record={'id':'D10-test','declarations':[0,1],'uses':[{'interval':0},{'interval':1}]}
    row={'record':'D10-test','concept':'systems','reason':'Exact declaration distinguishes each from the pair',
         'declarations':deepcopy(intervals),'meaning':meaning,'extra_meanings':[],
         'uses':[{**deepcopy(v),'interval':i,'kind':'BOUND_CONTEXTUALLY',
             'number':'EACH_OR_RELEVANT_ICSD' if i==0 else 'BOTH_ICSDS',
             'context':{'start':0,'end':10,'quote':text}} for i,v in enumerate(intervals)]}
    return row,record,intervals,text,{'clearing':node}


def test_each_and_both_preserve_source_qualifications():
    args=fixture()
    before=deepcopy(args)
    module._decision(*args)
    assert args==before


@pytest.mark.parametrize('kind',['plural','singular','lost-use','duplicate-use','reorder',
    'wrong-record','wrong-declaration','wrong-context','wrong-quote','wrong-provenance',
    'wrong-meaning','lost-qualification','wrong-node','nonoperative','false-kind'])
def test_context_decision_cannot_hide_source_or_identity_mismatch(kind):
    row,record,intervals,text,nodes=fixture()
    if kind=='plural':row['uses'][1]['number']='EACH_OR_RELEVANT_ICSD'
    elif kind=='singular':row['uses'][0]['number']='BOTH_ICSDS'
    elif kind=='lost-use':row['uses'].pop()
    elif kind=='duplicate-use':row['uses'][1]=deepcopy(row['uses'][0])
    elif kind=='reorder':row['uses'].reverse()
    elif kind=='wrong-record':row['record']='D09-test'
    elif kind=='wrong-declaration':row['declarations'].pop()
    elif kind=='wrong-context':row['uses'][1]['context']['end']=9
    elif kind=='wrong-quote':row['uses'][1]['quote']='ICSD'
    elif kind=='wrong-provenance':row['uses'][1]['source_piece_indices']=[0]
    elif kind=='wrong-meaning':row['meaning']['reading']['meaning']='one system'
    elif kind=='lost-qualification':
        del nodes['clearing']['reading']['qualification']
        row['meaning']['reading']=deepcopy(nodes['clearing']['reading'])
        row['meaning']['node_sha256']=digest(nodes['clearing'])
    elif kind=='wrong-node':row['meaning']['node']='unrelated'
    elif kind=='nonoperative':
        nodes['clearing']['role']='HEADER'
        row['meaning']['node_sha256']=digest(nodes['clearing'])
    else:row['uses'][0]['kind']='RESOLVED'
    with pytest.raises(ValueError):module._decision(row,record,intervals,text,nodes)
