"""Bounded public-source pilot plus paired unanimous-omission/clean-control checks."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
import json
from legalmath.canonical import canonical, loads, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import CodexProvider, Allowance, Completion
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.assurance.engine import Assurance, AssuranceSettings
from legalmath.interpretation.assurance.journal import JournalProvider, RetainedProvider
from legalmath.interpretation.assurance.semantics import Fidelity, fidelity_request, validate_fidelity, merge_inventories
from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
from legalmath.interpretation.assurance.monitor import save

ROOT=Path(__file__).resolve().parents[1]
AT='2026-09-23T00:00:00.000000Z'
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
INCREMENT_START=41
RESERVATION_CEILING=93


class IncrementCap:
    """Independent of per-run limits; failed calls count against the existing 100."""
    def __init__(self, provider, allowance, recovered=None):
        self.provider,self.allowance=provider,Path(allowance)
        self.provider_id,self.live,self.routing=provider.provider_id,provider.live,provider.routing
        self.recovered=None
        if recovered is not None:
            record=loads(Path(recovered).read_bytes())
            calls=loads(self.allowance.read_bytes())['calls']
            slots=[i+1 for i,c in enumerate(calls) if c['request_hash']==record['request_hash']]
            if (not slots or record['request_hash']!=digest(record['request'])
                    or record['response_hash']!=digest(record['response']) or record['contract_status']!='VALID_CONTRACT'):
                raise LegalMathError('E_INTEGRITY')
            self.recovered=(record,slots[-1],raw_digest(Path(recovered).read_bytes()))
    def complete(self,request,schema,settings):
        if self.recovered is not None:
            record,slot,record_hash=self.recovered
            if record['request']==request and record['schema']==schema:
                self.recovered=None
                return Completion(record['response'],{'provider':self.provider_id,
                    'evidence_class':'RECOVERED_PREVIOUSLY_COUNTED_LIVE_RESPONSE',
                    'allowance_slot':slot,'request_hash':record['request_hash'],
                    'response_hash':record['response_hash'],'recovery_record_hash':record_hash,
                    'events_jsonl':record['events_jsonl'],'origin':record['origin'],
                    'new_live_invocation':False})
        value=loads(self.allowance.read_bytes())
        if value['maximum']!=100 or len(value['calls'])>=RESERVATION_CEILING:
            raise LegalMathError('E_RESOURCE_LIMIT',details='Reviewed round3 increment cap reached (41 + 52)')
        return self.provider.complete(request,schema,settings)


class TaskReplay:
    """Route declared tasks to exact retained evidence; every member verifies its manifest."""
    def __init__(self, provider, allowance, plan):
        self.provider_id,self.live,self.routing=provider.provider_id,provider.live,provider.routing
        self.base=RetainedProvider(provider,ROOT/plan['directory'],allowance,
                                   new_tasks=plan['allowed_live_tasks'],exclude_tasks=plan['task_overrides'])
        self.overrides={task:RetainedProvider(provider,ROOT/path,allowance,new_tasks=())
                        for task,path in plan['task_overrides'].items()}

    def complete(self,request,schema,settings):
        task=request.get('original_task',request['task'])
        return self.overrides.get(task,self.base).complete(request,schema,settings)


def source(ref):
    return {'url':'https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo='+ref,
            'data':(ROOT/'.localresources/sfc'/f'{ref}.json').read_bytes(),'media_type':'application/json'}


def omission_challenge(directory,provider):
    """Known inserted defect, not a hand-authored gold interpretation of all law."""
    p=packet_from_context(acquire_context([source('23EC46')]),
        'Only the explicitly stated fee/charge-discount exception in paragraph 10; assess its representation, not all fund compliance.')
    unit=next(u for u in p['units'] if 'other than a discount of fees or charges' in u['text'])
    evidence=[{'unit_id':unit['unit_id'],'quote':'other than a discount of fees or charges'}]
    claim={'claim_id':'discount.exception','kind':'EXCEPTION','actor':'distributor','action':'offering gifts',
           'modality':'SHOULD_NOT','conditions':['When promoting a specific product or particular product type'],
           'exceptions':['A discount of fees or charges is excluded from the gift restriction'], 'temporal':[],
           'statement':'The stated gift restriction excludes a discount of fees or charges.',
           'relevance':'CONTROL','evidence':evidence,'uncertainty':[]}
    facts=[{'name':name,'type':'bool','meaning':meaning,'unit':'truth value','source_unit_ids':[unit['unit_id']],
            'requires_judgment':True} for name,meaning in (
            ('distributor','Actor is a distributor to whom the stated rule applies'),
            ('gift','Actor offers a gift to a client'),
            ('linked','The gift promotes a specific investment product or a particular type of investment product'),
            ('discount','The gift is a discount of fees or charges'))]
    clean={'local_id':'gift','family':'exceptions','subject':'Paragraph 10 stated gift restriction',
           'statement':'[TRUE_IS_PROHIBITED] True means an offer falls under the stated should-not-offer gift restriction.',
           'distinction':'Controlled exception-retaining fixture; other legal obligations outside this target',
           'citations':[{'unit_id':unit['unit_id'],'quote':unit['text']}], 'assumptions':[], 'questions':[],
           'formalization':{'facts':facts,'scope':'distributor','result':'(and gift linked (not discount))','result_type':'bool'}}
    omitted=deepcopy(clean);omitted['formalization']['result']='(and gift linked)'
    candidates={'candidate.a':omitted,'candidate.b':deepcopy(omitted),'candidate.c':deepcopy(omitted)}
    checker=Comparisons(directory/'java',JDK,AT)
    baseline=checker.compare(candidates['candidate.a'],candidates['candidate.b'],p)
    fault=checker.compare(clean,omitted,p)
    journal=JournalProvider(provider,directory/'calls',maximum=4)
    settings=Settings(max_input_bytes=200000,max_output_bytes=200000,timeout_seconds=300)
    results=[]
    for name,readings in [('unanimous-omission',candidates),('clean-control',{'candidate.clean':clean})]:
        request=fidelity_request(p,[claim],readings);outcome=None;failures=[]
        for attempt in range(2):
            response=None
            try:
                response=journal.complete(request,Fidelity.model_json_schema(),settings)
                outcome=validate_fidelity(response.value,p,[claim],readings);break
            except (LegalMathError,ValueError,OSError) as exc:
                failures.append({'error':getattr(exc,'code',type(exc).__name__)})
                if response is None:break
                request={**request,'task':'REPAIR_OUTPUT','original_task':'SOURCE_FIDELITY',
                         'invalid_response':response.value,'validation_error':str(getattr(exc,'details',None) or exc),
                         'validation_error_data':getattr(exc,'details',None),
                         'response_schema':Fidelity.model_json_schema()}
        passed=outcome is not None and not outcome['additional_concerns'] if name=='clean-control' else outcome is not None
        if passed:
            passed=all(c['label']=='ENTAILED' for c in outcome['checks']) if name=='clean-control' else all(c['label']!='ENTAILED' for c in outcome['checks'])
        results.append({'case':name,'passed':passed,'result':outcome,'failures':failures})
    result={'passed':all(r['passed'] for r in results) and baseline['status']=='EQUIVALENT_WITHIN_DOMAIN' and fault['status']=='DIFFERENT',
            'source_packet':p,'target_claim':claim,'readings':{'clean':clean,'omitted':omitted},
            'baseline_same_error_agreement':baseline,'inserted_fault_java_witness':fault,'cases':results,
            'evidence_class':'LIVE_DETECTION_OF_A_PREDECLARED_SEEDED_EXCEPTION_OMISSION',
            'legal_accuracy_evaluated':False}
    save(directory/'result.json',result);return result


def frozen_ablations(directory,report):
    """Reuse identical retained responses; do not claim equal-cost stochastic efficacy."""
    state=loads((directory/'search-state.json').read_bytes())
    nodes={n['node_id']:n for n in state['nodes']}
    normative=state['initial'].get('normative')
    initial_ids={n['node_id'] for n in nodes.values() if n['parent'] is None}
    first=[]
    if normative:
        target=normative['readings'][0]
        first=[n['node_id'] for n in nodes.values() if n['reading']==target][:1]
    arms={'single':set(first),'independent_roles':initial_ids,'search':set(nodes)}
    checks=report.get('fidelity',{}).get('checks',[]) if report.get('fidelity') else []
    return {'design':'FROZEN_RESPONSE_SUBSET_ABLATION_NO_STATISTICAL_RANKING',
            'arms':{name:{'candidate_count':len(ids),'formal_disagreements':sum(
                c['result']['status']=='DIFFERENT' and set(c['pair'])<=ids for c in state['comparisons']),
                'source_check_findings':sum(c['candidate_id'] in ids and c['label']!='ENTAILED' for c in checks),
                'source_checks_without_added_method':0} for name,ids in arms.items()},
            'limits':['Same source and retained candidates; no outcome labels or superiority claim',
                      'A separate equal-budget held-out experiment is required to rank operating methods']}


def main():
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--allowance',required=True)
    parser.add_argument('--recover',help='Retained, already-counted exact request/schema response; provenance remains explicit')
    parser.add_argument('--resume-from',help='Manifest-verified prior pilot; replay completed work and issue only the declared missing checks')
    parser.add_argument('--replay-plan',help='Reviewed source/task-specific manifest replay routes')
    args=parser.parse_args();out=Path(args.out)
    if out.exists():raise ValueError('A fresh pilot directory is required')
    out.mkdir(parents=True)
    allowance=loads(Path(args.allowance).read_bytes());start=len(allowance['calls'])
    replay_plan=loads(Path(args.replay_plan).read_bytes()) if args.replay_plan else {}
    minimum=10 if replay_plan else 14 if args.resume_from and (Path(args.resume_from)/'24EC16/manifest.json').exists() else 18
    if allowance['maximum']!=100 or RESERVATION_CEILING-start<minimum:
        raise LegalMathError('E_RESOURCE_LIMIT',details='Insufficient remaining reviewed increment for a complete pilot')
    provider=IncrementCap(CodexProvider(allowance=Allowance(args.allowance,100,reservation_ceiling=RESERVATION_CEILING)),args.allowance,args.recover)
    settings=AssuranceSettings(total_model_calls=15,semantic_repair_rounds=1,max_derived_comparisons=0,
        run_formula_challenges=True,search=Settings(max_model_calls=5,max_candidates=6,max_rounds=1,
            max_input_bytes=200000,max_output_bytes=200000,timeout_seconds=300))
    selected={
        '23EC46':'Selected paragraph-10 gift-promotion control, its fee/charge-discount exception and product or product-type connection. Account for all other provisions and footnotes as context, uncertainty or dependencies.',
        '24EC16':'Selected operational readiness obligations on licensed corporations for the settlement transition, including the Canada footnote and different foreign-exchange cycle. Distinguish optional staffing measures from duties; preserve discretion and definitions.'}
    reports=[]
    for ref,slice_text in selected.items():
        directory=out/ref
        before=len(loads(Path(args.allowance).read_bytes())['calls'])
        replay=ref in replay_plan or bool(args.resume_from and (Path(args.resume_from)/ref/'manifest.json').exists())
        missing_tasks={'SOURCE_FIDELITY','STRUCTURED_CRITICISM'}
        current=TaskReplay(provider,args.allowance,replay_plan[ref]) if ref in replay_plan else RetainedProvider(provider,Path(args.resume_from)/ref,args.allowance,
                                 new_tasks=missing_tasks) if replay else provider
        engine=Assurance(directory,current,JDK,AT,settings)
        report=engine.drive([source(ref)],slice_text);engine.verify()
        passed=(report.get('execution_complete') is True and report['model_calls']>=7 and
                len(report['inventories'])==2 and report['fidelity'] is not None and
                report['argumentation'] is not None and not report['release_eligible'])
        if (directory/'search-state.json').exists():save(directory.parent/(ref+'-ablations.json'),frozen_ablations(directory,report))
        reports.append({'circular':ref,'engineering_pass':passed,'status':report['status'],
                        'model_calls':report['model_calls'],'residual_questions':len(report['residual_questions']),
                        'new_live_invocations':len(loads(Path(args.allowance).read_bytes())['calls'])-before,
                        'evidence_mode':'EXACT_RETAINED_RESPONSES_WITH_DECLARED_MISSING_CHECKS' if replay else 'LIVE_WITH_EXPLICIT_RECOVERY_IF_MATCHED',
                        'failures':report['failures'],'report_hash':digest(report)})
        print(json.dumps(reports[-1]),flush=True)
    # These checks have independent inputs. A failed source vetoes acceptance,
    # but cannot erase the evidence obtainable from another source or challenge.
    challenge=omission_challenge(out/'shared-error-challenge',provider)
    end=len(loads(Path(args.allowance).read_bytes())['calls'])
    result={'engineering_pass':len(reports)==2 and all(r['engineering_pass'] for r in reports) and challenge is not None and challenge['passed'],
            'sources':reports,'shared_error_challenge_passed':challenge['passed'] if challenge else False,
            'starting_total_calls':start,'ending_total_calls':end,'increment_calls':end-start,
            'authorized_total':100,'round3_cap':RESERVATION_CEILING-INCREMENT_START,'legal_accuracy_evaluated':False,
            'review_effort_measured':False,'statistical_ranking_supported':False}
    save(out/'result.json',result)
    if not result['engineering_pass']:raise SystemExit(1)


if __name__=='__main__':main()
