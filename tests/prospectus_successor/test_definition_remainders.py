"""Source evidence, overlap identity and unresolved-premise corruption checks."""
from copy import deepcopy
import pytest
from legalmath.prospectus.successor import definition_remainders as module
from legalmath.prospectus.successor.contracts import digest

def fixture():
    text='BASF SE BASF'
    intervals=[{'start':0,'end':7,'quote':'BASF SE','source_piece_indices':[0]},
        {'start':0,'end':4,'quote':'BASF','source_piece_indices':[0]},
        {'start':8,'end':12,'quote':'BASF','source_piece_indices':[1]}]
    node={'id':'source','role':'OPERATIVE','quote':text,'spans':[{'unit':'source'}],
        'legal_reading':'Conditional source role, actual appointment unestablished',
        'selection_authority':[{'unit':'final','quote':'Named agent'}]}
    row={'record':'U10-calculation-agent','declarations':[deepcopy(intervals[0])],
        'reading':'Conditional role retaining final-term naming and template placeholder',
        'open_issues':['ACTUAL_APPOINTMENT_OPEN'],
        'source_evidence':[{'node':'source','node_sha256':digest(node),'evidence':deepcopy(node)}],
        'support':[{'start':0,'end':12,'quote':text}],
        'uses':[{**deepcopy(v),'interval':i,'context':{'start':0,'end':12,'quote':text},
            'kind':'CONDITIONAL_ROLE','reason':'Exact conditional role reference',
            'open_issues':['ACTUAL_APPOINTMENT_OPEN']} for i,v in enumerate(intervals)]}
    record={'id':row['record'],'declarations':[0],'uses':[{'interval':i} for i in range(3)]}
    return row,record,intervals,text,{'source':node}

def test_full_interval_identity_and_string_reading_preserved():
    args=fixture();before=deepcopy(args);module._decision(*args);assert args==before

def test_structured_reading_preserved():
    row,record,intervals,text,nodes=fixture()
    nodes['source']['legal_reading']={'reading':'Conditional','qualification':'Actual appointment open'}
    row['source_evidence'][0].update(evidence=deepcopy(nodes['source']),node_sha256=digest(nodes['source']))
    module._decision(row,record,intervals,text,nodes)

@pytest.mark.parametrize('kind',['missing-use','duplicate-use','reordered-use','wrong-end',
    'wrong-record','wrong-declaration','wrong-context','wrong-support','wrong-node',
    'lost-authority','wrong-node-hash','lost-open-issues','empty-reading','empty-reason',
    'false-kind','wrong-provenance','nonoperative','duplicate-node','lost-node','wrong-issue'])
def test_source_or_identity_corruption_is_refused(kind):
    row,record,intervals,text,nodes=fixture()
    if kind=='missing-use':row['uses'].pop()
    elif kind=='duplicate-use':row['uses'][1]=deepcopy(row['uses'][0])
    elif kind=='reordered-use':row['uses'].reverse()
    elif kind=='wrong-end':row['uses'][1]['end']=7
    elif kind=='wrong-record':row['record']='U08-fiscal-agent'
    elif kind=='wrong-declaration':row['declarations']=[]
    elif kind=='wrong-context':row['uses'][2]['context']['end']=11
    elif kind=='wrong-support':row['support'][0]['quote']='changed'
    elif kind=='wrong-node':row['source_evidence'][0]['evidence']['legal_reading']='Unconditional'
    elif kind=='lost-authority':row['source_evidence'][0]['evidence']['selection_authority']=[]
    elif kind=='wrong-node-hash':row['source_evidence'][0]['node_sha256']='0'*64
    elif kind=='lost-open-issues':row['open_issues']=[]
    elif kind=='empty-reading':row['reading']='  '
    elif kind=='empty-reason':row['uses'][0]['reason']='  '
    elif kind=='false-kind':row['uses'][0]['kind']='PROVED'
    elif kind=='wrong-provenance':row['uses'][1]['source_piece_indices']=[1]
    elif kind=='duplicate-node':row['source_evidence'].append(deepcopy(row['source_evidence'][0]))
    elif kind=='lost-node':row['source_evidence']=[]
    elif kind=='wrong-issue':row['uses'][0]['open_issues']=[]
    else:
        nodes['source']['role']='HEADER'
        row['source_evidence'][0].update(evidence=deepcopy(nodes['source']),node_sha256=digest(nodes['source']))
    with pytest.raises(ValueError):module._decision(row,record,intervals,text,nodes)
