"""Preserve the failed audit and stage its reviewed source-address repair."""
import ast
import difflib
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_question_scope_audit as old

PREP=old.AUTH/'reviews/question-scope-provenance-292'
NEW='scripts/prospectus_question_scope_repair.py'
PLAN='docs/plans/prospectus-question-scope-provenance-repair-2026-10-18.md'


def main():
    started=time.monotonic()
    old.frozen()
    failure=old.read(old.HERE/'stages/inventory/failure.json')
    assert failure['type']=='KeyError' and failure['message']=="'unit'"
    old.save(old.HERE/'result.json',{'status':'FAIL','task':'basf-references',
        'result_kind':'QUESTION_AUDIT_SOURCE_SCHEMA_FAILURE','original_task_complete':False,
        'failure':failure,'resources':old.costs(),'production_changed':False,
        'attribution':'Local audit confused source metadata with exact occurrence anchor',
        'next_action':'Changed source-address method; preserve exact copied segments and gaps'})
    old.save(old.HERE/'run-manifest.json',{'command':old.read(old.HERE/'stages/inventory/started.json')['command'],
        'plan':old.PLAN,'result':old.rel(old.HERE/'result.json'),'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU; GPU intentionally hidden','random_seeds':'N/A deterministic',
        'data_version':old.sha(old.prior.HERE/'complete-products.json.gz'),
        'git_commit':old.read(old.HERE/'admission.json')['git_commit'],
        'wall_seconds':failure['wall_seconds'],'prior_costs_reset':False})
    with (old.HERE/'RESULT.md').open('x') as stream:
        stream.write("""# Audit source-address failure retained

The audit failed on a nonexistent source metadata field before producing its
inventory. Retained assembly items identify their occurrence separately; exact
raw copies require the occurrence mapper and any explicit character map.
The failed diagnostic establishes no conclusion about the legal answer.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Reject this audit result | Inventory absent | Local source-schema assumption failed | Remaining exact map and relevance findings | Reviewed changed mapper | Candidate legal failure or completed source audit |
""")
    old.save(old.HERE/'outputs.json',{str(p.relative_to(old.HERE)):old.sha(p) for p in old.HERE.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts})
    text=(ROOT/old.METHOD).read_text()
    text=text.replace('from scripts import prospectus_definition_package as prior',
        'from scripts import prospectus_definition_package as baseline_package\n'
        'from scripts import prospectus_question_scope_audit as failed\nprior=baseline_package')
    text=text.replace('question-scope-audit-291','question-scope-provenance-292')
    text=text.replace('attempt-032','attempt-033').replace("METHOD='scripts/prospectus_question_scope_audit.py'",
                                                         "METHOD='"+NEW+"'")
    text=text.replace("PLAN='"+old.PLAN+"'","PLAN='"+PLAN+"'")
    text=text.replace("'cumulative026_031_measured_seconds'","'cumulative026_032_measured_seconds'")
    text=text.replace("'cumulative026_031_bytes'","'cumulative026_032_bytes'")
    text=text.replace('316*1024**2','380*1024**2').replace('320*1024**2','384*1024**2')
    text=text.replace('cumulative026_032','cumulative026_033')
    # The start snapshot retains the failed audit's actual previous key.
    text=text.replace("start['prior_resources']['cumulative026_033_measured_seconds']",
                      "start['prior_resources']['cumulative026_032_measured_seconds']")
    text=text.replace("start['prior_resources']['cumulative026_033_bytes']",
                      "start['prior_resources']['cumulative026_032_bytes']")
    text=text.replace("    for folder in (PREP,HERE):",
        "    seconds+=read(PREP/'repair-preparation.json')['wall_seconds']\n"
        "    for folder in (PREP,HERE):",1)
    text=text.replace("program['revision']==290","program['revision']==291")
    text=text.replace("proposal['revision']=291","proposal['revision']=292")
    text=text.replace("'revision':291","'revision':292")
    text=text.replace("'baseline_revision']=291","'baseline_revision']=292")
    text=text.replace("'revisions/0291.json'","'revisions/0292.json'")
    text=text.replace("len(attempts)==31 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE)",
                      "len(attempts)==32 and any(e['kind'] in ('RECORD','REJECT') and e.get('attempt')==rel(failed.HERE)")
    text=text.replace("'prior_resources':prior.costs()","'prior_resources':failed.costs()")
    text=text.replace("'source_relevance_decisions_made':False","'source_relevance_decisions_made':False")
    text=text.replace("'src/legalmath/prospectus/successor/reference_closure.py'",
        "'src/legalmath/prospectus/successor/reference_closure.py',\n"
        "        'src/legalmath/prospectus/successor/occurrences.py',\n"
        "        'scripts/prospectus_question_scope_repair_preparation.py'")
    text=text.replace("save(PREP/'freeze.json',{'bindings':bindings",
        "bindings[rel(failed.HERE/'outputs.json')]=sha(failed.HERE/'outputs.json')\n"
        "    bindings[failed.METHOD]=sha(ROOT/failed.METHOD)\n"
        "    save(PREP/'freeze.json',{'bindings':bindings")
    text=text.replace("maximum_new_attempts']=32","maximum_new_attempts']=33")
    text=text.replace("32 admissions;","33 admissions;").replace("320MiB","384MiB")
    text=text.replace("'previous_maximum':31,'new_maximum':32","'previous_maximum':32,'new_maximum':33")
    text=text.replace("'Admission31 to32;existing cumulative time and storage unchanged'",
        "'Admission32 to33;existing cumulative time unchanged;storage320 to384MiB includes failed audit and repair'")
    text=text.replace("'reason':'Completed packaging enables return to actual question-level substantive gaps'",
        "'reason':'Failed audit used metadata instead of exact occurrence source anchors; changed mapper preserves source gaps'")
    needle="    uncovered=set(clauses['uncovered_units'])"
    addition="""    from legalmath.prospectus.successor.occurrences import segments
    raw_by_id={k:v[1] for k,v in raw.items()}
    def source_segments(unit):
        matches=segments(graph,unit,_raw=raw_by_id)
        for segment in matches:
            anchor=segment['source']
            original=raw_by_id[anchor['unit']]
            assert (anchor['document'],anchor['source_sha256'])==(original['document'],original['source_sha256'])
            assert original['raw'][anchor['start']:anchor['end']]==anchor['quote']
            assert unit['text'][segment['start']:segment['end']]==anchor['quote']
        return matches
"""
    assert text.count(needle)==1
    text=text.replace(needle,addition+needle)
    before="""            source_id=unit['source']['unit']
            assert source_id in raw
            j,original=raw[source_id]
            source_rows[unit_id]={'assembly_index':i,'assembly_sha256':digest(unit),'raw_index':j,
                'raw_sha256':digest(original),'document':original['document'],'page':original['page'],
                'role':unit['role'],'context':unit['context'],'questions':unit['questions'],
                'selected_source_copy':unit_id in selected}
            doc_counts[(original['document'],unit['role'],unit_id in selected)]+=1"""
    after="""            matches=source_segments(unit)
            anchors=[]
            covered=set()
            for segment in matches:
                j,original=raw[segment['source']['unit']]
                anchors.append({'raw_index':j,'raw_sha256':digest(original),**segment})
                covered.update(range(segment['start'],segment['end']))
            unmapped=[n for n,c in enumerate(unit['text']) if not c.isspace() and n not in covered]
            source_rows[unit_id]={'assembly_index':i,'assembly_sha256':digest(unit),'exact_segments':anchors,
                'document':unit['source']['document'],'page':unit['source']['page'],
                'role':unit['role'],'context':unit['context'],'questions':unit['questions'],
                'unmapped_nonspace_positions':unmapped,'selected_source_copy':unit_id in selected}
            doc_counts[(unit['source']['document'],unit['role'],unit_id in selected)]+=1"""
    assert text.count(before)==1
    text=text.replace(before,after)
    before="""                j,original=raw[unit['source']['unit']]
                examples.append({'unit':uid,'assembly':unit,'raw':original})"""
    after="""                matches=source_segments(unit)
                originals=[raw[s['source']['unit']][1] for s in matches]
                examples.append({'unit':uid,'assembly':unit,'raw_sources':originals,
                                 'source_mapping':source_rows[uid]})"""
    assert text.count(before)==1
    text=text.replace(before,after)
    text=text.replace("'unmatched_identifiers':len(all_unmatched),",
        "'source_units_with_unmapped_text':sum(bool(v['unmapped_nonspace_positions']) for v in source_rows.values()),\n"
        "        'unmatched_identifiers':len(all_unmatched),")
    text=text.replace("'scripts.prospectus_question_scope_audit',stage","'scripts.prospectus_question_scope_repair',stage")
    ast.parse(text)
    with (ROOT/NEW).open('x') as stream:
        stream.write(text)
    PREP.mkdir(parents=True,exist_ok=True)
    with (PREP/'method.diff').open('x') as stream:
        stream.writelines(difflib.unified_diff((ROOT/old.METHOD).read_text().splitlines(True),text.splitlines(True),
            fromfile=old.METHOD,tofile=NEW))
    old.save(PREP/'repair-preparation.json',{'status':'PASS','production_changes':False,
        'changed_source_sites':2,'candidate_evaluated':False,'wall_seconds':time.monotonic()-started,
        'old_method_sha256':old.sha(ROOT/old.METHOD),'new_method_sha256':old.sha(ROOT/NEW),
        'failed_outputs_sha256':old.sha(old.HERE/'outputs.json')})
    print({'status':'PASS','failed_audit_sealed':True,'changed_source_sites':2,'candidate_evaluated':False})


if __name__=='__main__':
    main()
