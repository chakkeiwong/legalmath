"""Source-first preparation for a same-task explicit-section scope check."""
from copy import deepcopy
import json
import sys

from scripts import prospectus_definition_declarations_trial as previous
from scripts.prospectus_definition_declarations_run import costs as prior_costs

ROOT, AUTH = previous.ROOT, previous.AUTH
PREP = AUTH / 'reviews/explicit-definition-scope-358'
HERE = AUTH / 'attempts/basf-references/attempt-097'
PLAN = 'docs/plans/prospectus-explicit-definition-scope-2026-10-20.md'
METHOD = 'scripts/prospectus_explicit_scope_trial.py'
TARGETS = tuple('src/legalmath/prospectus/successor/' + name for name in
                ('definition_scope_evidence.py', 'definition_applications.py', 'service.py'))
SECONDS_BOUND, BYTES_BOUND = 27000, 4096 * 1024**2
read, save, rel, sha, digest = previous.read, previous.save, previous.rel, previous.sha, previous.digest


def fixture(text, ident='example'):
    pieces, pos = [], 0
    for line in text.splitlines(keepends=True):
        raw = line.rstrip('\n')
        unit = ident + ':' + str(len(pieces))
        binding = {'unit':unit, 'document':ident, 'source_sha256':digest(ident.encode()),
                   'start':0, 'end':len(raw), 'quote':raw}
        use = {'unit':unit, 'start':0, 'end':len(raw), 'source':deepcopy(binding),
               'role':'HEADER' if raw.startswith('§ ') else 'OPERATIVE', 'context':ident}
        if raw:
            pieces.append({'start':pos,'end':pos+len(raw),'text':raw,
                'kind':'EXACT_SOURCE_COPY','raw_binding':binding,'assembly_uses':[use]})
        pos += len(raw)
        if line.endswith('\n'):
            pieces.append({'start':pos,'end':pos+1,'text':'\n','kind':'GENERATED_SEPARATOR',
                           'raw_binding':None,'assembly_uses':[]})
            pos += 1
    assert pos == len(text)
    return {'version':'definition-scope-evidence-request.v1','text':text,
            'text_sha256':digest(text.encode()),'source_pieces':pieces,'rules':[]}


def cases():
    text = '§ 37\nTEXT\nFür die Zwecke dieses § 37 bedeutet "Linde" ein Unternehmen.\n§ 38\nENDE'
    req = fixture(text)
    start = text.index('Für die Zwecke')
    base = {'id':'independent-number','request':req,'expected':[
        {'start':start,'end':start+len('Für die Zwecke dieses § 37'),'status':'EXPLICIT_SECTION',
         'extent':[0,text.index('§ 38')],'section':'37'}]}
    output = [base]
    for ident, phrase in [('deictic','Für diese Zwecke'),('contract','Für die Zwecke dieser Anleihebedingungen'),
                          ('option','Für Zwecke dieses Wahlrechts'),('foregoing','Für die Zwecke des Vorstehenden')]:
        value = '§ 37\n' + phrase + ' bedeutet "Linde" ein Unternehmen.\n§ 38\nENDE'
        a = value.index(phrase)
        output.append({'id':ident,'request':fixture(value,ident),'expected':[
            {'start':a,'end':a+len(phrase),'status':'REVIEW_REQUIRED','extent':None,'section':None}]})
    return {'candidate_derived':False,'cases':output}


def line_oracle(text):
    """Independent literal-line inventory; never call candidate boundary code."""
    result, position = [], 0
    for line in text.splitlines(keepends=True):
        raw = line.rstrip('\r\n')
        words = raw.split()
        if len(words) == 2 and words[0] == '§' and words[1].isascii() and words[1].isdigit():
            result.append({'section': words[1], 'start': position, 'end': position + len(raw), 'raw': raw})
        position += len(line)
    assert position == len(text)
    return result


def prepare():
    assert not PREP.exists() and not HERE.exists()
    program = read(AUTH/'program.json'); assert program['revision']==357
    events = previous.old.old.Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==96
    old = AUTH/'attempts/basf-references/attempt-096'
    for name, checksum in read(old/'outputs.json').items(): assert sha(old/name)==checksum
    prior = prior_costs()
    assert prior['combined_accounted_seconds'] + 1020 < SECONDS_BOUND
    assert prior['combined_bytes'] + 128*1024**2 < BYTES_BOUND - 4*1024**2
    baseline = AUTH/'attempts/basf-references/attempt-093/ordinary-answer.json.gz'
    answer = read(baseline); text=(AUTH/'attempts/basf-references/attempt-026/selected-text.txt').read_text()
    assert len(answer['definition_remainder_review']['uses'])==612
    assert len(answer['definition_sources']['records'])==62
    report = answer['definition_sources']
    rules = report['application_supplement']['rules']
    assert rules[3]['id']=='affiliate' and rules[3]['extents']==[[32176,34657]]
    assert text[32176:32180]=='§ 10' and text[34657:34661]=='§ 11'
    assert text[34003:34029]=='Für die Zwecke dieses § 10'
    labels = line_oracle(text)
    section = next(i for i, row in enumerate(labels) if row['section'] == '10')
    assert [labels[section]['start'], labels[section + 1]['start']] == [32176, 34657]
    request = {'version':'definition-scope-evidence-request.v1','text':text,
               'text_sha256':digest(text.encode()),'source_pieces':report['source_pieces'],'rules':rules}
    expected = []
    for r in read(previous.PREP/'expected.json')['restrictions']:
        explicit = r['start']==34003
        expected.append({**{k:v for k,v in r.items() if k!='raw'},
            'status':'EXPLICIT_SECTION' if explicit else 'REVIEW_REQUIRED',
            'extent':[32176,34657] if explicit else None,'section':'10' if explicit else None})
    PREP.mkdir(parents=True)
    save(PREP/'accounting-start.json',{'prior':prior,'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    save(PREP/'request.json',request)
    save(PREP/'expected.json',{'candidate_derived':False,'restrictions':expected,'checked_rules':['affiliate'],
                             'records':62,'associations':612,'all_other_restrictions_unresolved':True})
    save(PREP/'independent-cases.json',cases())
    save(PREP/'line-oracle.json', {'candidate_derived': False, 'labels': labels,
         'explicit_extent': [labels[section]['start'], labels[section + 1]['start']]})
    for name in TARGETS[1:]:
        target = PREP/'baseline'/name.split('/')[-1]; target.parent.mkdir(exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    profiles = AUTH/'reviews/bgb-onward-integration-354/profiles.json'
    products = AUTH/'reviews/conditional-cli-311/products.json'
    paths = [PREP/n for n in ('request.json','expected.json','independent-cases.json','line-oracle.json',
                             'baseline/definition_applications.py','baseline/service.py')]
    paths += [baseline,profiles,products,old/'outputs.json',ROOT/PLAN,ROOT/METHOD]
    bindings = {rel(p):sha(p) for p in paths}
    for row in read(products)['products'].values(): bindings[row['path']]=row['sha256']
    save(PREP/'source-freeze.json',{'bindings':bindings,'candidate_executed':False,
         'full_answer_baseline':rel(baseline),'profiles':rel(profiles),'products':rel(products)})
    proposal = deepcopy(program); proposal['revision']=358
    task = next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=PLAN,
        reason='Independently verify explicit section scope against supplied application extent through the real consumer',
        explicit_definition_scope_review={'review':rel(PREP),'original_task_complete':False,
            'accounted_seconds_bound':SECONDS_BOUND,'bytes_bound_with_4MiB_reserve':BYTES_BOUND})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'source-freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=97
    routes = read(ROOT/program['continuation_review']['routes']); routes['baseline_revision']=358
    for row in routes['tasks']:
        if row['task']=='basf-references':
            row.update(task_sha256=previous.old.old.authority_digest(task),dossier=PLAN,
                remaining='096 exact naming syntax is recorded; supplied explicit-section extents lack independent normal-consumer checks',
                next_action='Derive exact printed self-section scope, refuse conflicting application extents, preserve full original answer, then remaining original acceptance',
                stop_condition='97cumulative admissions;900new command seconds/128MiB;27000seconds/4096MiB cumulative;4MiB reserve;no unchanged formal retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for name in TARGETS: proposal['continuation_review']['bindings'].pop(name,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),
                                                     rel(PREP/'source-freeze.json'):sha(PREP/'source-freeze.json')})
    review = {'baseline':previous.old.old.authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Derive explicit printed section extent without supplied destination','Guard real conditional applications and preserve whole answer'],
        'skeptical_audit':{'verdict':'PASS','review':PLAN,
            'baseline':'Sealed093complete answer/026source/096syntax; existing five purpose rules retained',
            'pre_mortem':'A side inventory cannot suffice; require real consumer check, conflicting extent refusal and complete answer equality'},
        'evidence_contract':{'primary':'Independent finite scope expectations, adverse extent/source controls, full actual ordinary/installed equality',
            'promotion_veto':['Guessed scope','Lost premise','Source/context drift','Expected extent leakage','Installed checkout import'],
            'continuation_veto':['Frozen corruption','Unreviewed drift','Cumulative exhaustion'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Legal truth','Unrestricted recall','Original task or build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':96,'new_maximum':97,'retained_attempts':attempts,
            'reason':'Existing supplied section extent is not independently checked against printed restriction and source boundary',
            'next_discriminating_check':'Actual consumer refuses conflicting extent while complete valid answer remains unchanged',
            'stop_condition':'900new command seconds/128MiB;27000seconds/4096MiB cumulative;no unchanged retry',
            'same_scope_authorization':'User directed refreshed internally supported general build and continued execution'},
        'resource_accounting':{'retained_costs':prior,'limits_extended':False,
            'additional_conservative_authoring_charge_seconds':120,'older_unmeasured_time':'UNKNOWN'}}
    save(PREP/'proposal.json',proposal); save(PREP/'review.json',review)
    return {'status':'PASS','revision':358,'candidate_executed':False,'scope':'EXPLICIT_SELF_SECTION_CONSISTENCY',
            'records':62,'associations':612,'prior':prior}


if __name__=='__main__':
    assert sys.argv[1:]==['prepare']
    print(json.dumps(prepare()))
