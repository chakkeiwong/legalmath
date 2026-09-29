"""Execute specific limitations of the unchanged round-14 child rules."""
from pathlib import Path
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from resolution_support import AT, JDK, read, save, sha
from legalmath.canonical import digest
from legalmath.ir.evaluate import evaluate
from legalmath.java.manifest import build_candidate, verify_candidate
from assurance_round15_checks import diverse_backends

SOURCE = ROOT/'artifacts/interpretation/round14/live-reviewed/repairs.json'
OUT = ROOT/'artifacts/interpretation/round15/child-witnesses'
SPEC = {
    'r2_contact': ('2026-01-29T04:00:00.000000Z', 'direct_contact_made'),
    'reading_4_trigger': ('2026-01-29T04:00:00.000000Z', 'intends_xml_submission'),
    'reading_3_trigger': ('2026-02-02T02:00:00.000000Z', 'submitted_following_implementation'),
}


def fixtures(child):
    bundle=child['bundle'];ident=child['id'];historical,condition=SPEC[ident]
    rows=[]
    for label,when,false_fact,expected in (
        ('positive',AT,None,'TRUE'),
        ('historical',historical,None,'ERROR'),
        ('condition_false',AT,condition,'FALSE'),
    ):
        facts={f['name']:{'type':f['type'],'status':'known','value':f['name']!=false_fact,
            'evidence_ids':['child-witness.'+ident+'.'+label],
            'valid_from':historical,'valid_until':None,'recorded_at':historical}
            for f in bundle['facts']}
        rows.append({'id':ident+'.'+label,'bundle':bundle,
                     'snapshot':{'subject_id':'str.witness','facts':facts},
                     'rule_id':'selected.control','valid_at':when,'known_at':AT,
                     'expected':{'status':expected}})
    return rows


def world_pairs():
    return [
        {'child_id':'r2_contact','assessment':'2026-01-29T12:00:00+08:00',
         'world_a':{'str_id':'S','contact_time':'2026-01-29T11:00:00+08:00'},
         'world_b':{'str_id':'S','contact_time':'2026-01-29T13:00:00+08:00'},
         'shared_input':{'licensed_firm':True,'during_blackout':True,
                         'requires_urgent_submission':True,'direct_contact_made':True},
         'missing_distinction':'Contact by the assessed instant versus later contact during the same blackout',
         'projection_basis':'The current direct_contact_made fact states contact during the blackout, without a by-assessment predicate.',
         'required_repair':'A separately reviewed event/time adapter must bind contact to the assessed STR and cutoff; do not invent timeliness requirements.',
         'legal_answer_established':False},
        {'child_id':'reading_4_trigger',
         'world_a':{'schema_followed':True,'liaison_arranged':True},
         'world_b':{'schema_followed':False,'liaison_arranged':False},
         'shared_input':{'is_licensed_firm':True,'intends_xml_submission':True},
         'missing_distinction':'Trigger satisfaction versus schema and liaison performance',
         'projection_basis':'Both worlds satisfy the same actor/intention conjunction; neither performance fact is a child input.',
         'required_repair':'Keep the performance child unresolved until the schema/version and liaison evidence criteria are supported.',
         'legal_answer_established':False},
        {'child_id':'reading_3_trigger',
         'world_a':{'original_str_id':'S','linked_resubmission':'R'},
         'world_b':{'original_str_id':'S','linked_resubmission':None},
         'shared_input':{'is_licensed_firm':True,'submitted_off_channel':True,
                         'submitted_following_implementation':True},
         'missing_distinction':'A triggering original submission versus performance of a linked resubmission',
         'projection_basis':'The child observes the original event only. Both worlds have the same original event.',
         'required_repair':'Retain the original event and establish performance/linkage criteria separately; do not infer a deadline.',
         'legal_answer_established':False},
    ]


def run():
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'result.json').exists():
        raise RuntimeError('Witness result already exists; preserve it and review a new attempt explicitly')
    began=time.monotonic();source_hash=sha(SOURCE);children=[]
    for parent in read(SOURCE):
        for child in parent['record']['encodings']:
            if child.get('bundle'):children.append((parent,child))
    assert {c['id'] for _,c in children}==set(SPEC)
    cases={c['id']:fixtures(c) for _,c in children}
    save(OUT/'reference-lock.json',{'source_sha256':source_hash,'script_sha256':sha(Path(__file__)),
        'cases':cases,'world_pairs':world_pairs(),
        'reference_basis':'Author-derived implementation and information-projection witnesses, not independent legal references'})
    # Cheap diagnostic precedes compilation.
    for rows in cases.values():
        for row in rows:
            actual=evaluate(row['bundle'],row['snapshot'],row['rule_id'],row['valid_at'],row['known_at'])
            assert actual['status']==row['expected']['status'],row['id']
            if row['id'].endswith('.historical'):assert actual['reason_codes']==['E_VERSION_TIME']
    results=[]
    for parent,child in children:
        ident=child['id'];rows=cases[ident];out=OUT/ident
        built=build_candidate(child['bundle'],out/'java',JDK)
        verification=verify_candidate(built,rows,JDK)
        diverse=diverse_backends(rows,built,out/'independent')
        results.append({'child_id':ident,'parent_candidate_id':parent['candidate_id'],
            'parent_review':parent['review']['judgment'],'bundle_hash':digest(child['bundle']),
            'case_count':len(rows),'verification':verification,'backends':diverse,
            'historical_status':'ERROR','historical_reason':'E_VERSION_TIME','parent_discharged':False})
    assert sha(SOURCE)==source_hash
    value={'status':'CHILD_LIMITATIONS_REPRODUCED','case_count':9,'children':results,
           'world_pairs':world_pairs(),'historical_replay_covered':False,
           'parent_equivalence_established':False,'release_eligible':False}
    save(OUT/'result.json',value)
    save(OUT/'run-manifest.json',{'command':[str(ROOT/'.venv/bin/python'),'scripts/assurance_round15_witnesses.py'],
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'environment':str(ROOT/'.venv'),'cpu_gpu':'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'seeds':'N/A; deterministic','source_sha256':source_hash,'script_sha256':sha(Path(__file__)),
        'plan':'docs/implementation/interpretation-round15/delivery-verification-plan.md',
        'wall_seconds':time.monotonic()-began,'result_sha256':sha(OUT/'result.json'),
        'files':{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}})
    print(value['status'],value['case_count'])


if __name__=='__main__':run()
