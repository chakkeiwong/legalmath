"""One source interpretation workflow; target selection happens after this module."""
from dataclasses import dataclass
import fcntl
from pathlib import Path
from typing import Literal
from pydantic import Field
from ..canonical import canonical,digest,loads,raw_digest
from ..errors import LegalMathError
from ..interpretation.contracts import Strict,Id,Text,Packet,parse
from ..interpretation.search.models import (FactDefinition, Formalization, Reading, Generation,
    GRAMMAR, generation_request, validate_generation_metadata)
from .model import FactName,TypeDefinition,Bound,from_reading,blockers,fail


class SharedFact(FactDefinition):
    name: FactName
    type: Text


class SharedFormalization(Formalization):
    facts: list[SharedFact] = Field(max_length=40)
    types: list[TypeDefinition] = Field(max_length=30)
    result_type: Text


class SharedReading(Reading):
    formalization: SharedFormalization | None


class SharedGeneration(Generation):
    readings: list[SharedReading] = Field(min_length=1,max_length=4)


class Task(Strict):
    record_type: Literal['RuleInterpretationTask']
    task_id: Id
    packet: Packet
    question: Text
    facts: list[SharedFact] = Field(min_length=1,max_length=40)
    types: list[TypeDefinition] = Field(max_length=30)
    result_type: Text
    profile: Literal['ruleir.v1','complete.v1']
    bounds: list[Bound] = Field(default_factory=list, max_length=40)
    valid_from: str
    valid_until: str | None


class Criticism(Strict):
    verdict: Literal['SUPPORTED','CHALLENGED','UNRESOLVED']
    findings: list[Text] = Field(max_length=40)


@dataclass(frozen=True)
class Limits:
    timeout_seconds: int = 180
    max_input_bytes: int = 100000
    max_output_bytes: int = 100000


EXTRA_GRAMMAR = '''Use the supplied typed factual interface exactly, including meanings and source references.
Return types as supplied in formalization.types. This is a shared rule model, not target code.
Additional exact syntax: (decimal NUMERATOR DENOMINATOR), (* DECIMAL DECIMAL),
(field RECORD FIELD), (list ELEMENT_TYPE EXPR ...), (map VARIABLE LIST BODY),
(filter VARIABLE LIST BOOLEAN_BODY), (sum NUMERIC_LIST), (some VALUE), (none TYPE),
(option OPTIONAL VARIABLE PRESENT_BODY ABSENT_BODY),
(variant ENUM CASE PAYLOAD) or (variant ENUM NULLARY_CASE),
(match ENUM_VALUE (CASE VARIABLE BODY) (NULLARY_CASE _ BODY)).
Types include decimal, list[T], optional[T], and the supplied named records/enums.
Known optional absence differs from unavailable evidence. Exact money scaling retains
its declared policy; do not invent rounding. No source code, filenames or external calls.
Uncertainty must remain in questions; choosing an output language cannot resolve it.'''


def request(task, previous=None, feedback=None):
    t=parse(Task,task)
    r=generation_request(t['packet'],'normative',parent=previous,diagnostics=feedback or [])
    r.update(protocol='legalmath.interpretation.shared.v1', selected_question=t['question'],
             factual_interface=t['facts'],type_definitions=t['types'],result_type=t['result_type'],
             semantic_profile=t['profile'],declared_bounds=t['bounds'])
    r['instructions']=r['instructions'].replace('Use null formalization if a requirement cannot be represented in this fragment.',
        'Use null formalization if a requirement cannot be represented by the supplied shared expression grammar.')+'\n'+EXTRA_GRAMMAR
    return r


def validate_generation(value, task):
    t=parse(Task,task);g=validate_generation_metadata(parse(SharedGeneration,value),t['packet'])
    for r in g['readings']:
        f=r['formalization']
        if f is None: continue
        if f['facts']!=t['facts'] or f['types']!=t['types'] or f['result_type']!=t['result_type']:
            fail('E_TYPE','Interpretation changed the fixed factual interface')
        from_reading(r,t['packet'],t['valid_from'],until=t['valid_until'],profile=t['profile'],
                     coverage=g['coverage'],dimensions=g['dimensions'],questions=g['questions'],bounds=t['bounds'])
    return g


def implementation_hash():
    paths=sorted(Path(__file__).parent.glob('*.py'))
    paths.append(Path(__file__).parents[1]/'interpretation/search/models.py')
    return digest({str(p.relative_to(Path(__file__).parents[1])):raw_digest(p.read_bytes()) for p in paths})


def interpret(task, output, provider, *, resume=False, max_revisions=1):
    if max_revisions not in (0,1): fail('E_RESOURCE_LIMIT')
    t=parse(Task,task);out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    context={'task_hash':digest(t),'implementation_hash':implementation_hash(),'provider_id':provider.provider_id,
             'route':getattr(provider,'routing',None),'limits':Limits().__dict__,'max_revisions':max_revisions}
    def write(name,v):
        path=out/name;temp=path.with_suffix(path.suffix+'.tmp');temp.write_bytes(canonical(v));temp.replace(path)
    with (out/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        statefile=out/'state.json'
        if statefile.exists():
            if not resume: fail('E_JOB_STATE','Existing interpretation requires resume')
            state=loads(statefile.read_bytes())
            if state['context']!=context: fail('E_STALE_REVIEW')
            for name,h in state['files'].items():
                if digest(loads((out/name).read_bytes()))!=h: fail('E_HASH_MISMATCH')
            if state['status']!='RUNNING': return state
        else:
            if resume: fail('E_NOT_FOUND')
            state={'record_type':'SharedInterpretationRun','context':context,'status':'RUNNING','files':{},'calls':[],'models':[]}
            write('state.json',state)
        def save(name,v):
            write(name,v);state['files'][name]=digest(v);write('state.json',state)
        save('task.json',t)
        def call(label,r,schema):
            req,res=label+'.request.json',label+'.response.json'
            if req in state['files'] and loads((out/req).read_bytes())!={'request':r,'schema':schema}: fail('E_INTEGRITY')
            if res in state['files']: return loads((out/res).read_bytes())['value']
            if label in state['calls']: fail('E_JOB_STATE','Interrupted dispatch remains counted')
            save(req,{'request':r,'schema':schema});state['calls'].append(label);write('state.json',state)
            c=provider.complete(r,schema,Limits());save(res,{'value':c.value,'provenance':c.provenance});return c.value
        previous=None;feedback=[]
        try:
            for attempt in range(max_revisions+1):
                label='attempt-'+str(attempt)
                value=call(label+'.generation',request(t,previous,feedback),SharedGeneration.model_json_schema())
                try: generation=validate_generation(value,t)
                except LegalMathError as error:
                    feedback=[{'code':error.code,'details':error.details}];save(label+'.failure.json',feedback);continue
                previous=generation
                criticism=call(label+'.criticism',{'protocol':'legalmath.interpretation.shared.v1','task':'REVIEW',
                    'source_packet':t['packet'],'question':t['question'],'generation':generation,'interpretation_task':t,
                    'semantic_profile':t['profile'],
                    'instructions':'Assess legal scope, definitions, conditions, exceptions, dates, units and unresolved dependencies against retained text. Check the shared formal meaning and all proposed readings. Preserve real ambiguity. SUPPORTED means no identified mismatch under the declared assumptions; it is provisional model criticism, never legal or release approval. Return CHALLENGED for a specific repair, UNRESOLVED for a material unanswered question.'},Criticism.model_json_schema())
                criticism=parse(Criticism,criticism);save(label+'.review.json',criticism)
                if criticism['verdict']=='CHALLENGED' and attempt<max_revisions:
                    feedback=[criticism];continue
                state['models']=[];unrepresented=[]
                for reading in generation['readings']:
                    if reading['formalization'] is None:
                        unrepresented.append(reading['local_id']);continue
                    model=from_reading(reading,t['packet'],t['valid_from'],until=t['valid_until'],profile=t['profile'],
                                       coverage=generation['coverage'],dimensions=generation['dimensions'],questions=generation['questions'],critic=criticism,bounds=t['bounds'])
                    name='model-'+digest(model)+'.json';save(name,model)
                    state['models'].append({'reading_id':reading['local_id'],'model_hash':digest(model),'path':name,'unresolved':blockers(model)})
                state.update(status='INTERPRETED',unrepresented_readings=unrepresented,source_review=criticism)
                break
            else: state['status']='REJECTED'
        except LegalMathError as error:
            state.update(status='STOPPED',failure={'code':error.code,'details':error.details})
        write('state.json',state)
        return state
