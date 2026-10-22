"""Retain original-page decisions and a concrete migration continuation."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_selected_role_review as a

def main():
    a.frozen()
    packet=a.read(a.HERE/'source-packet.json.gz')
    reasons={108:'Bold option/language title followed by centered section1 heading; retain option and language context.',
        110:'Centered bold section2 heading; the selected title removes the separately unselected guarantee branch.',
        111:'Centered section3 title and italic subsection1 caption; operative interest wording follows separately.',
        113:'Centered section4 heading; payment caption and obligations start below in an OPERATIVE source unit.',
        123:'Centered section6 agent title; appointment caption and obligations start below in an OPERATIVE source unit.',
        125:'Centered section7 tax heading; withholding and exceptions are separate body text.',
        126:'Centered section8 presentment and section9 default headings; operative rules follow separately.',
        128:'Centered section10 substitution heading; selected subsection1 caption and substantive conditions remain in OPERATIVE text.',
        129:'Centered section11 amendment/representative heading; amendment authority and majority rules remain in body text.',
        130:'Italic subsection6 caption and two-line subsection7 heading, followed by italic(a)/(b) captions; body rights and procedure remain separate.',
        131:'Italic(c)/(d)/(e) procedure captions and centered section12 heading; substantive procedure and issuance provisions remain.',
        133:'Centered section15 language heading; the selected governing-language statement is separate body text.'}
    renders={r['page']:r for r in packet['renders']}
    assert set(reasons)==set(renders)
    rows=[]
    for candidate in packet['candidates']:
        unit=candidate['unit'];page=unit['source']['page']
        rows.append({'unit':unit['unit'],'text':unit['text'],'source_segments':candidate['exact_segments'],
            'decision':'HEADER','basis':reasons[page],'image':renders[page],
            'context_retained':True,'selected_text_change':False,'review_kind':'AGENT_SOURCE_READING'})
    plan='docs/plans/prospectus-structural-role-migration-2026-10-18.md'
    review={'status':'PASS','source_packet_sha256':a.sha(a.HERE/'source-packet.json.gz'),
        'decisions':rows,'all12_rendered_pages_inspected':True,'independent_human_acceptance':False,
        'mixed_nodes':[{**r,'next_treatment':'Remove reviewed structural spans only; preserve original ID and remaining caption spans as UNKNOWN'}
            for r in packet['affected_clauses'] if not r['only_candidate_units']],
        'protected_unknown_ids':packet['protected_unknown_ids'],
        'findings':['44 finite structural source decisions; no broad document exclusion',
            '14 entirely structural nodes; five nodes include caption prefixes from OPERATIVE units',
            'p130:l31-37 extraction fragments a single visual subtitle; group membership retained without silently reordering source text',
            'Definition-source/application assembly binding and reference admissions require explicit migrated versions',
            'Previous seven missing heading-use rows reflect HEADER-filtered operative lookup; no lost source text'],
        'next_plan':plan,'next_plan_sha256':a.sha(ROOT/plan),
        'next_action':'Prepare exact optional role migration, protected legacy profiles, independent full delta and reviewed cumulative resource extension',
        'production_changes':False,'original_task_complete':False,
        'resources_for_migration':'Existing3600s cannot cover full migration validation; review4800s/512MiB cumulative ceiling with all prior costs retained'}
    a.save(a.HERE/'source-review.json',review)
    a.save(a.HERE/'accounting-addendum.json',{'extra_root_files':[{'path':a.rel(p),'sha256':a.sha(p),'bytes':p.stat().st_size}
        for p in (Path(__file__),ROOT/plan)],'manual_source_reading_seconds':'UNKNOWN','prior_costs_reset':False})
    with (a.HERE/'RESULT.md').open('x') as f:f.write('''# Selected structural roles reviewed against original pages

All44 candidates were inspected on12 original PDF pages. They are structural
titles and captions. The14 wholly structural clause nodes can be removed from
semantic inference under that exact reading. Five further nodes include caption
prefixes from OPERATIVE units; these must be shortened by exact spans while
preserving their residual uncertainty and all substantive text. No production
role, source text or answer changed in this source-review package.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Accept finite structural source review | Every candidate has original-page and exact-source basis | Mixed nodes detected and protected | Full migration compatibility and indirect identity dependencies | Exact optional migration and complete predicted-delta comparison | Automatic heading recognition, legal completeness or whole-build completion |

The strongest alternative explanation is context lost through a role change.
Retain every unit, source map, section group and selected character; compare all
dependent outputs. The next reviewed plan explicitly preserves the five mixed
residuals and the unresolved default/agent fields. It must not remove uncertainty
merely to lower counts. Budget history remains cumulative; full migration needs
an explicit reviewed extension before execution.
''')
    print(json.dumps({'status':'PASS','decisions':len(rows),'mixed_residuals_preserved':5,'resources':a.costs()}))

if __name__=='__main__':main()
