"""Create the reviewed BASF agent-change packet from current exact source data."""
from copy import deepcopy
from pathlib import Path
import sys
sys.path[:0] = [str(Path.cwd()), str(Path.cwd() / 'src')]

from legalmath.prospectus.successor import basf, jobs, source_graph
from legalmath.prospectus.successor.contracts import digest, read, write
from scripts.prospectus_closure_basf import prepared_request
from legalmath.prospectus.successor.basf_agents import AGENT_PARAGRAPHS, AUTHORITY_IDS, paragraph_spans, source_pieces

ROOT = Path.cwd()
OUT = ROOT / 'docs/implementation/prospectus-integration-closure/basf-agent-notices/review.json'
SOURCE_IMAGE = ROOT / 'docs/implementation/prospectus-basf-scope-repair/source-review-001/base-124.png'
FINAL_IMAGE = ROOT / 'docs/implementation/prospectus-basf-continuation-2026-10-05/review-images/basf-2032-final-7.png'


def source(graph, unit, start=0, end=None):
    row = next(u for u in graph['units'] if u['id'] == unit)
    end = len(row['raw']) if end is None else end
    return {'unit': unit, 'document': row['document'], 'source_sha256': row['source_sha256'],
            'start': start, 'end': end, 'quote': row['raw'][start:end]}


def main():
    graph = source_graph.build(jobs.basf_request(ROOT)['bundle'], ROOT)
    construction = basf.construct(graph, read(ROOT / jobs.BASF))
    request = prepared_request(ROOT, graph)
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    units = {u['unit']: u for u in assembly['units']}
    notices = read(ROOT / 'docs/implementation/prospectus-integration-closure/basf-notices/review.json')
    authority = [source(graph, key) for key in AUTHORITY_IDS]
    selected = []
    for unit in dict.fromkeys(sum(AGENT_PARAGRAPHS.values(), [])):
        spans = [{'unit': unit, 'start': 0, 'end': len(units[unit]['text'])}]
        selected.append({'unit': unit, 'text_sha256': digest(units[unit]['text'].encode()),
                         'role': 'OPERATIVE',
                         'sources': [r['source'] for r in source_pieces(graph, units, spans)],
                         'reason': 'Original page 124 reviewed; exact surviving construction pieces. Line 68 includes a separately retained United States definition.'})
    clauses = []
    readings = {
        'initial-agent': {
            'reading': 'The selected initial Fiscal and Paying Agent is Deutsche Bank Aktiengesellschaft, Trust & Agency Services, Taunusanlage 12, 60325 Frankfurt am Main, Germany. The final terms separately name NatWest Markets N.V. as Calculation Agent.',
            'fiscal_and_paying_agent': 'Deutsche Bank Aktiengesellschaft',
            'final_term_calculation_agent': 'NatWest Markets N.V.',
            'calculation_agent_office': 'UNRESOLVED',
            'qualification': 'Final-term labels and names identify the issue agents. No calculation-agent office is supplied and the B54 template name/office placeholder is retained.'},
        'office-replacement': {
            'reading': 'The Fiscal Agent, Paying Agent and, where selected, Calculation Agent may replace their designated office with another designated office in the same country.',
            'same_country': True,
            'qualification': 'The clause supplies a same-country office-change rule; it does not identify a replacement office or establish that a change occurred.'},
        'appointment-change': {
            'reading': 'The issuer may change or end the appointment of the Fiscal Agent or Paying Agent, and where the calculation-agent branch is operative, may change or end that appointment and appoint another or additional agent; the issuer must maintain a Fiscal Agent.',
            'maintain_fiscal_agent': True,
            'maintain_calculation_agent_if_selected': True,
            'calculation_agent_condition': 'if a Calculation Agent is to be appointed',
            'qualification': 'The frozen construction retains the calculation-agent wording. Its template condition is if a Calculation Agent is to be appointed; the issuer then maintains one. Final terms name NatWest, but B54 name/office construction authority remains unresolved.'},
        'effectiveness-reference': {
            'reading': 'An appointment, removal, appointment of an additional agent or other change becomes effective only after holders are informed under section 13 with at least 30 and no more than 45 days notice; an insolvency change is immediately effective.',
            'notice_window_days': [30, 45],
            'insolvency_immediate_effect': True,
            'notice_reference': 'agent-change-notices',
            'actual_change_validity': 'NOT_EVALUATED',
            'qualification': 'The reading supplies the contractual condition and onward notice dependency; no actual change, insolvency event, notice or effective date is supplied.'},
    }
    for cid, ids in AGENT_PARAGRAPHS.items():
        spans = paragraph_spans(units, cid)
        clauses.append({'id': cid, 'units': ids, 'spans': spans,
                        'quote': ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in spans), 'effect': 'none',
                        'effect_scope': ['Q1', 'Q2'],
                        'effect_explanation': 'No direct principal-loss or compulsory-conversion effect asserted; procedural appointment conditions remain positive typed meaning.',
                        'actor': 'agent' if cid.endswith('office-replacement') else 'issuer',
                        'affected': 'holder', 'modality': 'may' if cid.endswith('office-replacement') else 'statement', 'election': 'none',
                        'assets': [], 'role': 'OPERATIVE', 'polarity': True, 'conditions': [], 'exceptions': [],
                        'questions': ['Q1', 'Q2'], 'origin': 'development-source-review',
                        'agent_reading': readings[cid.split(':')[-1]],
                        'source_uses': source_pieces(graph, units, spans)})
    clauses[0]['selection_authority'] = authority
    ref_targets = deepcopy(notices['references'][0]['targets'])
    packet = {
        'version': 'basf-agents-review.v1', 'graph_sha256': digest(graph),
        'construction_sha256': digest(construction), 'baseline_assembly_sha256': digest(assembly),
        'notice_clauses_sha256': digest(notices['clauses']),
        'review': {'reviewer': 'Codex implementer original-page review', 'kind': 'DEVELOPMENT',
                   'reason': 'Original p124 and final-terms p7 reviewed for selected agents and section 6(2) change conditions; not independent legal adjudication.'},
        'images': {
            str(SOURCE_IMAGE.relative_to(ROOT)): digest(SOURCE_IMAGE.read_bytes()),
            str(FINAL_IMAGE.relative_to(ROOT)): digest(FINAL_IMAGE.read_bytes())},
        'authority_sources': authority,
        'units': selected,
        'references': [{'id': 'agent-change-notices', 'form': 'relative',
                        'source': source(graph, 'basf-base-september-2022-exchange:p124:l66', 67, 71),
                        'from_use': 'basf-base-september-2022-exchange:p124:l66', 'language': 'de/en',
                        'questions': ['Q1', 'Q2'],
                        'authority': source(graph, 'basf-base-september-2022-exchange:p124:l66', 67, 71),
                        'discovery_ids': ['basf-base-september-2022-exchange:p124:l66:ref:67'],
                        'targets': ref_targets,
                        'reason': 'Section 6(2) expressly makes the selected change effective only after advance notice under section 13; the complete selected §13 body is the target.'}],
        'clauses': clauses,
        'markers': {'calculation_agent_office': {'status': 'UNRESOLVED', 'text': '[Name und bezeichnete Geschäftsstelle]',
                                                  'reason': 'No authority supplies the template placeholder; final-term NatWest name is not an office.'},
                    'excluded_branches': ['Canadian/CDS branch', 'U.S.-dollar/New York branch'],
                    'retained_conditional_wording': 'Calculation-agent wording is retained by construction; B54 remains unresolved',
                    'us_definition': 'Retained independently of the excluded U.S.-dollar branch; meaning outside this package'},
        'limitations': ['Development reading only', 'No actual agent change, notice, insolvency or effective date supplied',
                        'Q1/Q2 remain UNKNOWN and Q3 remains PARTIAL', 'No independent legal acceptance']}
    write(OUT, packet)
    print(OUT)


if __name__ == '__main__':
    main()
