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
from .model import FactName,ModelId,OutputId,Parameter,TypeDefinition,Bound,from_reading,blockers,fail


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


class OutputSignature(Strict):
    id: OutputId
    result_type: Text


class OutputExpression(OutputSignature):
    scope: Text
    result: Text


class HelperExpression(Strict):
    name: ModelId
    parameters: list[Parameter] = Field(max_length=20)
    result_type: Text
    body: Text


class FormalizationV2(Strict):
    version: Literal['2']
    facts: list[SharedFact] = Field(max_length=40)
    types: list[TypeDefinition] = Field(max_length=30)
    helpers: list[HelperExpression] = Field(max_length=20)
    outputs: list[OutputExpression] = Field(min_length=1,max_length=40)


class ReadingV2(Reading):
    formalization: FormalizationV2 | None


class GenerationV2(Generation):
    readings: list[ReadingV2] = Field(min_length=1,max_length=4)


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


class TaskV2(Strict):
    record_type: Literal['RuleInterpretationTask']
    version: Literal['2']
    task_id: Id
    packet: Packet
    question: Text
    facts: list[SharedFact] = Field(min_length=1,max_length=40)
    types: list[TypeDefinition] = Field(max_length=30)
    outputs: list[OutputSignature] = Field(min_length=1,max_length=40)
    profile: Literal['complete.v1','partial.v1']
    bounds: list[Bound] = Field(default_factory=list,max_length=40)
    valid_from: str
    valid_until: str | None


def parse_task(task):
    t=parse(TaskV2 if task.get('version')=='2' else Task,task)
    if 'outputs' in t and len({o['id'] for o in t['outputs']})!=len(t['outputs']): fail('E_DUPLICATE_ID')
    return t


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

V2_GRAMMAR = '''Version 2 formalization contains version, facts, types, helpers and outputs.
Return each fixed output id/result_type with scope and result expressions. Helpers
are pure typed calculations with name, parameters, result_type and body; they may
use only their parameters and other acyclic helpers, never hidden facts or rules.
Additional syntax: (call HELPER ARG ...), (rule OUTPUT_ID),
(record TYPE (FIELD EXPR) ...), (scale VALUE INTEGER_NUMERATOR POSITIVE_DENOMINATOR),
(round integer|money_hkd toward_zero|floor|ceiling|nearest_away EXACT_DECIMAL),
(default BASE (exception ID BOOLEAN_GUARD CONSEQUENCE) ...),
(library OP ARG ...). OP is numeric.min, numeric.max, date.add_days,
date.add_months_clamped, date.month_end, list.length or list.sequence.
Sequence includes begin and excludes end (at most 10000 items). Month addition
clamps to the last valid day. Money and rounding inputs use minor units. Scale is
exact and errors if indivisible; rounding must be expressly justified by source.
Scope runs before the body. Default tests all guards: multiple true guards
conflict even for equal consequences; otherwise an unknown guard prevents a
choice. Only the selected consequence executes. The partial.v1 profile uses
evaluated dependencies, strong Kleene booleans, and per-field/item observations.
Missing optional evidence is not known absence; incomplete collection membership
is not a complete observed subset. Complete.v1 still requires all declared inputs.
Do not invent a helper, exception, rounding mode, output or policy from a target
language feature. Cite the source meaning and preserve unresolved questions.'''


def request(task, previous=None, feedback=None):
    t=parse_task(task)
    r=generation_request(t['packet'],'normative',parent=previous,diagnostics=feedback or [])
    r.update(protocol='legalmath.interpretation.shared.v1', selected_question=t['question'],
             factual_interface=t['facts'],type_definitions=t['types'],
             semantic_profile=t['profile'],declared_bounds=t['bounds'])
    r['instructions']=r['instructions'].replace('Use null formalization if a requirement cannot be represented in this fragment.',
        'Use null formalization if a requirement cannot be represented by the supplied shared expression grammar.')+'\n'+EXTRA_GRAMMAR
    if t.get('version')=='2':
        r.update(protocol='legalmath.interpretation.shared.v2',outputs=t['outputs'])
        r['instructions']+='\n'+V2_GRAMMAR
    else: r['result_type']=t['result_type']
    return r


def validate_generation(value, task):
    t=parse_task(task);schema=GenerationV2 if t.get('version')=='2' else SharedGeneration
    g=validate_generation_metadata(parse(schema,value),t['packet'])
    for r in g['readings']:
        f=r['formalization']
        if f is None: continue
        outputs_match=([{k:o[k] for k in ('id','result_type')} for o in f['outputs']]==t['outputs']
                       if t.get('version')=='2' else f['result_type']==t['result_type'])
        if f['facts']!=t['facts'] or f['types']!=t['types'] or not outputs_match:
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
    t=parse_task(task);out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
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
                schema=GenerationV2 if t.get('version')=='2' else SharedGeneration
                value=call(label+'.generation',request(t,previous,feedback),schema.model_json_schema())
                try: generation=validate_generation(value,t)
                except LegalMathError as error:
                    feedback=[{'code':error.code,'details':error.details}];save(label+'.failure.json',feedback);continue
                previous=generation
                criticism=call(label+'.criticism',{'protocol':'legalmath.interpretation.shared.v'+t.get('version','1'),'task':'REVIEW',
                    'source_packet':t['packet'],'question':t['question'],'generation':generation,'interpretation_task':t,
                    'semantic_profile':t['profile'],
                    'instructions':'Assess legal scope, definitions, conditions, exceptions, dates, units and unresolved dependencies against retained text. Check the shared formal meaning and all proposed readings. Preserve real ambiguity. SUPPORTED means no identified mismatch under the declared assumptions; it is provisional model criticism, never legal or release approval. Return CHALLENGED for a specific repair, UNRESOLVED for a material unanswered question.'
                    + ('\nReview every output and helper, scope, exception overlap, rounding location/mode, library domain and partial-evidence assumption.\n'+V2_GRAMMAR if t.get('version')=='2' else '')},Criticism.model_json_schema())
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
