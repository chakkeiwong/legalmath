"""Independent source preparation for the same BASF definition task."""
from copy import deepcopy
import sys
import json

from scripts import prospectus_reference_resolution_trial as old
from scripts.prospectus_reference_resolution_run import costs as prior_costs

ROOT, AUTH = old.ROOT, old.AUTH
PREP = AUTH / 'reviews/definition-declarations-357'
HERE = AUTH / 'attempts/basf-references/attempt-096'
PLAN = 'docs/plans/prospectus-definition-declarations-2026-10-20.md'
METHOD = 'scripts/prospectus_definition_declarations_trial.py'
TARGETS = ('src/legalmath/prospectus/successor/definition_declarations.py',
           'src/legalmath/prospectus/successor/service.py')
read, save, rel, sha = old.read, old.save, old.rel, old.sha
digest = old.old.digest
SECONDS_BOUND, BYTES_BOUND = 27000, 4096 * 1024**2

# Source-inspected exact tokens, not output from the new detector.
TOKEN_SPANS = [(1,271,292),(2,309,313),(2,325,335),(3,363,382),(4,538,560),
 (5,763,787),(6,952,970),(7,2732,2747),(8,2870,2873),(9,2956,2965),
 (10,3000,3004),(10,3024,3029),(11,3130,3133),(12,4860,4869),
 (13,6073,6100),(14,6802,6817),(15,7426,7442),(16,7570,7593),(17,8833,8837),
 (18,9716,9723),(19,9932,9938),(20,11354,11368),(21,11391,11409),
 (22,13649,13669),(23,14092,14105),(24,14166,14169),(25,14200,14207),
 (26,14246,14251),(27,14424,14445),(28,14918,14933),(29,15007,15030),
 (30,15506,15529),(31,15619,15634),(32,15864,15886),(33,16189,16206),
 (34,16369,16387),(35,19073,19112),(36,22369,22400),(37,22920,22947),
 (38,24544,24562),(39,25769,25789),(40,32492,32512),(41,34040,34063),
 (42,34924,34929),(43,39043,39054),(44,44239,44259),(45,45657,45666)]
TYPES = {**dict.fromkeys([7,12,13,15,18,23,36,38,41,45],'DEFINING_VERB'),
         **dict.fromkeys([27,28],'CONDITIONAL_EVENT_PREDICATE'),
         **dict.fromkeys([30,31,37],'COPULAR_PREDICATE'),
         10:'COORDINATED_NAMING',21:'EQUATING_PREDICATE',42:'DASH_NAMING'}
RESTRICTIONS = [(9687,'Für diese Zwecke'), (14052,'Für Zwecke dieses Wahlrechts'),
 (24491,'Für die Zwecke dieser Anleihebedingungen'), (34003,'Für die Zwecke dieses § 10'),
 (45613,'Für die Zwecke des Vorstehenden')]

def request_for(text, ident='fixture'):
    unit={'id':ident,'document':ident,'source_sha256':digest(ident.encode()),
          'raw':text,'text_sha256':digest(text.encode())}
    raw={'unit':ident,'document':ident,'source_sha256':unit['source_sha256'],
         'start':0,'end':len(text),'quote':text}
    return {'version':'definition-declaration-request.v1','language':'de',
        'source':{'version':'reference-mention-request.v1','text':text,
          'text_sha256':unit['text_sha256'],'raw_units':[unit],'section_headers':[],
          'source_pieces':[{'start':0,'end':len(text),'text':text,'kind':'EXACT_SOURCE_COPY','raw_binding':raw}]},
        'layout':[{'unit':ident,'context':ident,'role':'OPERATIVE'}]}

def independent_cases():
    rows=[
      ('alias','Die Nord AG (die "Gesellschaft") zahlt.', [('Gesellschaft','PARENTHETICAL_NAMING')]),
      ('two','Die Nord AG ("Nord" oder die "Ausstellerin") zahlt.', [('Nord','PARENTHETICAL_NAMING'),('Ausstellerin','PARENTHETICAL_NAMING')]),
      ('bare','Die Bank ("Kappa") handelt.', [('Kappa','PARENTHETICAL_NAMING')]),
      ('nested','Der Termin (jeweils ein "Tag (Put)") gilt.', [('Tag (Put)','PARENTHETICAL_NAMING')]),
      ('coordinated','(X und Y jeweils ein "Verwahrer" und zusammen die "Verwahrergruppe").', [('Verwahrer','COORDINATED_NAMING'),('Verwahrergruppe','COORDINATED_NAMING')]),
      ('dash','Das Mustergesetz (Mustergesetz – "MG") gilt.', [('MG','DASH_NAMING')]),
      ('verb','"Abrechnungstag" bedeutet den dritten Werktag.', [('Abrechnungstag','DEFINING_VERB')]),
      ('prefix','Für diese Zwecke bezeichnet "Banktag" einen Werktag.', [('Banktag','DEFINING_VERB')]),
      ('event','Gilt ein "Ausfall" als eingetreten, wenn die Zahlung fehlt.', [('Ausfall','CONDITIONAL_EVENT_PREDICATE')]),
      ('equating','Der "Betrag" in Bezug auf jede Urkunde entspricht dem Nennwert.', [('Betrag','EQUATING_PREDICATE')]),
      ('copula','"Termin" ist der dritte Werktag.', [('Termin','COPULAR_PREDICATE')]),
      ('copula-inverted','Ist der "Zeitraum" der Zeitraum bis zum Ende;', [('Zeitraum','COPULAR_PREDICATE')]),
      ('quoted-use','Der "Banktag" wird später geprüft.', [('Banktag',None)]),
      ('reference','Es gilt (siehe "Banktag").', [('Banktag',None)]),
      ('defined-elsewhere','Es gilt ("Banktag" wie oben definiert).', [('Banktag',None)]),
      ('negated','"Termin" bedeutet nicht den dritten Werktag.', [('Termin',None)]),
      ('negated-prefix','Nicht bezeichnet "Termin" den dritten Werktag.', [('Termin',None)]),
      ('question','Ist der "Termin" der dritte Werktag?', [('Termin',None)]),
      ('question-verb','Bedeutet "Termin" den dritten Werktag?', [('Termin',None)]),
      ('conditional','Wenn "Termin" den dritten Werktag bedeutet, gilt dies.', [('Termin',None)]),
      ('broken','"Termin bedeutet den dritten Werktag.', []),
      ('curly','„Termin“ bedeutet den dritten Werktag.', []),
      ('split','Der Tag (die "lange\nBezeichnung") gilt.'.replace(chr(92)+'n',chr(10)), [('lange'+chr(10)+'Bezeichnung','PARENTHETICAL_NAMING')]),
      ('empty','Die Bank ("") zahlt.', []),
      ('adjacent','"Termin". Bedeutet das etwas?', [('Termin',None)]),
    ]
    output=[]
    for ident,text,expected in rows:
        position=0; spans=[]
        for raw,syntax in expected:
            start=text.index(raw,position); position=start+len(raw)
            spans.append({'start':start,'end':position,'raw':raw,'syntax':syntax})
        output.append({'id':ident,'request':request_for(text,ident),'expected':spans,
                       'issue_required':ident in ('broken','curly','empty')})
    return {'candidate_derived':False,'cases':output}

def prepare():
    assert not PREP.exists() and not HERE.exists()
    program=read(AUTH/'program.json'); assert program['revision']==356
    events=old.old.Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==95
    previous=AUTH/'attempts/basf-references/attempt-095'
    assert [e['kind'] for e in events if e.get('attempt')==rel(previous)]==['ADMIT','RECORD']
    for name,checksum in read(previous/'outputs.json').items(): assert sha(previous/name)==checksum
    prior=prior_costs()
    assert prior['combined_accounted_seconds']+420<SECONDS_BOUND
    assert prior['combined_bytes']+128*1024**2<BYTES_BOUND-4*1024**2
    source=read(old.PREP/'request.json')
    request={**source,'version':'definition-declaration-request.v1','language':'de'}
    text=request['source']['text']
    original=read(AUTH/'attempts/basf-references/attempt-026/definition-dossier.json')
    answer_path=AUTH/'attempts/basf-references/attempt-093/ordinary-answer.json.gz'
    answer=read(answer_path); records=answer['definition_sources']['records']
    assert len(records)==62 and len(answer['definition_remainder_review']['uses'])==612
    expected=[]
    for number,a,b in TOKEN_SPANS:
        rec=original['records'][number-1]
        assert rec['id'].startswith('D'+str(number).zfill(2)+'-')
        assert text[a-1]=='"' and text[b]=='"'
        assert any(d['start']<=a<b<=d['end'] for d in rec['declarations'])
        assert ' '.join(text[a:b].split()) in [' '.join(f.split()) for f in rec['forms']]
        expected.append({'record':rec['id'],'start':a,'end':b,'raw':text[a:b],
            'syntax':TYPES.get(number,'PARENTHETICAL_NAMING'),
            'source_projection':old.old.project(request['source'],a,b)})
    assert len(expected)==47 and len({r['record'] for r in expected})==45
    lineage={'version':'reviewed-definition-lineage.v1','text_sha256':request['source']['text_sha256'],
        'source_answer_sha256':sha(answer_path),'records':[],
        'naming_tokens':[{k:v for k,v in r.items() if k not in ('syntax','source_projection')} for r in expected],
        'uses':answer['definition_remainder_review']['uses'],
        'dependencies':answer['definition_dependency_review']['records']}
    for row in records:
        lineage['records'].append({'id':row['id'],'kind':row['kind'],'forms':row['forms'],
            'original_record_sha256':digest(row),'reading':row['reading'],
            'declarations':[answer['definition_sources']['intervals'][i] for i in row['declarations']],
            'scope_alternatives':row['scope_alternatives'],
            'scope_admitted':row['scope_admitted'],'meaning_admitted':row['meaning_admitted']})
    restrictions=[]
    for start,raw in RESTRICTIONS:
        assert text[start:start+len(raw)]==raw
        restrictions.append({'start':start,'end':start+len(raw),'raw':raw})
    PREP.mkdir(parents=True)
    save(PREP/'accounting-start.json',{'prior':prior,'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size,
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    save(PREP/'request.json',request)
    save(PREP/'expected.json',{'candidate_derived':False,'tokens':expected,'restrictions':restrictions})
    save(PREP/'lineage.json',lineage)
    save(PREP/'independent-cases.json',independent_cases())
    (PREP/'baseline').mkdir(); (PREP/'baseline/service.py').write_bytes((ROOT/TARGETS[1]).read_bytes())
    paths=[PREP/n for n in ('request.json','expected.json','lineage.json','independent-cases.json','baseline/service.py')]
    paths += [answer_path,previous/'outputs.json',ROOT/PLAN,ROOT/METHOD]
    bindings={rel(p):sha(p) for p in paths}
    save(PREP/'source-freeze.json',{'bindings':bindings,'candidate_executed':False,'independent_exact_tokens':True})
    proposal=deepcopy(program); proposal['revision']=357
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=PLAN,
        reason='Distinguish source-only declaration syntax and refine exact naming tokens while preserving62records/612uses',
        definition_declaration_review={'review':rel(PREP),'original_task_complete':False,
            'accounted_seconds_bound':SECONDS_BOUND,'bytes_bound_with_4MiB_reserve':BYTES_BOUND})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'source-freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=96
    routes=read(ROOT/program['continuation_review']['routes']); routes['baseline_revision']=357
    for row in routes['tasks']:
        if row['task']=='basf-references':
            row.update(task_sha256=old.old.authority_digest(task),dossier=PLAN,
                remaining='095 resolution recorded;47quoted labels still lack exact declaration syntax and token lineage',
                next_action='Check47exact naming tokens against syntax; preserve62records/612uses; continue governing-scope/source work',
                stop_condition='96cumulative admissions;300new command seconds/128MiB;27000seconds/4096MiB cumulative with4MiB reserve;no unchanged retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for name in TARGETS: proposal['continuation_review']['bindings'].pop(name,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),
                                                     rel(PREP/'source-freeze.json'):sha(PREP/'source-freeze.json')})
    review={'baseline':old.old.authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Add source-only declaration syntax beyond quoted-label discovery','Bind independently inspected47tokens to45quoted records; retain62records/612associations and all premises'],
        'skeptical_audit':{'verdict':'PASS','review':PLAN,'baseline':'Sealed093current meanings/uses and095source/layout; no old-status repair',
            'pre_mortem':'Exact tokens required; syntax cannot establish legal meaning/scope; negative and cross-source controls'},
        'evidence_contract':{'primary':'Exact finite original/adverse syntax outcomes, complete provenance/lineage conservation and installed equality',
            'promotion_veto':['Oracle leakage','Guessed governing scope','Dropped premise','Transformed raw evidence','Installed checkout import'],
            'continuation_veto':['Frozen corruption','Unreviewed drift','Cumulative exhaustion'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Legal truth','Unrestricted recall','Build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':95,'new_maximum':96,'retained_attempts':attempts,
            'reason':'Exact declaration-token relation and source-only syntax are absent from lexical candidate discovery',
            'next_discriminating_check':'Independent47token expectations and adverse references with retained612associations',
            'stop_condition':'300new command seconds/128MiB;27000seconds/4096MiB cumulative;no unchanged retry',
            'same_scope_authorization':'User directed refresh and continued internally supported general build'},
        'resource_accounting':{'retained_costs':prior,'limits_extended':False,'additional_conservative_authoring_charge_seconds':120,'older_unmeasured_time':'UNKNOWN'}}
    save(PREP/'proposal.json',proposal); save(PREP/'review.json',review)
    return {'status':'PASS','revision':357,'tokens':47,'records':62,'associations':612,'candidate_executed':False}

if __name__=='__main__':
    assert sys.argv[1:]==['prepare']
    print(json.dumps(prepare()))
