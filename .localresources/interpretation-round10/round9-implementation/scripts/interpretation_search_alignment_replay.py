"""Replay frozen P8 evidence and prepare correspondence review packets; no model calls."""
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
import hashlib
import json
from legalmath.canonical import canonical, loads, digest
from legalmath.interpretation.search.alignment import review_packet
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.search.models import commitment

ROOT=Path(__file__).resolve().parents[1]
AT='2026-09-23T00:00:00.000000Z'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prose(value):
    return str(value).replace('|','\\|').replace('\n',' ')


def render(value):
    lines=['# Fact correspondence review','',
           'These are generated readings awaiting review. No semantic mapping is approved.',
           'This packet exposes model proposals and cannot serve as blind reference annotation.', '',
           'Source packet: `'+value['source_packet_hash']+'`', '']
    for side in ('left','right'):
        reading=value[side]
        lines+=['## '+side.capitalize()+' reading','',reading['statement'],'',
                'Distinction: '+reading['distinction'],'',
                '| Fact | Type | Declared meaning | Unit | Judgment required | Source units |',
                '|---|---|---|---|---|---|']
        for f in reading['formalization']['facts']:
            lines.append('| '+' | '.join(prose(f[k]) for k in ('name','type','meaning','unit','requires_judgment','source_unit_ids'))+' |')
        lines+=['','Scope: `'+reading['formalization']['scope']+'`',
                '', 'Result expression: `'+reading['formalization']['result']+'`','',
                'Assumptions:','',*['- '+x for x in reading['assumptions']],'',
                'Unresolved questions:','',*['- '+x for x in reading['questions']],'']
    lines+=['## Questions for the reviewer','',*['- '+x for x in value['review_questions']],'',
            'Record an explicit one-to-one mapping and the assumptions for each changed declaration. '
            'A different number or decomposition of facts may require a new interpretation rather than a mapping.','',
            '## Retained source','']
    for u in value['source_packet']['units']:
        lines += ['**'+u['unit_id']+' — '+u['locator']+'**','',u['text'],'']
    lines += ['Missing or supplied dependencies:','',
              '```json',json.dumps(value['source_packet']['dependencies'],indent=2),'```','']
    return '\n'.join(lines)


def main():
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    original=ROOT/'artifacts/interpretation/round2/P8/attempt-01'
    manifest=json.loads((original/'run-manifest.json').read_text())
    assert manifest['status']=='PASSED'
    allowance=ROOT/'artifacts/interpretation/round2/live-allowance.json';allowance_hash=sha(allowance)
    sources=[];conditional=None
    for ref in ('24EC50','23EC46'):
        source=original/'pilot'/ref
        for name in ('packet.json','investigation.json','report.json','history.zip'):
            assert sha(source/name)==manifest['artifact_sha256']['pilot/'+ref+'/'+name]
        packet=loads((source/'packet.json').read_bytes())
        record=loads((source/'investigation.json').read_bytes())
        state=record['records']['search-state'][0]
        nodes={n['node_id']:n for n in state['nodes']}
        directory=out/ref;directory.mkdir();reviews=directory/'review-packets';reviews.mkdir()
        checker=Comparisons(directory/'java',ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
        comparisons=[];index=[]
        for previous in state['comparisons']:
            left,right=[nodes[previous[k]]['reading'] for k in ('left_node_id','right_node_id')]
            current=checker.compare(left,right,packet)
            # This frozen population contains no literal-alias opportunities.
            # A semantic mismatch becoming unconditional equivalence is a defect.
            assert current['status']==previous['result']['status'],previous['pair']
            comparisons.append({'pair':previous['pair'],'left_node_id':previous['left_node_id'],
                                'right_node_id':previous['right_node_id'],
                                'old_status':previous['result']['status'],'current':current})
            if current['status']=='INCOMPARABLE_FACT_BINDINGS':
                value=review_packet(left,right,packet)
                value.update(run_id=state['run_id'],left_node_id=previous['left_node_id'],right_node_id=previous['right_node_id'],
                             search_state_hash=digest(state),report_hash=digest(record['records']['search-report'][0]))
                name='pair-'+str(len(index)+1).zfill(2)
                (reviews/(name+'.json')).write_bytes(canonical(value))
                (reviews/(name+'.md')).write_text(render(value))
                index.append({'packet':name+'.md','json':name+'.json','pair':previous['pair']})
        (reviews/'index.json').write_bytes(canonical(index))
        (reviews/'index.md').write_text('# Correspondence review: '+ref+'\n\n'
            +'All listed pairs remain incomparable without a new explicit assumption.\n\n'
            +'\n'.join('- ['+x['packet']+']('+x['packet']+') — '+' / '.join(x['pair']) for x in index)+'\n')
        if ref=='24EC50':
            # Fixed reviewed pair, never selected after seeing the result.
            left=nodes['node.8722fff61cac09f9526e4832']['reading']
            right=nodes['node.b67de3d0d9e2578b893f0d3b']['reading']
            proposal={'source_packet_hash':digest(packet),'left_commitment':commitment(left),'right_commitment':commitment(right),
                'links':[
                    {'left':'covered_submission','right':'covered_submission',
                     'assumption':'Hypothesis only: the same submission event and product classification populate both inputs, including the footnote and fee-payment exclusions.'},
                    {'left':'submission_date','right':'submission_date',
                     'assumption':'Hypothesis only: both inputs use the same submission event, timezone and dispatch-versus-receipt convention. The source does not settle that convention.'},
                    {'left':'submitted_via_eip','right':'submitted_via_e_ip',
                     'assumption':'Hypothesis only: both inputs record the same observed use of e-IP for that submission event.'}],
                'rationale':'Expose the encoded consequence of these proposed correspondences for independent review. No semantic equivalence is approved.',
                'output_meaning_assumption':'Hypothesis only: a true in-scope result in both rules means the selected e-IP route requirement is satisfied; neither result means whole-bank compliance.',
                'citations':[left['citations'][0]]}
            conditional=checker.compare_conditional(left,right,packet,proposal)
            assert conditional['status']=='CONDITIONAL_ANALYSIS' and conditional['review_required']
            assert not conditional['release_eligible']
            (directory/'hypothetical-correspondence.json').write_bytes(canonical(proposal))
            (directory/'conditional-analysis.json').write_bytes(canonical(conditional))
        result={'circular':ref,'source_packet_hash':digest(packet),'comparisons':comparisons,
                'status_counts':dict(Counter(c['current']['status'] for c in comparisons)),
                'mismatch_review_packets':len(index),'legal_accuracy_evaluated':False}
        (directory/'result.json').write_bytes(canonical(result))
        for name in ('packet.json','investigation.json','report.json','history.zip'):
            assert sha(source/name)==manifest['artifact_sha256']['pilot/'+ref+'/'+name]
        sources.append({k:v for k,v in result.items() if k!='comparisons'}|{'comparisons':len(comparisons)})
    assert sha(allowance)==allowance_hash
    result={'passed':True,'sources':sources,'model_calls':0,'allowance_sha256_unchanged':allowance_hash,
            'prior_histories_modified':False,'extra_automatic_matches':0,
            'hypothetical_24ec50_result':conditional['encoded_comparison']['status'],
            'hypothetical_status':conditional['status'],'human_mapping_reviews':0,
            'legal_accuracy_evaluated':False,'release_authorized':False}
    (out/'result.json').write_bytes(canonical(result));print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
