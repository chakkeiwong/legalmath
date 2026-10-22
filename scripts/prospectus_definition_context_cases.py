"""Freeze independently enumerated source decisions before context candidate."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import time
from scripts import prospectus_definition_binding as prior
from scripts import prospectus_definition_context_oracle as oracle

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/definition-contexts-332'
PLAN = 'docs/plans/prospectus-definition-contexts-2026-10-19.md'
ORACLE = 'scripts/prospectus_definition_context_oracle.py'
METHOD = 'scripts/prospectus_definition_context_cases.py'


def main():
    assert not PREP.exists(), 'Exclusive preparation; preserve any failed cases'
    assert not (ROOT / 'src/legalmath/prospectus/successor/definition_contexts.py').exists()
    start = time.monotonic()
    PREP.mkdir()
    prior.save(PREP / 'cases-started.json', {'command':['.venv/bin/python','-m','scripts.prospectus_definition_context_cases'],
        'started_at':datetime.now(timezone.utc).isoformat()})
    try:
        for n,v in prior.read(prior.HERE / 'outputs.json').items():
            assert prior.sha(prior.HERE/n) == v
        products, _ = prior.baseline()
        ordinary = prior.read(prior.HERE/'ordinary-answer.json.gz')
        source = prior.read(AUTH/'attempts/basf-references/attempt-026/definition-dossier.json')
        text = (AUTH/'attempts/basf-references/attempt-026/selected-text.txt').read_text()
        report = ordinary['definition_sources']
        nodes = {n['id']:n for n in products['P3']['payload']['clauses']['nodes']}
        original = {r['id']:r for r in source['records']}
        def meaning(node_id, field):
            node = nodes[node_id]
            assert node['role'] == 'OPERATIVE' and node['spans']
            return {'node':node_id,'node_sha256':oracle.digest(node),'field':field,
                'reading':deepcopy(node[field]),'quote':node['quote'],'spans':deepcopy(node['spans'])}
        decisions = []
        for record in report['records']:
            key = record['id'].split('-')[0]
            if key not in oracle.STARTS: continue
            raw = original[record['id']]
            assert [u['start'] for u in raw['uses']] == oracle.STARTS[key]
            assert [report['intervals'][i] for i in record['declarations']] == [
                {**d,'source_piece_indices':report['intervals'][i]['source_piece_indices']}
                for d,i in zip(raw['declarations'],record['declarations'])]
            node,field,concept = oracle.LINKS[key]
            row = {'record':record['id'],'concept':concept,'reason':oracle.REASONS[key],
                'declarations':[deepcopy(report['intervals'][i]) for i in record['declarations']],
                'meaning':meaning(node,field),'extra_meanings':[], 'uses':[]}
            if key in ('D05','D06'):
                row['extra_meanings'].append(meaning('basf-global:exchange-certification','global_reading'))
            for u, raw_use in zip(record['uses'],raw['uses']):
                item = report['intervals'][u['interval']]
                a,b=item['start'],item['end']
                assert (a,b,item['quote']) == (raw_use['start'],raw_use['end'],raw_use['quote'])
                assert text[a:b] == item['quote']
                kind = 'HEADING_MENTION' if key=='D07' and a in (2601,42983) else (
                    'NAME_COMPONENT' if key=='D09' and a==2880 else 'BOUND_CONTEXTUALLY')
                number = ('EACH_OR_RELEVANT_ICSD' if a in (3000,3453,3693,3862) else 'BOTH_ICSDS') if key=='D10' else None
                left,right=max(0,a-120),min(len(text),b+160)
                row['uses'].append({'interval':u['interval'],'start':a,'end':b,'quote':item['quote'],
                    'source_piece_indices':deepcopy(item['source_piece_indices']),
                    'context':{'start':left,'end':right,'quote':text[left:right]},'kind':kind,'number':number})
            decisions.append(row)
        assert len(decisions)==10 and sum(len(r['uses']) for r in decisions)==75
        content = oracle.expected_content(ordinary,decisions)
        assert sum(u['disposition']=='BOUND_CONTEXTUALLY' for u in content['uses'])==72
        prior.save(PREP/'source-decisions.json',decisions)
        prior.save(PREP/'expected-content.json',content)
        prior.save(PREP/'cases-freeze.json',{'created_at':datetime.now(timezone.utc).isoformat(),
            'candidate_absent':True, 'source_decisions_sha256':prior.sha(PREP/'source-decisions.json'),
            'expected_file_sha256':prior.sha(PREP/'expected-content.json'),
            'expected_content_sha256':oracle.digest(content),'products_sha256':oracle.digest(products),
            'ordinary_answer_sha256':oracle.digest(ordinary), 'source_text_sha256':oracle.digest(text.encode()),
            'oracle_sha256':prior.sha(ROOT/ORACLE),'method_sha256':prior.sha(ROOT/METHOD),
            'plan_sha256':prior.sha(ROOT/PLAN)})
        result={'status':'PASS','records':10,'associations':75,'context_bindings':72,
            'heading_mentions':2,'name_components':1,'wall_seconds':time.monotonic()-start}
        prior.save(PREP/'case-preparation.json',result)
        print(json.dumps(result))
    except BaseException as error:
        prior.save(PREP/'case-failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start})
        raise


if __name__=='__main__':
    main()
