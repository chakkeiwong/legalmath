"""Capture the first production phase contract without dispatch or old writes."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_master import BASE, PROGRAM, TOKENIZER
from scripts.legal_integration_campaign import provider
from scripts.legal_integration_phased_live import LIVE
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.phased import product as product_module
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import (
    account_contract, account_encoding, account_instructions, account_input,
    account_output, downstream_instructions, phase,
)
from legalmath.interpretation.assurance.phased.evidence_store import load_exact

WORK = Path(__file__).resolve().parent
began = time.monotonic()
program = read(ROOT / PROGRAM)
revision = program['repair_execution']
ledger_before = ref(ROOT, BASE / 'live-calls.json')
binding_before = ref(ROOT, BASE / 'current-binding.json')
program_before = ref(ROOT, PROGRAM)
grant_before = ref(ROOT, BASE / 'live-grant.json')
common = ROOT / revision['common_directories']['p10']
directory = WORK / 'p10-phase-diagnostic'
require(not directory.exists(), 'Never overwrite a diagnostic')

def forbidden(*args, **kwargs):
    raise AssertionError('Completion, reservation and admission forbidden')

service = provider()
service.complete = forbidden
service.allowance.reserve = forbidden
product = PhasedProduct(
    ROOT, directory, service, read(ROOT / program['prerequisite_repair']['source']['path']),
    tokenizer(ROOT / TOKENIZER), limits=Limits(), maximum_calls=8100,
    active_questions=['p10'], phase_admit=forbidden,
    phase_identity=binding_before['sha256'],
    requirement_account_profile=account_contract.PROFILE,
    requirement_account_input_profile=account_encoding.PROFILE,
    requirement_account_instruction_profile=account_instructions.PROFILE,
    requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
    requirement_account_output_profile=account_output.PROFILE,
    requirement_account_recovery=revision['recoveries']['p10'],
    downstream_input_profile=revision['downstream_input_profile'],
    downstream_instruction_profile=downstream_instructions.PROFILE)
product.retained_acquisition = load_exact(ROOT / LIVE / 'acquisition/investigation.json')

def capture(actual_product, name, calls, *, implementation_identity, admit, **kwargs):
    prepared = actual_product.prepare_calls(calls)
    path = common / 'phases' / name / 'phase.json'
    require(path.is_file(), 'First actual phase differs from retained failure hypothesis')
    before = ref(ROOT, path)
    old = read(path)['contract']
    current = dict(profile='bounded-persisted-phase.v1', name=name,
        input_hash=actual_product.route.input_hash,
        implementation_identity=implementation_identity,
        calls=[dict(key=r['key'], identity=actual_product.dispatch.request_identity(
            r['request'], r['schema'])) for r in prepared])
    differences = [dict(field=k, previous=old.get(k), current=current.get(k))
        for k in sorted(set(old) | set(current)) if old.get(k) != current.get(k)]
    require([r['field'] for r in differences] == ['implementation_identity'],
            'Phase mismatch is not limited to the implementation binding')
    require(old['implementation_identity'] == program['frontier_refresh']['prior_binding']['sha256'],
            'Persisted phase is not from the authenticated predecessor')
    proxy = SimpleNamespace(directory=common, route=actual_product.route,
        dispatch=actual_product.dispatch, prepare_calls=lambda _: prepared)
    try:
        phase.execute(proxy, name, calls, implementation_identity=implementation_identity,
                      admit=forbidden)
    except LegalMathError as exc:
        require(exc.code == 'E_INTEGRITY' and exc.details == 'Changed phase on resume',
                'Different actual phase guard failure')
    else:
        raise AssertionError('Actual guard did not refuse changed phase binding')
    require(ref(ROOT, path) == before, 'Diagnostic changed retained phase')
    for path, pointer in ((BASE / 'live-calls.json', ledger_before),
            (BASE / 'current-binding.json', binding_before), (PROGRAM, program_before),
            (BASE / 'live-grant.json', grant_before)):
        require(ref(ROOT, path) == pointer, 'Diagnostic changed authority or calls')
    evidence_common = ROOT / revision['common_directories']['evidence']
    evidence_phases = sorted(str(p.relative_to(ROOT))
        for p in evidence_common.glob('phases/*/phase.json'))
    report = dict(verdict='PASS', question='p10', phase=name,
        actual_constructor=True, actual_phase_guard=True, differences=differences,
        all_other_contract_fields_equal=True, retained_phase=before,
        current_contract=current, provider_calls=0, ledger_unchanged=True,
        ledger=ledger_before, program=program_before, binding=binding_before,
        grant=grant_before, evidence_existing_phases=evidence_phases,
        p10_attempts_exhausted=True, repaired=False, legal_acceptance=False,
        limitation='One first-account phase boundary; no complete acquisition or evidence execution claim.',
        command='.venv-context/bin/python ' + str(Path(__file__).relative_to(ROOT)),
        environment=sys.executable, devices='CPU only; CUDA_VISIBLE_DEVICES=-1',
        seeds='N/A: deterministic constructor/contract diagnostic',
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source=ref(ROOT, Path(__file__)), plan=ref(ROOT, WORK / 'p10-phase-diagnostic-plan.md'),
        at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic()-began)
    save(WORK / 'p10-phase-diagnostic-result.json', report)
    print(json.dumps({k:report[k] for k in ('verdict','phase','differences',
        'provider_calls','evidence_existing_phases','wall_seconds')},indent=2),flush=True)
    raise SystemExit(0)

product_module.execute = capture
product.install_dispatch_admission()
product.requirement_details()
raise AssertionError('Diagnostic never reached an actual account phase')
