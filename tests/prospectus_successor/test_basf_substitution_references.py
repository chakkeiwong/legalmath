from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest
from legalmath.prospectus.successor import basf_substitution_references as core
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.reviewed_references import admit

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/'docs/implementation/prospectus-execution-authority'


@pytest.fixture(scope='module')
def original():
    p=json.loads(gzip.decompress((AUTH/'attempts/basf-meanings/attempt-019/installed-construct/products.json.gz').read_bytes()))
    packet=json.loads((AUTH/'reviews/substitution-references-277/packet.json').read_text())
    spec=core.specification()
    ids={r['source']['unit'] for r in spec['references']}
    ids|={t['source']['unit'] for r in spec['references'] for t in r['targets']}
    ids|={r['unit'] for r in spec['contexts']}
    for name in ('basf_call_references_spec.json','basf_payment_references_spec.json','basf_legacy_references_spec.json','basf_governance_references_spec.json','basf_default_references_spec.json'):
        other=json.loads((ROOT/'src/legalmath/prospectus/successor'/name).read_text())
        ids|={r['source']['unit'] for r in other['references']}
        ids|={r['unit'] for r in other.get('contexts',[])+other.get('split_contexts',[])}
    graph=p['P1']['payload']['graph']
    ids.add(next(u['id'] for u in graph['units'] if u['document']=='basf-2032-final'))
    financial = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_financial_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in financial['references']}
    ids |= {r['unit'] for r in financial['contexts']}
    internal = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_internal_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in internal['references']}
    ids |= {r['unit'] for r in internal['contexts']}
    substitution = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_substitution_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in substitution['references']}
    ids |= {r['unit'] for r in substitution['contexts']}
    substitution = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_substitution_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in substitution['references']}
    ids |= {r['unit'] for r in substitution['contexts']}
    raw_ids = ids | {m['source']['unit'] for u in p['P2']['payload']['assembly']['units']
                     if u['unit'] in ids for m in (u.get('character_map') or [])}
    graph={**graph,'units':[u for u in graph['units'] if u['id'] in raw_ids],
        'references':[r for r in graph['references'] if r['unit'] in ids]}
    assembly=p['P2']['payload']['assembly']
    assembly={**assembly,'units':[u for u in assembly['units'] if u['unit'] in ids]}
    packet['assembly_sha256']=digest(assembly)
    return graph,assembly,packet


def test_complete_substitution_and_amendment_targets(original):
    graph,assembly,packet=original
    deps,edges=admit(graph,assembly,packet)
    assert [len(d['targets']) for d in deps]==[22,110] and len(edges)==132
    assert [d['status'] for d in deps]==['RESOLVED','UNRESOLVED']
    assert len(deps[1]['unknown_target_uses'])==13
    assert 'Negativverpflichtung' in ' '.join(t['source']['quote'] for t in deps[0]['targets'])
    assert '72 Stunden' in ' '.join(t['source']['quote'] for t in deps[1]['targets'])
    assert core.check(graph,assembly,packet)['actual_substitution_compliance']=='UNKNOWN'


@pytest.mark.parametrize('mutation',['omit-d','opening-only','omit-procedure','swap','extend','rename','question','edition','duplicate','promote-role'])
def test_incomplete_or_wrong_substitution_target_refused(original,mutation):
    graph,assembly,packet=deepcopy(original)
    row=packet['references'][0]
    if mutation=='omit-d':row['targets']=row['targets'][:11]
    elif mutation=='opening-only':packet['references'][1]['targets']=packet['references'][1]['targets'][:9]
    elif mutation=='omit-procedure':packet['references'][1]['targets']=packet['references'][1]['targets'][:-7]
    elif mutation=='swap':row['targets']=packet['references'][1]['targets']
    elif mutation=='extend':row['targets'].append(deepcopy(packet['references'][1]['targets'][0]))
    elif mutation=='rename':row['id']='hidden'
    elif mutation=='question':row['questions']=['Q1']
    elif mutation=='edition':row['source']['source_sha256']='0'*64
    elif mutation=='promote-role':
        next(u for u in assembly['units'] if u['unit'].endswith(':p130:l2'))['role']='OPERATIVE'
        packet['assembly_sha256']=digest(assembly)
    else:packet['references'].append(deepcopy(row))
    with pytest.raises(ValueError,match='BASF substitution'):admit(graph,assembly,packet)


def test_missing_and_hidden_uncertainty(original):
    graph,assembly,packet=original
    packet={**packet,'references':[]}
    deps=core.missing_dependencies(core.check(graph,assembly,packet))
    missing=[d['id'] for d in deps]
    semantic={'dependencies':deps,'questions':{q:{'unresolved':missing.copy(),
        'subquestions':{'a':{'unresolved':missing.copy()}}} for q in ('Q1','Q2')}}
    core.verify_consumed(graph,assembly,{'reference_admission':packet},semantic)
    semantic['questions']['Q2']['subquestions']['a']['unresolved'].pop()
    with pytest.raises(ValueError,match='hides or invents'):
        core.verify_consumed(graph,assembly,{'reference_admission':packet},semantic)
