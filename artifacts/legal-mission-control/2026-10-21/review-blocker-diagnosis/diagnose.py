"""Offline reconstruction of review sizing; no dispatch or production writes."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import sys
import time
import subprocess
from pathlib import Path
from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts import legal_integration_phased_live as live
from scripts.legal_mission_execution import read, ref, save
from legalmath.canonical import digest, canonical
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import group_review, downstream_input
from legalmath.interpretation.assurance.phased.source_review import assignments
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
from jsonschema import validate as validate_schema

WORK = Path(__file__).resolve().parent
ARMS = ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface/live/arms'


def never(*args, **kwargs):
    raise AssertionError('Read-only diagnostic attempted model dispatch or phase admission')


def measured(product, request, schema):
    try:
        return dict(status='FIT', measurement=product.dispatch.measure(request, schema))
    except LegalMathError as exc:
        return dict(status='REFUSED', code=exc.code, detail=exc.details)


def main():
    started = time.monotonic()
    ledger = ROOT/live.BASE/'live-calls.json'
    initial_ledger = ref(ROOT, ledger)
    ledger_value = read(ledger)
    program = read(ROOT/live.PROGRAM)
    envelope = read(ROOT/program['prerequisite_repair']['source']['path'])
    acquisition = load_exact(ROOT/live.LIVE/'acquisition/investigation.json')
    encode = tokenizer(ROOT/live.TOKENIZER)
    service = live.configure().provider()
    report = dict(provider_calls=0, started_at_utc=datetime.now(timezone.utc).isoformat(),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        command='.venv-context/bin/python '+str(Path(__file__).relative_to(ROOT)),
        environment='.venv-context; CUDA_VISIBLE_DEVICES=-1; GPU deliberately hidden',
        plan=ref(ROOT,'docs/plans/legal-review-blocker-diagnosis-2026-10-21.md'),
        program=ref(ROOT,live.PROGRAM), questions={},
        charged_calls=len(ledger_value['calls']), maximum_calls=ledger_value['maximum'])
    with patch.object(BoundedCodexProvider, 'complete', never):
        for qid in ('gatecoin','p14'):
            original = ARMS/qid/'baseline'
            identity = read(original/'identity.json')
            options = {k: identity[k] for k in (
                'requirement_account_profile','requirement_account_input_profile',
                'requirement_account_instruction_profile','requirement_account_capacity_profile',
                'requirement_account_output_profile','common_capacity_profile') if k in identity}
            product = PhasedProduct(ROOT,WORK/'constructor'/qid,service,envelope,encode,
                limits=Limits(),maximum_calls=8100,maximum_corrections=1,active_questions=[qid],
                downstream_input_profile=program['repair_execution']['downstream_input_profile'],
                downstream_instruction_profile=program['repair_execution'].get('downstream_instruction_profile'),
                downstream_capacity_profile=program['synthesis_resolution']['downstream_capacity_profile'],
                phase_admit=never,phase_identity='offline-review-blocker-diagnosis',**options)
            assert product.route.input_hash == identity['input_hash']
            assert product.route.store_hash == identity['store_hash']
            assert product.route.records == read(original/'source-store.json')
            if 'review_census' not in report:
                from scripts.legal_integration_acceptance import current_register
                applicability_ref = current_register(program, 'applicability')
                applicability = read(ROOT/applicability_ref['path'])
                census = {}
                for question_id in ('p10', 'p14', 'evidence', 'gatecoin'):
                    population = assignments(product, question_id, acquisition['discovered_dependencies'])
                    applicable = [r['tool'] for r in applicability['pairs']
                        if r['question'] == question_id and r['decision'] == 'applicable']
                    minimum = (len(population) + 4) // 5
                    census[question_id] = dict(assignments=len(population), applicable_tools=applicable,
                        minimum_groups_per_fresh_arm=minimum,
                        minimum_groups_baseline_and_applicable_arms=minimum*(1+len(applicable)))
                report['review_census'] = dict(applicability=applicability_ref, questions=census,
                    basis='Current estimator 1024 + 1200*n <= 8192 permits at most five assignments per call.',
                    scope='Fresh review pass only; not remaining work after exact reuse. Excludes corrections, bridges, other stages and service retries.',
                    fresh_pass_lower_bound=sum(r['minimum_groups_baseline_and_applicable_arms'] for r in census.values()))
            result = load_exact(original/'result.json')
            answer = result['answers'][qid]['answer']['value']
            reviews = result['answers'][qid]['reviews']
            items = assignments(product,qid,acquisition['discovered_dependencies'])
            source = [i for i in items if i.get('kind')=='source']
            deps = [i for i in items if i.get('kind')!='source']
            # Deliberately small, named diagnostic population; not a full fit claim.
            selected = [source[0],max(source,key=lambda r:len(product.route.records[r['origin_id']]['text']))]
            if deps:
                selected += [deps[0],max(deps,key=lambda r:len(canonical(r)))]
            cases=[]
            question=next(q for q in envelope['original_questions'] if q['question_id']==qid)
            for item in selected:
                req,shape=group_review.build(product,qid,question,answer,[item])
                corrected=deepcopy(req)
                corrected['downstream_capacity_profile']=product.downstream_capacity_profile
                assert {k:v for k,v in corrected.items() if k!='downstream_capacity_profile'} == req
                cases.append(dict(id=item['id'],kind=item.get('kind','dependency'),
                    original_profile=req.get('downstream_capacity_profile'),
                    current=measured(product,req,shape),selected_profile=measured(product,corrected,shape),
                    changed_fields=['downstream_capacity_profile']))
            report['questions'][qid]=dict(input_hash=product.route.input_hash,
                result=ref(ROOT,original/'result.json'),assignment_count=len(items),
                answer_bytes=len(canonical(answer)), answer_tokens=len(encode(canonical(answer).decode())),
                cases=cases,review_status=dict(Counter(r['status'] for r in reviews)),
                failed_reasons=dict(Counter(r.get('reason') for r in reviews if r['status']!='VALIDATED')),
                verdicts=dict(Counter(r['value']['verdict'] for r in reviews if r['status']=='VALIDATED')))
            if qid=='p14':
                folder=original/'calls/audit-group-p14-b1344d092fd76fb2dc46c4e1'
                raw=read(folder/'raw.json')['value']; req=read(folder/'request.json'); shape=read(folder/'schema.json')
                validate_schema(raw,shape)
                invalid=[]
                for row in raw['analyses']:
                    for need in row['decision']['context_needs']:
                        if need['kind']!='SOURCE_TEXT' and (need['record_ids'] or need['locators']):
                            invalid.append(dict(analysis=row['analysis_id'],kind=need['kind'],
                                source_ids=len(need['record_ids']),locators=len(need['locators'])))
                try:
                    group_review.validate(product,qid,raw,req['required_considered'],req['records'])
                    semantic='VALIDATED'
                except LegalMathError as exc:
                    semantic=dict(code=exc.code,reason=exc.details)
                bad_rejects=[r for r in reviews if r['status']=='VALIDATED' and
                    r['value']['verdict']=='REJECT' and not (r['value']['issues'] and r['value']['support'])]
                unresolved=[r for r in reviews if r['status']=='VALIDATED' and r['value']['verdict']=='UNRESOLVED']
                mixed=[r for r in unresolved if any(n['kind']=='SOURCE_TEXT' for n in r['value'].get('context_needs',[]))
                    and any(n['kind']!='SOURCE_TEXT' for n in r['value'].get('context_needs',[]))]
                report['questions'][qid].update(schema_passes_but_local_validation=semantic,
                    invalid_context_needs=invalid,unsupported_reject_labels=len(bad_rejects),
                    mixed_context_reviews_skipped=len(mixed))
            else:
                report['questions'][qid]['warrants']=[dict(review_index=r['review_index'],
                    status=r['result']['status'],gaps=len(r['result'].get('value',{}).get('source_gaps',[])),
                    dispositions=dict(Counter(d['disposition'] for d in r['result'].get('value',{}).get('decisions',[]))))
                    for r in result['answers'][qid]['correction']['review_warrants']]
            save(WORK/'diagnosis.json',report)
            print(qid,json.dumps(dict(assignment_count=len(items), cases=[dict(id=c['id'],
                current_status=c['current']['status'], selected_status=c['selected_profile']['status'],
                current=c['current'].get('measurement',c['current'].get('detail')),
                selected=c['selected_profile'].get('measurement',c['selected_profile'].get('detail')))
                for c in cases]),sort_keys=True),flush=True)
    report.update(ledger_unchanged=initial_ledger==ref(ROOT,ledger),wall_seconds=time.monotonic()-started,
        legal_acceptance=False,production_changes=False,completed_at_utc=datetime.now(timezone.utc).isoformat())
    save(WORK/'diagnosis.json',report)
    assert report['ledger_unchanged']


if __name__=='__main__':
    main()
