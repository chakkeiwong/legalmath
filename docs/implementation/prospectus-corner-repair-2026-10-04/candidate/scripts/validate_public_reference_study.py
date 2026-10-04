"""Actual Java/Python reference replay, mutation provenance and allowance admission."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.interpretation.assurance.evaluation import load_frozen,source_packet,admit
from legalmath.interpretation.search.formal import bundle,Comparisons,project

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'.localresources/interpretation-round5/public-qa-v1'


def main(out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round5'):
        raise ValueError('Use a new round5 output directory')
    out.mkdir(parents=True)
    manifest=loads((SOURCE/'manifest.json').read_bytes())
    for name,expected in manifest['files'].items():
        path=(SOURCE/name).resolve()
        if not path.is_relative_to(SOURCE) or raw_digest(path.read_bytes())!=expected:raise ValueError('Changed source/reference file')
    study=load_frozen(SOURCE/'frozen');assert digest(study)==manifest['study_hash']
    provenance={p['case_id']:p for p in loads((SOURCE/'provenance.json').read_bytes())}
    rows=[]
    jdk=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    for c in study['cases']:
        original=(SOURCE/(c['family_id'][4:-3]+'.html')).read_bytes()
        p=provenance[c['case_id']];case_raw=bytes.fromhex(c['roots'][0]['raw_hex'])
        assert raw_digest(original)==p['original_source_sha256']
        if p['mutation']:
            edit=p['mutation'];assert original.count(edit['before'].encode())==edit['occurrences']==1
            assert case_raw==original.replace(edit['before'].encode(),edit['after'].encode())
            assert c['reference']['basis']=='SEEDED_TRANSFORMATION' and not p['official_bytes_unchanged']
        else:assert case_raw==original and p['official_bytes_unchanged']
        packet=source_packet(c);reference=c['reference'];r=reference['binding_reading']
        checker=Comparisons(out/c['case_id'],jdk,c['at']);compiled=bundle(r,packet,c['at'])
        actual=[project(checker.replay([compiled],s)[0]['java']) for s in reference['snapshots']]
        assert actual==reference['accepted'][0]
        mutants=[]
        if c['variant']=='CLEAN':
            formulas=(['(or regulated business hong_kong)','(and regulated hong_kong)']
                if 'family-offices' in c['case_id'] else
                ['(and ra13_context scheme_money in_hong_kong (not transfer_agent))','(and ra13_context scheme_money)'])
            for index,expression in enumerate(formulas):
                bad=deepcopy(r);bad['formalization']['result']=expression
                b=bundle(bad,packet,c['at'])
                values=[project(checker.replay([b],s)[0]['java']) for s in reference['snapshots']]
                witnesses=[i for i,(a,v) in enumerate(zip(actual,values)) if a!=v]
                assert witnesses,'Adverse rule survived every reference scenario'
                mutants.append({'expression':expression,'witness_indices':witnesses,'actual_java':values})
        rows.append({'case_id':c['case_id'],'packet_hash':c['packet_hash'],'reference_program_hash':digest(compiled),
            'expected':reference['accepted'][0],'actual_java':actual,'mutants':mutants,
            'meaning':'Reference-program consistency and tested mutation detection; English interpretation remains proposed'})
    ledger=loads((ROOT/'artifacts/interpretation/round2/live-allowance.json').read_bytes())
    admission=admit(study,ledger['maximum']-len(ledger['calls']))
    assert admission['status']=='UNDER_BUDGETED'
    summary={'engineering_status':'PASS','case_count':len(rows),'reference_scenarios':sum(len(r['actual_java']) for r in rows),
        'mutants_detected':sum(len(r['mutants']) for r in rows),'families':len(study['families']),
        'unlabelled_qualification_families':2,'new_live_calls':0,'live_study_admission':admission,
        'legal_accuracy_evaluated':False,'method_ranking_established':False,'reference_semantics_independently_verified':False}
    (out/'reference-replays.json').write_bytes(canonical(rows));(out/'summary.json').write_bytes(canonical(summary))
    print(canonical(summary).decode())


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);main(parser.parse_args().out)
