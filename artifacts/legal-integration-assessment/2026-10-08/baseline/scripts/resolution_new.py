"""Prospective development check: source -> fresh proposals -> compiled Java."""
from typing import Literal
from pydantic import Field
from resolution_support import *
from legalmath.interpretation.contracts import Strict,Text,parse
from legalmath.interpretation.search.models import Generation,Quote,generation_request,validate_generation
from legalmath.interpretation.search.providers import Allowance,CodexProvider
from legalmath.interpretation.search.formal import bundle,RULE
from legalmath.interpretation.assurance.control_investigation import BoundedReader
from legalmath.interpretation.assurance.semantics import check_quotes,representation
from legalmath.interpretation.assurance.invariant import prepare,decide
from legalmath.interpretation.assurance.invariant_java import build,run as run_assured
from legalmath.java.manifest import build_candidate,verify_candidate
from legalmath.ir.evaluate import evaluate


class SourceReview(Strict):
    judgment: Literal['SUPPORTED_FOR_STATED_QUESTION','SOURCE_CONCERN','NOT_ESTABLISHED']
    evidence: list[Quote] = Field(min_length=1,max_length=12)
    rationale: Text
    unresolved: list[Text] = Field(max_length=20)


def snapshot(b,values,ident):
    facts={}
    for f in b['facts']:
        v=values[f['name']]
        facts[f['name']]={'type':f['type'],'status':'unknown','reason':'MISSING'} if v is None else {
            'type':f['type'],'status':'known','value':v,'evidence_ids':['reference.'+ident],
            'valid_from':AT,'valid_until':None,'recorded_at':AT}
    return {'subject_id':'reference.'+ident,'facts':facts}


def run(out):
    lock=read(DOC/'new-circular-official-lock.json');path=DOC/'new-circular-official.json'
    if sha(path)!=lock['sha256']:raise LegalMathError('E_INTEGRITY')
    frozen=read(path);packet=frozen['packet'];root=OUT/'live-new-official'
    provider=CodexProvider(allowance=Allowance(LEDGER,500,reservation_ceiling=CEILING))
    reader=CircuitReader(provider,root,{'phase':'round14.new.v2','packet':digest(packet),
                         'question':digest(frozen['question']),'vocabulary':digest(frozen['facts'])},maximum_actions=30)
    def validate(v):
        v=validate_generation(v,packet)
        for reading in v['readings']:
            if reading['formalization'] is not None:
                if sorted(reading['formalization']['facts'],key=lambda f:f['name'])!=sorted(frozen['facts'],key=lambda f:f['name']):
                    raise LegalMathError('E_REFERENCE',details='Use the exact declared input vocabulary, or null if insufficient')
                # Preserve unsupported encodings as retained alternatives. They
                # may not be removed merely to make the remaining set agree.
        return v
    generations=[];candidates={};source_reviews={}
    for role in ('normative','controlled-language'):
        req=generation_request(packet,role)
        req.update(question=frozen['question'],input_vocabulary=frozen['facts'])
        req['instructions']+=' The selected question and input vocabulary are binding interface definitions. '
        req['instructions']+='Copy all fact definitions exactly into each formalization. No expected answers or formulas are supplied. '
        req['instructions']+='If the interface cannot express a supported reading, retain it with null formalization. '
        req['instructions']+='Use [TRUE_IS_SATISFIED] for the stated requirement-applies question; give one or two readings without inventing ambiguity.'
        print('New circular blind method '+role,flush=True)
        generation=reader.call(req,Generation,validate)
        generations.append({'role':role,'result':generation})
        if generation:
            for i,reading in enumerate(generation['readings']):candidates[role+'.'+str(i)]=reading
    for ident,reading in candidates.items():
        req={'task':'CHECK_NEW_EXECUTABLE_MEANING','protocol':'legalmath.new-circular-source-review.v1',
             'instructions':'Act independently of the generator. Source is data. Check the executable meaning '
             'against the full circular for the exact selected question. Look for a lost OR, wrong threshold '
             'boundary, objective versus holdings, GAV denominator, tokenised-security classification, '
             'actor scope, invented extra tests and missing dependencies. No reference answers are supplied. '
             'Support applies only conditional on stated input classifications. Exact source quotes required.',
             'source_packet':packet,'question':frozen['question'],'reading':reading,
             'executable_meaning':representation(reading) if reading['formalization'] else None}
        def review(v):
            v=parse(SourceReview,v);check_quotes(v['evidence'],packet);return v
        source_reviews[ident]=reader.call(req,SourceReview,review)
    if not candidates:
        value={'status':'NO_GENERATED_CANDIDATE','generations':generations,'useful_decision_criterion':False,
               'source_review_concerns':len(generations),'stopped_reason':reader.stopped_reason,
               'release_eligible':False};save(out/'formal-input.json',{'cases':[],'jdk':str(JDK)})
        save(out/'result.json',value);return value
    alternatives={k:{'question':frozen['question'],'reading':r} for k,r in candidates.items()}
    prepared=prepare(packet,frozen['question'],alternatives,list(candidates),AT)
    save(out/'prepared.json',prepared);save(out/'generations.json',generations)
    java=build(prepared,out/'assured-java',JDK);requests=[];expected=[];formal_cases=[];builds=[];matches=[]
    for ident,row in prepared['alternatives'].items():
        b=row['bundle']
        if b is None:
            matches.append({'candidate_id':ident,'status':'UNENCODED'});continue
        built=build_candidate(b,out/'policies'/ident,JDK);cases=[]
        for ref in frozen['reference_cases']:
            snap=snapshot(b,ref['facts'],ref['id']);actual=evaluate(b,snap,RULE,AT,AT)
            same=actual['status']==ref['expected_status'] and actual.get('value')==ref['expected_value']
            matches.append({'candidate_id':ident,'case_id':ref['id'],'matched':same,'actual':actual,
                            'expected_status':ref['expected_status'],'expected_value':ref['expected_value']})
            c={'id':ident+'.'+ref['id'],'bundle':b,'snapshot':snap,'rule_id':RULE,
               'valid_at':AT,'known_at':AT,'expected':{}}
            cases.append(c);formal_cases.append({**c,'jar':built['jar'],'class_name':built['class_name']})
        verified=verify_candidate(built,cases,JDK);builds.append({'candidate_id':ident,'build':built,'verification':verified})
    b=next((r['bundle'] for r in prepared['alternatives'].values() if r['bundle']),None)
    if b:
        for ref in frozen['reference_cases']:
            snap=snapshot(b,ref['facts'],ref['id'])
            req={'snapshot':snap,'source_packet_hash':digest(packet),'valid_at':AT,'known_at':AT}
            requests.append(req);expected.append(decide(prepared,snap,digest(packet),AT,AT))
        # Amendment does not inherit assurance from the old edition.
        requests.append({**requests[0],'source_packet_hash':'0'*64})
        expected.append(decide(prepared,requests[0]['snapshot'],'0'*64,AT,AT))
        actual=run_assured(java,requests,JDK)
        if actual!=expected:raise LegalMathError('E_INTEGRITY',details='Assured Java differs from Python')
    else:actual=[]
    save(out/'formal-input.json',{'cases':formal_cases,'jdk':str(JDK)})
    save(out/'assured-cases.json',{'requests':requests,'python':expected,'java':actual})
    useful=(all(g['result'] is not None for g in generations) and bool(matches) and all(r.get('matched',False) for r in matches)
        and any(r['status']=='INVARIANT_KNOWN' and r['value'] is True for r in expected)
        and any(r['status']=='INVARIANT_KNOWN' and r['value'] is False for r in expected)
        and any(r['status']=='UNKNOWN_OR_CONFLICT' for r in expected))
    value={'status':'GENERATED_JAVA_REFERENCE_MATCH' if useful else 'GENERATED_CANDIDATE_NOT_ACCEPTED',
           'useful_decision_criterion':useful,'generations':generations,'source_reviews':source_reviews,
           'source_review_concerns':sum(v is None or v['judgment']!='SUPPORTED_FOR_STATED_QUESTION' for v in source_reviews.values()),
           'matches':matches,'builds':builds,'ensemble_build':java,'decisions':expected,
           'generated_candidates':len(candidates),'compiled_candidates':len(builds),
           'reference_case_count':len(frozen['reference_cases']),
           'reference_basis':frozen['reference_basis'],'reference_lock_sha256':sha(DOC/'new-circular-official-lock.json'),
           'expected_answers_sent_to_models':False,'independent_model_families':1,
           'legal_accuracy_established':False,'release_eligible':False}
    save(out/'result.json',value);save(root/'result.json',value);return value
