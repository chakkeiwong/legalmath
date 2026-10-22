"""Freeze source identities and complete expectations before candidate creation."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import signal
import time
from scripts import prospectus_definition_referent as prior
from scripts import prospectus_definition_remainder_oracle as oracle

ROOT,AUTH=prior.ROOT,prior.AUTH
PREP=AUTH/'reviews/definition-remainders-334'
PLAN='docs/plans/prospectus-definition-remainders-2026-10-19.md'
ORACLE='scripts/prospectus_definition_remainder_oracle.py'
METHOD='scripts/prospectus_definition_remainder_cases.py'

def main():
    assert not PREP.exists(),'Preserve prior preparation evidence'
    assert not (ROOT/'src/legalmath/prospectus/successor/definition_remainders.py').exists()
    start=time.monotonic();PREP.mkdir()
    prior.save(PREP/'cases-started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_remainder_cases'],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':90})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Case preparation bound')))
    signal.alarm(90)
    try:
        for n,v in prior.read(prior.HERE/'outputs.json').items():assert prior.sha(prior.HERE/n)==v,n
        products,_=prior.baseline();ordinary=prior.read(prior.HERE/'ordinary-answer.json.gz')
        source=prior.read(AUTH/'attempts/basf-references/attempt-026/definition-dossier.json')
        text=(AUTH/'attempts/basf-references/attempt-026/selected-text.txt').read_text()
        assert text==products['P2']['payload']['assembly']['continuous_text']
        report=ordinary['definition_sources'];original={r['id']:r for r in source['records']}
        nodes={n['id']:n for n in products['P3']['payload']['clauses']['nodes']}
        assert len(nodes)==len(products['P3']['payload']['clauses']['nodes'])
        decisions=[]
        for record in report['records']:
            key=record['id'].split('-')[0]
            if key not in oracle.PAIRS:continue
            raw=original[record['id']]
            assert [(u['start'],u['end']) for u in raw['uses']]==oracle.PAIRS[key],key
            declarations=[deepcopy(report['intervals'][i]) for i in record['declarations']]
            assert [{k:d[k] for k in ('start','end','quote')} for d in declarations]==raw['declarations']
            evidence=[]
            for node_id in oracle.P3[key]:
                node=nodes[node_id]
                assert node['role']=='OPERATIVE' and node['spans'] and node['quote']
                assert any(k.endswith('_reading') and v for k,v in node.items())
                evidence.append({'node':node_id,'node_sha256':oracle.digest(node),'evidence':deepcopy(node)})
            row={'record':record['id'],'declarations':declarations,
                'reading':oracle.READINGS[key][0],'open_issues':deepcopy(oracle.READINGS[key][1]),
                'source_evidence':evidence,
                'support':[{'start':a,'end':b,'quote':text[a:b]} for a,b in oracle.SUPPORT.get(key,[])],'uses':[]}
            for use,raw_use in zip(record['uses'],raw['uses']):
                item=report['intervals'][use['interval']];a,b=item['start'],item['end']
                assert (a,b,item['quote'])==(raw_use['start'],raw_use['end'],raw_use['quote'])
                assert text[a:b]==item['quote']
                left,right=max(0,a-180),min(len(text),b+220)
                row['uses'].append({**deepcopy(item),'interval':use['interval'],
                    'context':{'start':left,'end':right,'quote':text[left:right]},**oracle.decision(key,a,b)})
            assert len(row['uses'])==len(raw['uses']);decisions.append(row)
        assert len(decisions)==44 and sum(len(r['uses']) for r in decisions)==231
        content=oracle.expected_content(ordinary,decisions)
        assert len(content['uses'])==612 and len(content['records'])==62
        assert not any(u['disposition']=='UNRECONCILED' for u in content['uses'])
        counts=dict(Counter(u['kind'] for r in decisions for u in r['uses']))
        agent=next(r for r in decisions if r['record'].startswith('U10-'))
        initial=agent['source_evidence'][0]['evidence']
        assert initial['agent_reading']['final_term_calculation_agent']=='NatWest Markets N.V.'
        assert any('NatWest Markets N.V.' in s['quote'] for s in initial['selection_authority'])
        prior.save(PREP/'source-decisions.json',decisions);prior.save(PREP/'expected-content.json',content)
        prior.save(PREP/'cases-freeze.json',{'created_at':datetime.now(timezone.utc).isoformat(),
            'candidate_absent':True,'source_decisions_sha256':prior.sha(PREP/'source-decisions.json'),
            'expected_file_sha256':prior.sha(PREP/'expected-content.json'),
            'expected_content_sha256':oracle.digest(content),'products_sha256':oracle.digest(products),
            'ordinary_answer_sha256':oracle.digest(ordinary),'source_text_sha256':oracle.digest(text.encode()),
            'oracle_sha256':prior.sha(ROOT/ORACLE),'method_sha256':prior.sha(ROOT/METHOD),'plan_sha256':prior.sha(ROOT/PLAN)})
        result={'status':'PASS','records':44,'associations':231,'decisions':counts,'wall_seconds':time.monotonic()-start}
        prior.save(PREP/'case-preparation.json',result);print(result)
    except BaseException as error:
        prior.save(PREP/'case-failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
