"""Finish the admitted source audit without changing its frozen method."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_question_scope_repair as a

def main():
    a.frozen()
    receipt=a.read(a.HERE/'source-reading-manifest.json')
    helper=ROOT/'scripts/prospectus_question_source_readings.py'
    assert a.sha(helper)==receipt['method_sha256']
    # Account the completed command once, without rerunning it.
    a.save(a.HERE/'stages/source-reading/result.json',receipt)
    a.save(a.HERE/'stages/source-reading/started.json',{
        'command':receipt['command'],'receipt_imported':True,'command_rerun':False,
        'original_manifest_sha256':a.sha(a.HERE/'source-reading-manifest.json')})
    p=a.read(a.prior.HERE/'complete-products.json.gz')
    units={u['unit']:u for u in p['P2']['payload']['assembly']['units']}
    readings=a.read(a.HERE/'exceptional-source-readings.json.gz')
    missing=[]
    for item in readings['missing_selected_occurrences']:
        piece=item['piece']
        # Retain full source inventory objects; no semantic inference from uses.
        missing.append(item)
    header_ids=['p118:l15','p118:l16','p132:l1','p132:l2','p132:l40','p132:l41','p132:l42']
    headers=[units['basf-base-september-2022-exchange:'+i] for i in header_ids]
    assert all(u['role']=='HEADER' for u in headers)
    default_result=a.AUTH/'attempts/basf-meanings/attempt-021/result.json'
    default=a.read(default_result)
    assert default['comparison']['complete_answer_equal020']
    assert default['verification']['valid']['checked_answers']==192
    plan='docs/plans/prospectus-question-integrity-and-source-closure-2026-10-18.md'
    a.save(a.HERE/'source-analysis.json',{
        'status':'PASS','original_identifiers_preserved':True,
        'summary_sha256':a.sha(a.HERE/'summary.json'),
        'unmatched_sha256':a.sha(a.HERE/'unmatched.json.gz'),
        'exceptional_readings_sha256':a.sha(a.HERE/'exceptional-source-readings.json.gz'),
        'next_plan':plan,'next_plan_sha256':a.sha(ROOT/plan),
        'next_action':'Reproduce complete-question consumer consistency gap; if reproduced repair before source-role/profile migration',
        'unmatched_reconciliation':{'absent_application_targets':20,'open_conditions':12,
            'all32_source_addressed':True,'legal_targets_resolved':False,'event_facts_supplied':False},
        'selected_unknown':{'total':51,'structural_or_title_fragments':44,
            'default_f_lines':5,'calculation_agent_label_and_placeholder':2,
            'roles_changed':False,'source_layout_review_required_before_role_change':True},
        'missing_selected_uses':{'count':11,'whitespace':4,'already_retained_headers':headers,
            'finding':'Operative-use lookup omits HEADER roles; these seven source headings are retained, not missing'},
        'default_f':{'implementation':'src/legalmath/prospectus/basf_default_f_current.py',
            'consumer':'src/legalmath/prospectus/successor/service.py',
            'retained_result':a.rel(default_result),'retained_result_sha256':a.sha(default_result),
            'existing_finite_decisions':192,'option_enabled_in_audit_baseline':False,
            'governing_reading_proved':False,'candidate_set_exhaustive':False,
            'rebind_after_answer_change':'Verify original/selected source groups and retain alternative semantics'},
        'source_role_cause':'BASF assembly retains other dossier units as UNKNOWN; all receive Q1/Q2 by default. This is conservative unreviewed scope, not proof all units have operative effect.',
        'conditional_analysis':'Missing client facts do not prevent source-bound hypothetical analysis; no actual event activation is inferred.',
        'statutory_priority':'Selected section11 amendment authority and historical SchVG application; preserve other19 application targets and uncertainty.',
        'integrity_hypothesis':'Frozen consumer checks dependency-owned uncertainty but does not explicitly recompute all question fields; test actual resealed inputs before editing.',
        'limits':['No source relevance exclusion from selected-copy membership','No headings reclassified without original-layout review',
            'No legal completion from counts','No missing-package verdict from optional-profile omission'],
        'production_changes':False})
    a.save(a.HERE/'accounting-addendum.json',{
        'receipt':a.rel(a.HERE/'source-reading-manifest.json'),'counted_by_frozen_costs':True,
        'additional_root_files':[{'path':a.rel(path),'sha256':a.sha(path),'bytes':path.stat().st_size}
            for path in (helper,Path(__file__),ROOT/plan)],
        'manual_source_analysis_seconds':'UNKNOWN','prior_costs_reset':False})
    with (a.HERE/'RESULT.md').open('x') as f:
        f.write('''# Remaining question uncertainty traced to sources

The audit preserves every original identifier and maps all32 exceptional
diagnostics to source clauses. The seven apparently missing selected headings
already exist as HEADER units; the lookup covers operative uses. Four further
pieces are spaces. This is not evidence of lost source text.

The selected UNKNOWN set contains44 structural fragments, five default(f)
lines and two calculation-agent fields. Existing default(f) alternatives are
already available through an optional consumer profile; its omission from this
baseline does not establish missing implementation. Historical statutory
applications, event conditions and unreviewed source roles remain unresolved.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Accept lossless source audit | Original lists preserved; all32 exceptional entries source-addressed | No lost IDs or invented anchors | Legal relevance and historical applications | Test full-question consistency, then source-role and conditional-law repair | Legal answer or original task complete |

The strongest alternative explanation for the suspected frozen-answer gap is
an existing check outside the inspected dependency checks. The next actual
consumer diagnostic must distinguish it before production edits. Counts and
mapping success do not prove source meanings. Source-reading helper time is
accounted from its actual receipt; manual/controller time remains UNKNOWN.
''')
    print(json.dumps({'status':'PASS','source_audit_ready_to_seal':True,'resources':a.costs()}))

if __name__=='__main__':
    main()
