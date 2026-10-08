"""B2a actual Java vectors and preserved uncertainty on retained 23EC46 readings."""
from argparse import ArgumentParser
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.interpretation.assurance.composition import compose,execute
from tests.assurance.test_composition import fixture,AT


def main(out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round4'):
        raise ValueError('Use a new round4 output directory')
    out.mkdir(parents=True);jdk=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    p,claims,candidates,matrix,spec=fixture()
    synthetic=compose(spec,p,claims,candidates,matrix,AT,jdk=jdk,out=out/'controlled-vector')
    assert len(synthetic['combinations'])==2
    assert all(c['status']=='JAVA_VECTOR_CONFORMANCE' for c in synthetic['combinations'])
    source=ROOT/'artifacts/interpretation/round3/A7/attempt-08/pilot/23EC46'
    p=loads((source/'packet.json').read_bytes());claims=loads((source/'claims.json').read_bytes())
    candidates=loads((source/'candidates.json').read_bytes())
    spec={'version':'composition.v1','source_packet_hash':digest(p),'claims_hash':digest(claims),
        'candidates_hash':digest(candidates),'components':[{'component_id':'gift',
            'question':p['selected_slice'],'claim_ids':[c['claim_id'] for c in claims if c['relevance']!='CONTEXT'],
            'candidate_ids':sorted(candidates),'output_meaning':'TRUE_IS_PROHIBITED',
            'assignment_basis':'Retained selected gift-control alternatives; no claim that each covers all source requirements'}],
        'excluded_candidates':[],'max_combinations':16}
    specpath=out/'23ec46-spec.json';specpath.write_bytes(canonical(spec))
    actual=execute(SimpleNamespace(investigation=source,spec=specpath,jdk=jdk,out=out/'23ec46'))
    assert actual['status']=='INCOMPLETE' and not actual['release_eligible']
    assert actual['upstream_findings'] and actual['additional_source_concerns']
    assert len(actual['combinations'])==len(candidates)
    assert all(c['status']=='JAVA_VECTOR_CONFORMANCE' for c in actual['combinations'])
    summary={'status':'PASS_WITH_UNRESOLVED_INTERPRETATIONS','new_live_calls':0,
        'controlled_vector_combinations':2,'retained_23ec46_combinations':len(candidates),
        'java_builds_verified':2+len(candidates),'whole_circular_coverage_proved':False,
        'grouping_authority':'DEVELOPER_DECLARED; no new model grouping or legal acceptance'}
    (out/'summary.json').write_bytes(canonical(summary))
    (out/'manifest.json').write_bytes(canonical({'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
        for p in sorted(out.rglob('*')) if p.is_file()}}))
    print(summary)


if __name__=='__main__':
    p=ArgumentParser(description=__doc__);p.add_argument('--out',required=True);main(p.parse_args().out)
