import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import pytest
from copy import deepcopy
import hashlib
import sys
from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError

ROOT = Path('/home/chakwong/python/legalmath')
WORK = Path('artifacts/legal-mission-control/2026-10-21/review-repair')
BASE = Path('artifacts/legal-mission-control/2026-10-13/master')
CALLS = WORK/'live/arms/gatecoin/baseline/calls'
KEY = 'audit-group-gatecoin-12ea245965642fcec0dfddf2'
from legalmath.interpretation.assurance.phased import review_receipts as candidate


def fixture(root):
    folder = root/CALLS/KEY
    read = lambda name: json.loads((folder/name).read_text())
    product = SimpleNamespace(root=root, dispatch=SimpleNamespace(directory=root/CALLS),
        provider=SimpleNamespace(allowance=SimpleNamespace(path=root/BASE/'live-calls.json')))
    request = read('request.json')
    return product, KEY, read('result.json'), request['required_considered'], request, read('schema.json')


def copied(tmp_path):
    if not (ROOT/CALLS/KEY).exists():
        pytest.skip("Retained production receipt is not installed in this checkout")
    (tmp_path/CALLS).mkdir(parents=True)
    shutil.copytree(ROOT/CALLS/KEY, tmp_path/CALLS/KEY)
    journal = json.loads((ROOT/CALLS/'dispatch.json').read_text())
    journal['calls'] = {KEY: journal['calls'][KEY]}
    (tmp_path/CALLS/'dispatch.json').write_text(json.dumps(journal, sort_keys=True))
    (tmp_path/BASE).mkdir(parents=True)
    shutil.copyfile(ROOT/BASE/'live-calls.json', tmp_path/BASE/'live-calls.json')
    provenance = json.loads((ROOT/CALLS/KEY/'wire-response.json').read_text())['provenance']
    folder = BASE/'provider-evidence'/f'{provenance["allowance_slot"]}-{provenance["request_hash"][:16]}'
    shutil.copytree(ROOT/folder, tmp_path/folder)
    return fixture(tmp_path), tmp_path/folder


def test_real_wire_failure_after_canonical_reload_has_all_repair_assignments(tmp_path):
    args, _ = copied(tmp_path)
    rows = candidate.invalid_wire_reviews(*args)
    assert set(rows) == set(args[3]) and len(rows) == 24
    assert all(r['original']['interpreted'] is False for r in rows.values())
    assert all('verdict' not in r for r in rows.values())
    assert max(len(json.dumps(r)) for r in rows.values()) < 2000
    # Repeating the local read cannot spend a provider call or change its result.
    assert candidate.invalid_wire_reviews(*args) == rows


@pytest.mark.parametrize('which', ['ledger','response','provider_bytes','request','schema','dispatch'])
def test_changed_evidence_refused(tmp_path, which):
    args, receipt = copied(tmp_path)
    folder = tmp_path/CALLS/KEY
    paths = {'ledger':tmp_path/BASE/'live-calls.json', 'response':folder/'wire-response.json',
        'provider_bytes':receipt/'result.json', 'request':folder/'request.json',
        'schema':folder/'schema.json', 'dispatch':tmp_path/CALLS/'dispatch.json'}
    path = paths[which]
    data = json.loads(path.read_text())
    if which=='ledger': data['calls'][3543]['request_hash'] = '0'*64
    elif which=='response': data['value']['assignments'] = []
    elif which=='provider_bytes': data['assignments'] = []
    elif which=='request': data['required_considered'] = ['wrong']
    elif which=='schema': data['required'] = []
    else: data['calls'][KEY]['status'] = 'RESERVED'
    path.write_text(json.dumps(data))
    with pytest.raises(LegalMathError): candidate.invalid_wire_reviews(*args)


@pytest.mark.parametrize('error', ['TerminalServiceFailure','E_RESOURCE_LIMIT','E_AUTHORITY','E_INTEGRITY','E_SCHEMA'])
def test_no_transport_or_capacity_resampling(tmp_path, error):
    args, _ = copied(tmp_path)
    args = list(args)
    args[2] = {**args[2], 'error':error}
    assert candidate.invalid_wire_reviews(*args) == {}


def test_missing_wire_stays_missing(tmp_path):
    args, _ = copied(tmp_path)
    (tmp_path/CALLS/KEY/'wire-response.json').unlink()
    assert candidate.invalid_wire_reviews(*args) == {}


def test_existing_decoded_repair_path_not_duplicated(tmp_path):
    args, _ = copied(tmp_path)
    (tmp_path/CALLS/KEY/'raw.json').write_text('{}')
    assert candidate.invalid_wire_reviews(*args) == {}


@pytest.mark.parametrize('explicit_contract', [False, True])
def test_reference_dispatch_runs_one_repair_for_every_malformed_assignment(tmp_path, monkeypatch, explicit_contract):
    from dataclasses import replace
    from legalmath.interpretation.assurance.phased import group_review
    from legalmath.interpretation.assurance.phased.product import PhasedProduct
    from legalmath.interpretation.search.providers import Completion
    from tests.assurance.test_bounded_product import Scripted, envelope, limits
    from tests.assurance.test_source_review_repair import product as setup_review_product
    from legalmath.interpretation.assurance.phased import review_repair
    class WireProvider(Scripted):
        reference_transport = True
        live = False
        def __init__(self):
            super().__init__()
            self.allowance = SimpleNamespace(path=tmp_path/'ledger/live-calls.json')
            self.allowance.path.parent.mkdir(parents=True)
            self.allowance.path.write_text(json.dumps(dict(maximum=20,calls=[])))
        def complete(self, request, schema, settings):
            self.requests.append(deepcopy(request))
            ids = ([r['response_key'] for r in request['response_assignment_targets']]
                if explicit_contract else list(schema['properties']['assignments']['properties']))
            decision = dict(reason='The conditional statement follows from the delivered source.',
                source_gaps=[], assertion_bindings=[], context_needs=[],
                review=dict(verdict='ACCEPT', issues=[], support=[dict(span_id=0)]))
            value = dict(analyses=[dict(analysis_id='one', decision=decision)],
                assignments={identity:dict(analysis_id='one') for identity in ids})
            if len(self.requests)==1:
                value['assignments'] = [dict(id=identity, analysis_id='one') for identity in ids]
            ledger=json.loads(self.allowance.path.read_text())
            ledger['calls'].append(dict(request_hash=digest(request)))
            self.allowance.path.write_text(json.dumps(ledger))
            slot=len(ledger['calls'])
            folder=self.allowance.path.parent/'provider-evidence'/f'{slot}-{digest(request)[:16]}'
            folder.mkdir(parents=True)
            content={'request.json':canonical(request), 'schema.json':canonical(schema),
                'result.json':canonical(value), 'events.jsonl':(
                    json.dumps(dict(type='item.completed',item=dict(type='agent_message',text=' ')))+'\n'+
                    json.dumps(dict(type='item.completed',item=dict(type='agent_message',text=json.dumps(value))))+'\n'+
                    json.dumps(dict(type='turn.completed'))+'\n').encode()}
            manifest=dict(allowance_slot=slot, request_hash=digest(request), complete_output_present=True, files={})
            for filename,data in content.items():
                (folder/filename).write_bytes(data)
                manifest['files'][filename]=dict(bytes=len(data), original_sha256=hashlib.sha256(data).hexdigest(),
                    retained_sha256=hashlib.sha256(data).hexdigest(),redacted=False)
            (folder/'manifest.json').write_text(json.dumps(manifest))
            return Completion(value, dict(allowance_slot=slot, request_hash=digest(request), response_hash=digest(value)))

    provider = WireProvider()
    from legalmath.interpretation.assurance.phased.review_contract import PROFILE as EXPLICIT
    p=setup_review_product(tmp_path,provider, review_assignment_profile=EXPLICIT if explicit_contract else None)
    answer=dict(conclusion='Conditional source reading.', support=[], source_gaps=[])
    rows=p.audit_answer('p14',envelope()['original_questions'][0],answer,[])
    assert len(rows)==2 and all(r['status']=='VALIDATED' for r in rows)
    assert all(r['repair_evidence']['maximum_attempts']==1 for r in rows)
    assert len(provider.requests)==3
    repairs=provider.requests[1:]
    assert all('invalid_review_repair' in r['payload'] for r in repairs)
    assert all(r['payload']['answer']==provider.requests[0]['payload']['answer'] for r in repairs)
    assert all(r['account_record_table']==provider.requests[0]['account_record_table'] for r in repairs)
    assert all('full_diagnostic' in r['payload']['invalid_review_repair'] for r in repairs)
    assert p.audit_answer('p14',envelope()['original_questions'][0],answer,[]) == rows
    assert len(provider.requests)==3
