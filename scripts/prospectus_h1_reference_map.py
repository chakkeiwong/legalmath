"""Reviewed H1 reference addresses; navigation does not prove referenced claims."""
from copy import deepcopy
import json
import re
import sys
import time

from scripts import prospectus_h1_reference_state_audit as previous

common = previous.common
ROOT, BASE, AUTH = previous.ROOT, previous.BASE, previous.AUTH
read, save, require, sha, rel = common.read, common.save, common.require, common.sha, common.rel
digest, compact = common.digest, common.compact_digest
at, source = previous.at, previous.source
DOCUMENT, PREFIX = previous.DOCUMENT, previous.PREFIX
TEMP = ROOT / '.localresources/prospectus-preparation/h1-reference-closure'
PLAN = 'docs/plans/prospectus-h1-reference-closure-2026-10-22.md'
STATE = previous.TEMP / 'reference-state-065.json'
SNAPSHOT = ROOT / '.localresources/prospectus-preparation/h1-current-source-audit/snapshot-063.json'

# Reviewed printed declarations; endpoints are the next heading at the same
# level, or the explicit parent/report end. No title is silently corrected.
NOTE_STARTS = [(61,4),(67,1),(94,1),(97,1),(103,1),(104,1),(105,1),(106,1),
    (106,53),(107,1),(107,40),(108,13),(115,12),(116,1),(116,43),(117,9),
    (118,1),(119,174),(120,5),(122,1),(123,1),(126,1),(126,54),(128,1),
    (129,19),(131,1),(133,1),(134,41),(136,1),(137,1),(137,41),(138,1),
    (141,1),(142,1),(144,73),(146,1),(147,1),(149,1),(151,1),(153,1),
    (154,1),(158,1),(159,16),(160,19),(170,1),(171,1)]
POLICY_STARTS = [(67,2),(68,14),(73,1),(73,12),(75,10),(77,11),(80,12),
    (80,24),(81,18),(82,1),(82,5),(83,15),(84,26),(84,35),(85,20),
    (90,1),(90,27),(91,7),(92,1),(92,12),(92,14),(93,1),(93,9)]
JUDGMENT_STARTS = [(94,12),(94,27),(95,5),(95,14),(95,25),(96,8),(96,20)]
REPORT_END = (172,1)

# Destinations read separately from the original-string parser below.
PROSE_TARGETS = {
    (59,19): ['37'], (59,20): ['12'], (59,21): ['38'],
    (59,352): ['37'], (59,353): ['12'], (59,354): ['38'],
    (59,375): ['37'], (59,376): ['12'], (59,377): ['38'], (59,460): ['37'],
    (64,313): ['2.2'], (65,2): ['42'], (65,10): ['45'], (65,11): ['27'],
    (65,33): ['2.2'], (67,25): ['2.2'], (68,11): ['3'],
    (75,23): ['2.4'], (75,27): ['2.6'], (77,29): ['23'], (80,22): ['2.6'],
    (91,24): ['2.4'], (92,16): ['4'], (94,7): ['2'], (95,6): ['2.5'],
    (95,19): ['2.2'], (99,31): ['2'], (103,56): ['21'],
    (103,58): ['2.4','2.18'], (103,60): ['2.5','2.6','2.8'],
    (106,52): ['41'], (106,80): ['2.3'], (107,8): ['35'],
    (107,47): ['12'], (107,49): ['12'], (107,70): ['2.15','12'],
    (109,53): ['28'], (109,54): ['2.15'], (114,2): ['2.15'],
    (114,35): ['2.15'], (115,2): ['2.15'], (115,7): ['36'],
    (118,35): ['2.6'], (118,37): ['39'], (120,1): ['2.6'], (120,80): ['2.6'],
    (120,82): ['3.1'], (120,83): ['39'], (121,118): ['8'],
    (124,3): ['42'], (124,4): ['2.2'], (124,5): ['32','42'], (124,7): ['32'],
    (126,53): ['39'], (127,97): ['2.4'], (127,103): ['7'], (131,37): ['2.13'],
    (132,275): ['45'], (135,11): ['2.6'], (136,28): ['39'], (138,72): ['21'],
    (139,56): ['2.8'], (145,190): ['2.8'], (145,194): ['10'], (146,14): ['12'],
    (146,59): ['2.6'], (148,11): ['2.15'], (148,14): ['2.15'], (154,2): ['1'],
    (157,26): ['2.5'], (161,1): ['2.4'],
}
SPACED_TWELVE = {(59,20),(59,353),(59,376),(107,47),(107,49),(146,14)}
STATEMENT_SPECIAL = {'25 and 26': ['25','26'], '1 9, 20 and 22': ['19','20','22'],
    '24, 26 and 28': ['24','26','28']}
LIMITS = {'source_specific_supplied_review': True, 'address_availability_only': True,
    'historical_statuses_replaced': False, 'financial_reconciliation_established': False,
    'referenced_claims_proved': False, 'source_authenticity_established': False,
    'legal_incorporation_selected': False, 'implicit_references_complete': False,
    'automatic_interpretation_proved': False, 'original_task_complete': False}


def parse_prose(text, location):
    if location in SPACED_TWELVE:
        require('Note 1 2' in text, 'Reviewed spaced Note12 changed')
        text = text.replace('Note 1 2','Note 12')
    found = []
    number = r'\d+(?:\.\d+)?'
    for match in re.finditer(r'\b[Nn]otes?\s+(' + number + r'(?:\s*(?:,\s*|and\s+)' + number + r')*)', text):
        found.extend(re.findall(number,match.group(1)))
    return found


def parse_column(text):
    normalized = '19, 20 and 22' if text == '1 9, 20 and 22' else text
    tokens = normalized.replace(',',' ').replace('and',' ').split()
    require(tokens and all(t.isdigit() and 1<=int(t)<=46 for t in tokens), 'Ambiguous statement note')
    return tokens


def anchor(units, location):
    return source(units,*location)


def address_registry(units, answer, snapshot):
    declarations = [(str(i),loc,NOTE_STARTS[i] if i<46 else REPORT_END,'NOTE')
        for i,loc in enumerate(NOTE_STARTS,1)]
    declarations += [('2.'+str(i),loc,POLICY_STARTS[i] if i<23 else NOTE_STARTS[2],'POLICY')
        for i,loc in enumerate(POLICY_STARTS,1)]
    declarations += [('3.'+str(i),loc,JUDGMENT_STARTS[i] if i<7 else NOTE_STARTS[3],'JUDGMENT')
        for i,loc in enumerate(JUDGMENT_STARTS,1)]
    ordered = sorted((u for u in units.values() if u['document']==DOCUMENT),key=lambda u:(u['page'],u['order']))
    scanned = [(str(int(m.group(1))),(u['page'],u['order'])) for u in ordered
        if (m:=re.match(r'^NOTE\s+(\d+)\b',u['raw']))]
    require(scanned==[(str(i),loc) for i,loc in enumerate(NOTE_STARTS,1)], 'Printed note declaration mismatch')
    result = []
    for number,start,end,level in declarations:
        heading,boundary = anchor(units,start),anchor(units,end)
        if level!='NOTE':
            require(re.match(r'^'+re.escape(number)+r'\.\s',heading['quote']), 'Printed subsection mismatch')
        selected = [u for u in ordered if start<=(u['page'],u['order'])<end]
        sections = {}
        for u in selected:
            for ref in snapshot['direct_references'].get(u['id'],[]):
                path = ref['path']
                if ref.get('context') or not path.startswith('/source_statement_cells/'):
                    continue
                path = '/answer'+path
                value = at(answer,path)
                require(isinstance(value,dict) and value.get('id',value.get('unit'))==u['id'], 'Changed direct target identity')
                require(u['raw'][ref['start']:ref['end']]==value.get('quote'), 'Changed direct target quote')
                section = '/'.join(path.split('/')[:4])
                sections.setdefault(section,[]).append({'unit':u['id'],'path':path,
                    'start':ref['start'],'end':ref['end'],'sha256':compact(value)})
        require(sections,'No delivered direct references for '+number)
        result.append({'number':number,'level':level,'heading':heading,'end_exclusive':boundary,
            'end_basis':'NEXT_SAME_LEVEL_OR_PARENT_END' if number!='46' else 'SEPARATE_AUDITOR_REPORT_START',
            'source_units_sha256':compact(selected),'source_unit_count':len(selected),
            'delivered_sections':[{'path':p,'direct_sources':refs} for p,refs in sorted(sections.items())],
            'source_address_available':True,'complete_interpretation_established':False})
    return result


def reference_rows(units, answer, inventory):
    rows,observed = [],set()
    for row in inventory['prose_note_mentions']:
        if row['category'] not in ('INLINE_NUMBERED_REFERENCE_REQUIRES_TARGET_REVIEW','REVIEWED_SPLIT_REFERENCE'):
            continue
        first = row['sources'][0]
        loc = first['page'],first['order']
        require(loc in PROSE_TARGETS,'Unreviewed explicit reference')
        sources = [anchor(units,loc)]
        if loc in previous.SPLIT_NEXT:
            sources.append(anchor(units,previous.SPLIT_NEXT[loc]))
        require(row['sources']==sources,'Shifted source or split-reference anchor')
        numbers = PROSE_TARGETS[loc]
        require(parse_prose(' '.join(s['quote'] for s in sources),loc)==numbers,
            'Original prose destinations differ from reviewed list')
        observed.add(loc)
        rows.append({'id':first['id'],'kind':'SPLIT_PROSE' if len(sources)==2 else 'INLINE_PROSE',
            'sources':sources,'destinations':numbers,'availability':'DECLARED_TARGET_AND_DIRECT_READING_AVAILABLE',
            'referenced_claim_proved':False})
    require(observed==set(PROSE_TARGETS),'Reviewed explicit occurrence omitted')
    for row in inventory['statement_note_columns']:
        note = row['source']
        require(at(answer,row['path'])==note,'Statement reference changed')
        uid = note.get('id',note.get('unit'))
        u = units[uid]
        start,end = note.get('start',0),note.get('end',len(u['raw']))
        require(u['raw'][start:end]==note['quote'],'Statement source changed')
        expected = STATEMENT_SPECIAL.get(note['quote'],[note['quote']])
        require(parse_column(note['quote'])==expected,'Statement destinations changed')
        label_path = row['path'].rsplit('/notes/',1)[0]+'/label'
        require(at(answer,label_path)==row['row_label'],'Statement row context changed')
        original={k:u[k] for k in ('id','document','source_sha256','page','order','bbox')}|{'quote':u['raw']}
        rows.append({'id':row['path'],'kind':'STATEMENT_NOTE_COLUMN','sources':[original],
            'original_note_anchor':note,'reference_path':row['path'],'row_label':row['row_label'],
            'row_label_path':label_path,'destinations':expected,
            'availability':'DECLARED_TARGET_AND_DIRECT_READING_AVAILABLE','referenced_claim_proved':False})
    require(len(rows)==133,'Retained finite inventory changed')
    return rows


EXTRA_STATES = [
    ('afs-note18','afs_disclosures_evidence/dependency_resolution/note18',[(120,1),(120,2),(120,3),(120,4)],['18'],
     ['trading_balances_evidence/tables/2','trading_balances_evidence/clauses/4','trading_balances_evidence/clauses/5'],
     'SECTION_CONTINUATION_CONTEXT','The original Note18 continuation now has its designated-FVTPL balance table and designation clauses available.',
     'Designation is distinct from trading. The report uses and/or; no independent valuation or current-standard verification follows.'),
    ('afs-note41','afs_disclosures_evidence/dependency_resolution/note41',[(106,52)],['41'],
     ['related_parties_evidence/directory','related_parties_evidence/tables','related_parties_evidence/clauses/2',
      'related_parties_evidence/clauses/7','related_parties_evidence/distinctions'],
     'EXPLICIT_NUMBERED_REFERENCE','The related-party directory, dated balances and transaction disclosures are available.',
     'A source reference does not identify each sale counterparty or prove arm-length terms, compliance, entity identity or consolidation.'),
    ('judgments-tax-pension','critical_judgments_evidence/dependency_resolution/tax_and_pension_full_notes',
     [(96,i) for i in range(8,25)],['34','12'],
     ['provisions_tax_notes_evidence/clauses/8','provisions_tax_notes_evidence/tables/1',
      'provisions_tax_notes_evidence/tables/4','provisions_tax_notes_evidence/distinctions',
      'employee_benefits_notes_evidence/clauses/2','employee_benefits_notes_evidence/tables',
      'employee_benefits_notes_evidence/distinctions'],
     'REVIEWED_TOPICAL_ASSOCIATION_NOT_PRINTED_CITATION','Tax and employee-benefit readings now supply the associated disclosures and reported assumptions.',
     'These judgments print no numbered citation. Tax uncertainty, additional assessments, the reported tax-unit conflict and actuarial estimation remain; availability does not validate tax or pension values.'),
    ('policy-note23','financial_policies_evidence/source_dependencies/Note23',[(77,29),(77,30)],['23'],
     ['investment_hedges_evidence/clauses/2','investment_hedges_evidence/clauses/3',
      'investment_hedges_evidence/tables/2','investment_hedges_evidence/tables/3'],
     'EXPLICIT_NUMBERED_REFERENCE_WITH_DESCRIPTION_TENSION','The printed Note23 target and risk-management derivative reading are available.',
     'The policy describes a summary of assets/liabilities designated FVTPL at inception, whereas Note23 is headed derivatives for risk management. Preserve this mismatch; no corrected number or proof of that source description is supplied.'),
    ('hedges-note39','investment_hedges_evidence/source_dependencies/Note39',[(126,53)],['39'],
     ['income_collateral_evidence/tables/1','income_collateral_evidence/clauses/5',
      'income_collateral_evidence/clauses/6','income_collateral_evidence/dependency_resolution'],
     'EXPLICIT_NUMBERED_REFERENCE','The pledged-securities context, included collateral list and reported execution condition are available.',
     'The list is not proved exhaustive. Eligible securities differ from pledged balances; title, enforceability and holder recovery remain unproved.'),
    ('hedges-note7','investment_hedges_evidence/source_dependencies/Note7',[(127,101),(127,102),(127,103)],['7'],
     ['income_collateral_evidence/tables/0','income_collateral_evidence/clauses/1',
      'income_collateral_evidence/clauses/2','income_collateral_evidence/dependency_resolution'],
     'EXPLICIT_NUMBERED_REFERENCE','The FVTPL income table, hedged-item footnote and reported own-credit effects are available.',
     'Footnote inclusion does not reconcile every hedge component. Rounded own-credit period amounts are not cumulative balances, cash receipts or proof of credit improvement.'),
]


def historical_states(units, answer):
    rows = previous.check_states(answer,units)
    for row in rows:
        row['association_kind']='EXPLICIT_NUMBERED_REFERENCE'
        row['destinations']=[row['note']]
    for ident,flag,locations,numbers,targets,kind,current,remaining in EXTRA_STATES:
        expected = previous.HISTORICAL_LABELS[flag]
        require(at(answer,PREFIX+flag)==expected,'Historical dependency label changed')
        rows.append({'id':ident,'historical_flag':{'path':PREFIX+flag,'value':expected},
            'sources':[anchor(units,loc) for loc in locations],'destinations':numbers,'association_kind':kind,
            'targets':[{'path':PREFIX+p,'sha256':compact(at(answer,PREFIX+p))} for p in targets],
            'current_availability':current,'remaining':remaining,'target_available':True,
            'historical_flag_retained':True,'financial_reconciliation_established':False,'legal_effect_established':False})
    return rows


def clause_path(answer, section, key):
    rows=at(answer,PREFIX+section+'/clauses')
    matches=[i for i,row in enumerate(rows) if row.get('key')==key]
    require(len(matches)==1,'Missing reviewed clause '+key)
    return PREFIX+section+'/clauses/'+str(matches[0])


def build(units, answer, inventory, snapshot):
    registry=address_registry(units,answer,snapshot)
    references=reference_rows(units,answer,inventory)
    states=historical_states(units,answer)
    numbers={r['number'] for r in registry}
    require(all(set(r['destinations'])<=numbers for r in references+states),'Unknown referenced declaration')
    return {'registry':registry,'references':references,'historical_states':states,
        'discrepancies':[
            {'id':'policy2.23-heading-body','sources':[anchor(units,(93,i)) for i in range(9,14)],
             'targets':[clause_path(answer,'income_policies_evidence',k) for k in ('cash-heading','cash-definition','cash-restricted')],
             'explanation':'The printed heading says non-current assets held for sale; the body defines cash and cash equivalents. Both remain as printed.',
             'correction_selected':False},
            {'id':'policy2.6-note23-description','sources':[anchor(units,(77,29)),anchor(units,(77,30)),anchor(units,(126,54))],
             'targets':[clause_path(answer,'financial_policies_evidence','fvtpl-designation'),
                 clause_path(answer,'investment_hedges_evidence','derivative-dates')],
             'explanation':'The policy describes designated FVTPL assets/liabilities; the printed Note23 heading concerns risk-management derivatives. Availability does not prove that description or authorize redirecting the reference.',
             'correction_selected':False}],
        'inventory_scope':inventory['inventory_scope'],
        'excluded_mentions':[r for r in inventory['prose_note_mentions'] if r['category'] in
            ('GENERIC_OR_UNCLASSIFIED_MENTION','INSTRUMENT_NAME')],
        'limits':deepcopy(LIMITS)}


def compare_map(value, expected):
    require(value==expected,'Reference map differs from reviewed original addresses and current fields')
    return {'declarations':len(value['registry']),'explicit_occurrences':len(value['references']),
        'historical_states':len(value['historical_states']),'source_discrepancies':len(value['discrepancies']),
        'original_task_complete':False}


def main():
    tick=time.monotonic()
    output=TEMP/'reference-closure-065.json.gz'
    require(not output.exists(),'Preserve completed diagnostic; no unchanged retry')
    auth=common.authority()
    require(read(AUTH/'program.json')['revision']==428,'Expected revision428')
    require(any(e.get('attempt')==rel(previous.repair.HERE) and
        e.get('outputs_sha256')==sha(previous.repair.HERE/'outputs.json') for e in auth.events()),'Recorded065 required')
    inventory=read(STATE)
    for key in ('method','source_review','original_graph','actual_ordinary','actual_installed'):
        require(sha(ROOT/inventory[key]['path'])==inventory[key]['sha256'],'Changed prior diagnostic binding')
    answer=previous.repair.checked_answer('ordinary')
    require(answer==previous.repair.checked_answer('installed'),'Ordinary/installed baseline mismatch')
    production=common.production()
    require(production==read(previous.repair.PREP/'freeze.json')['production'],'Changed baseline production')
    graph=read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']
    units={u['id']:u for u in graph['units']}
    require(len(units)==len(graph['units']),'Duplicate source identity')
    snapshot=read(SNAPSHOT)
    require(sha(ROOT/snapshot['original_graph']['path'])==snapshot['original_graph']['sha256'],'Changed direct-reference source')
    value=build(units,answer,inventory,snapshot)
    checks=compare_map(value,build(units,answer,inventory,snapshot))
    controls=[]
    changes={
        'wrong-target':lambda b:b['references'][0].update(destinations=['12']),
        'shifted-boundary':lambda b:b['registry'][0].update(end_exclusive=b['registry'][2]['heading']),
        'lost-plural-target':lambda b:next(r for r in b['references'] if r['id'].endswith(':p103:l60'))['destinations'].pop(),
        'lost-second-note-token':lambda b:next(r for r in b['references'] if r['id'].endswith(':p107:l70'))['destinations'].pop(),
        'shifted-split-source':lambda b:next(r for r in b['references'] if r['id'].endswith(':p95:l19'))['sources'].pop(),
        'changed-history':lambda b:b['historical_states'][0]['historical_flag'].update(value=True),
        'invented-reconciliation':lambda b:b['limits'].update(financial_reconciliation_established=True),
        'topical-as-explicit':lambda b:next(r for r in b['historical_states'] if r['id']=='judgments-tax-pension').update(association_kind='EXPLICIT_NUMBERED_REFERENCE'),
        'suppressed-source-discrepancy':lambda b:b['discrepancies'].pop(),
    }
    for name,change in changes.items():
        bad=deepcopy(value)
        change(bad)
        try:
            compare_map(bad,value)
        except ValueError as exc:
            controls.append({'case':name,'refused':True,'reason':str(exc)})
        else:
            raise ValueError('Accepted corruption '+name)
    require(common.production()==production,'Diagnostic changed production')
    result={'status':'FINITE_REFERENCE_ADDRESSES_AND_CURRENT_STATES_REVIEWED','plan':PLAN,
        'method':common.ref(__file__),'source_review':common.ref(TEMP/'SOURCE-REVIEW.md'),
        'baseline_audit':common.ref(STATE),'direct_reference_snapshot':common.ref(SNAPSHOT),
        'original_graph':common.ref(BASE/'attempt-007/products.json.gz'),
        'actual_answer':common.ref(previous.repair.OLD_HERE/'ordinary-answer.json.gz'),
        'map':value,'checks':checks,'adverse_controls':controls,'production_changed':False,
        'seconds':time.monotonic()-tick,'original_task_complete':False}
    require(len(common.encoded(result))<8*1024**2,'Diagnostic exceeds8MiB reservation')
    save(output,result)
    return {'status':result['status'],**checks,'adverse_controls':len(controls),
        'seconds':result['seconds'],'bytes':output.stat().st_size,'output':rel(output)}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    started=time.monotonic()
    try:
        print(json.dumps(main()),flush=True)
    except Exception as exc:
        failure=TEMP/'diagnostic-failure.json'
        if not failure.exists():
            save(failure,{'status':'FAIL','method':common.ref(__file__),
                'error':type(exc).__name__+': '+str(exc),'seconds':time.monotonic()-started})
        raise
