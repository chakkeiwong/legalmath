"""Replay every frozen live comparison under the reviewed Boolean-domain repair.

No model calls. Original reports remain unchanged. The previously missed
direct/contextual link comparison must acquire a replayed distinguishing witness.
"""
from argparse import ArgumentParser
from collections import Counter
import json
from pathlib import Path
from legalmath.canonical import canonical,loads,digest,raw_digest
from legalmath.interpretation.search.formal import Comparisons

ROOT=Path(__file__).resolve().parents[1]
AT='2026-09-23T00:00:00.000000Z'


def main():
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out)
    if out.exists():raise ValueError('Use a fresh evidence directory')
    out.mkdir(parents=True);sources=[];found=False
    for ref in ('24EC50','23EC46'):
        original=ROOT/'artifacts/interpretation/round2/P5/attempt-05/pilot'/ref
        raw=(original/'investigation.json').read_bytes();record=loads(raw)
        # Supervisor manifests contain measured fractional wall times. They use
        # standard JSON, unlike canonical RuleIR/evidence payloads (no floats).
        manifest=json.loads((original.parent.parent/'run-manifest.json').read_bytes())
        assert manifest['status']=='PASSED'
        for name in ('investigation.json','packet.json'):
            assert raw_digest((original/name).read_bytes())==manifest['artifact_sha256']['pilot/'+ref+'/'+name]
        packet=loads((original/'packet.json').read_bytes());state=record['records']['search-state'][0]
        nodes={n['node_id']:n for n in state['nodes']};results=[]
        checker=Comparisons(out/ref/'java',ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
        for previous in state['comparisons']:
            pair=[nodes[previous[k]] for k in ('left_node_id','right_node_id')]
            current=checker.compare(*(n['reading'] for n in pair),packet)
            results.append({'pair':previous['pair'],'old_status':previous['result']['status'],
                            'current':current})
            f=pair[0]['reading']['formalization']
            if (ref=='23EC46' and any(v['name']=='contextual_product_nexus' for v in f['facts'])
                    and previous['result']['status']=='NO_DIFFERENCE_IN_FINITE_PROBES'):
                assert current['status']=='DIFFERENT' and len(current['replays'])==2
                found=True
        result={'circular':ref,'original_investigation_sha256':raw_digest(raw),
                'source_packet_hash':digest(packet),'comparisons':results,
                'status_counts':dict(Counter(r['current']['status'] for r in results)),
                'legal_accuracy_evaluated':False}
        (out/(ref+'.json')).write_bytes(canonical(result))
        assert (original/'investigation.json').read_bytes()==raw
        sources.append({'circular':ref,'comparisons':len(results),'status_counts':result['status_counts']})
    assert found,'The observed missed live pair was not repaired'
    result={'passed':True,'observed_missed_witness_repaired':found,'sources':sources,
            'model_calls':0,'old_histories_modified':False,'legal_accuracy_evaluated':False}
    (out/'result.json').write_bytes(canonical(result));print(result)


if __name__=='__main__':main()
