"""Freeze complete source decisions before the referent candidate exists."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import time
from scripts import prospectus_definition_context as prior
from scripts import prospectus_definition_referent_oracle as oracle

ROOT,AUTH=prior.ROOT,prior.AUTH
PREP=AUTH/'reviews/definition-referents-333'
PLAN='docs/plans/prospectus-definition-referents-2026-10-19.md'
ORACLE='scripts/prospectus_definition_referent_oracle.py'
METHOD='scripts/prospectus_definition_referent_cases.py'

def main():
    assert not PREP.exists(),'Preserve prior preparation evidence'
    assert not (ROOT/'src/legalmath/prospectus/successor/definition_referents.py').exists()
    start=time.monotonic();PREP.mkdir()
    prior.save(PREP/'cases-started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_referent_cases'],
        'started_at':datetime.now(timezone.utc).isoformat()})
    try:
        for n,v in prior.read(prior.HERE/'outputs.json').items():assert prior.sha(prior.HERE/n)==v
        products,_=prior.baseline();ordinary=prior.read(prior.HERE/'ordinary-answer.json.gz')
        source=prior.read(AUTH/'attempts/basf-references/attempt-026/definition-dossier.json')
        text=(AUTH/'attempts/basf-references/attempt-026/selected-text.txt').read_text()
        report=ordinary['definition_sources'];original={r['id']:r for r in source['records']}
        nodes={n['id']:n for n in products['P3']['payload']['clauses']['nodes']}
        decisions=[]
        for record in report['records']:
            key=record['id'].split('-')[0]
            if key not in oracle.STARTS:continue
            raw=original[record['id']]
            assert [u['start'] for u in raw['uses']]==oracle.STARTS[key]
            declarations=[deepcopy(report['intervals'][i]) for i in record['declarations']]
            assert [{k:d[k] for k in ('start','end','quote')} for d in declarations]==raw['declarations']
            node_id,field=oracle.LINKS[key];node=nodes[node_id]
            assert node['role']=='OPERATIVE' and node[field]['qualification']
            row={'record':record['id'],'declarations':declarations,
                'meaning':{'node':node_id,'node_sha256':oracle.digest(node),'field':field,
                    'reading':deepcopy(node[field]),'quote':node['quote'],'spans':deepcopy(node['spans'])},
                'support':[{'start':a,'end':b,'quote':text[a:b]} for a,b in oracle.SUPPORT[key]],'uses':[]}
            for u,raw_use in zip(record['uses'],raw['uses']):
                item=report['intervals'][u['interval']];a,b=item['start'],item['end']
                assert (a,b,item['quote'])==(raw_use['start'],raw_use['end'],raw_use['quote'])
                assert text[a:b]==item['quote']
                left,right=max(0,a-180),min(len(text),b+220)
                row['uses'].append({**deepcopy(item),'interval':u['interval'],
                    'context':{'start':left,'end':right,'quote':text[left:right]},
                    **oracle.decision(key,a,item['quote'])})
            assert len(row['uses'])==len(raw['uses']);decisions.append(row)
        assert len(decisions)==3 and sum(len(r['uses']) for r in decisions)==276
        content=oracle.expected_content(ordinary,decisions)
        counts=dict(Counter(u['kind'] for r in decisions for u in r['uses']))
        assert counts=={'HEADING_MENTION':10,'BOUND_REFERENT':260,'GENERIC_SECURITY_CLASS':1,
            'CONDITIONAL_REFERENT':2,'NAME_COMPONENT':2,'OTHER_CREDITORS':1},counts
        assert sum(u['disposition']=='UNRECONCILED' for u in content['uses'])==231
        prior.save(PREP/'source-decisions.json',decisions);prior.save(PREP/'expected-content.json',content)
        prior.save(PREP/'cases-freeze.json',{'created_at':datetime.now(timezone.utc).isoformat(),
            'candidate_absent':True,'source_decisions_sha256':prior.sha(PREP/'source-decisions.json'),
            'expected_file_sha256':prior.sha(PREP/'expected-content.json'),
            'expected_content_sha256':oracle.digest(content),'products_sha256':oracle.digest(products),
            'ordinary_answer_sha256':oracle.digest(ordinary),'source_text_sha256':oracle.digest(text.encode()),
            'oracle_sha256':prior.sha(ROOT/ORACLE),'method_sha256':prior.sha(ROOT/METHOD),'plan_sha256':prior.sha(ROOT/PLAN)})
        result={'status':'PASS','records':3,'associations':276,'decisions':counts,'wall_seconds':time.monotonic()-start}
        prior.save(PREP/'case-preparation.json',result);print(result)
    except BaseException as e:
        prior.save(PREP/'case-failure.json',{'type':type(e).__name__,'message':str(e),'wall_seconds':time.monotonic()-start});raise

if __name__=='__main__':main()
