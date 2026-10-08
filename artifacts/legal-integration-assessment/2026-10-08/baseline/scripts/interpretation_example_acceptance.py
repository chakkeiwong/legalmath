"""Retained real FAQ evidence and explicit conditional analogy to 23EC46."""
from argparse import ArgumentParser
from pathlib import Path
from legalmath.canonical import canonical,loads,raw_digest
from legalmath.interpretation.assurance.authorities import AuthorityCatalog
from legalmath.interpretation.assurance.examples import ExampleRegistry
ROOT=Path(__file__).resolve().parents[1]


def main(out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round4'):
        raise ValueError('Use a new round4 output directory')
    out.mkdir(parents=True)
    c=AuthorityCatalog.load(ROOT/'.localresources/sfc-authorities/b1/catalog.json')
    registry=ExampleRegistry.load(ROOT/'.localresources/sfc-examples/b3/registry.json',c)
    scope={'issuer':'Securities and Futures Commission','jurisdiction':'Hong Kong',
           'issue_ids':['paragraph.3.11.applicability']}
    p=ROOT/'artifacts/interpretation/round3/A7/attempt-08/pilot/23EC46'
    packet=loads((p/'packet.json').read_bytes());candidates=loads((p/'candidates.json').read_bytes())
    unit=next(u for u in packet['units'] if 'certain types of funds or funds offered by certain fund houses' in u['text'])
    queries={'queries':[{'candidate_id':cid,'issue_id':scope['issue_ids'][0],
        'factors':['gift.linked',branch+'.link'],'outcome':{'atom':'paragraph.3.11.applies','negative':False},
        'evidence':[{'unit_id':unit['unit_id'],'quote':unit['text']}]} for cid in candidates for branch in ('fund.type','fund.house')],
        'questions':['These target-factor assignments were proposed by the developer from the retained paragraph, not independently adjudicated.']}
    result=registry.reason(registry.retrieve(scope,'2023-11-30T00:00:00.000000Z'),queries,packet,candidates)
    assert result['moves'] and {m['temporal_status'] for m in result['moves']}=={'UNKNOWN_VERSION'}
    assert all(m['status']=='CONDITIONAL_PROPOSED_ANALOGY' for m in result['moves'])
    assert result['status']=='UNRESOLVED' and not result['release_eligible']
    assert {m['operator'] for m in result['moves']}=={'ANALOGISE','DISTINGUISH'}
    (out/'reasoning.json').write_bytes(canonical(result))
    (out/'faq-original.html').write_bytes(c.documents['faq.2010']['data'])
    (out/'registry.json').write_bytes(canonical(registry.value))
    (out/'summary.json').write_bytes(canonical({'status':'PASS_WITH_APPLICABILITY_QUESTIONS',
        'real_official_example_branches':2,'independent_source_families':1,'real_court_cases':0,
        'retained_candidate_count':len(candidates),'conditional_moves':len(result['moves']),
        'unresolved_questions':len(result['questions']),'new_live_calls':0,'legal_accuracy_evaluated':False}))
    (out/'manifest.json').write_bytes(canonical({'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
        for p in sorted(out.iterdir()) if p.is_file()}}))
    print('B3 PASS: real official FAQ example linked to retained 23EC46; version and materiality remain unresolved.')


if __name__=='__main__':
    p=ArgumentParser(description=__doc__);p.add_argument('--out',required=True);main(p.parse_args().out)
