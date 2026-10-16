"""Actual product/consumer entry points, with explicitly scripted model responses."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from copy import deepcopy
from pathlib import Path
import tempfile

from legalmath.canonical import loads
from legalmath.interpretation.assurance import dossier_answer as whole
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify
from scripts.legal_mission_context_boundary import receipt
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .test_integration import source, settings
from .test_successor_workflow import investigation, complete_responder
from .test_dossier_answer import prepared
from tests.tooling.test_legal_independent_tools import FailedBackend


def test_full_product_continues_after_failed_tool_without_claiming_completion():
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='independent-product-', dir=root/'artifacts') as td:
        provider = FunctionProvider(complete_responder)
        runner = CompleteInvestigation(root, td, provider, root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
            settings=settings(), maximum_scoped_actions=12, scoped_rounds=1,
            optional_tool_backend=FailedBackend(), optional_tool_failures='continue-independent')
        # This fixture also has an argument checkpoint.
        runner.optional_tool_backend.criticism = lambda *a: {'status': 'UNSUPPORTED', 'tool': 'Argument tools'}
        dossier = runner.run([source()], 'Selected gift control')
        assert any(r['task'] == 'SCOPED_SOURCE_FIDELITY' for r in provider.requests)
        assert not dossier['execution_complete']
        assert any(c['status'] == 'FAILED' for c in dossier['optional_tools']['checks'])
        assert verify(root, dossier)['status'] == 'FILE_BOUND_INVESTIGATION_VERIFIED'


def test_consumer_continues_valid_sibling_groups_and_blocks_synthesis(prepared, monkeypatch):
    root, directory, ref, args, original = prepared
    old_partition = whole.partition
    # Make several genuinely independent bounded groups out of the actual registry.
    def partition(value, **kwargs):
        result = old_partition(value, **kwargs)
        ids = list(result['registry']['records'])
        result['batches'] = [ids[:len(ids)//2], ids[len(ids)//2:]]
        return result
    monkeypatch.setattr(whole, 'partition', partition)
    calls = []
    def respond(req):
        calls.append(req['task']); value = receipt(req)
        if len(calls) == 1: value['accounts'] = []
        return value
    result = whole.propose(root, ref, FunctionProvider(respond), directory/'independent-reviews',
                           **args, continue_independent_reviews=True)
    assert calls == ['REVIEW_DOSSIER_EVIDENCE', 'REVIEW_DOSSIER_EVIDENCE']
    assert result['status'] == 'REJECTED' and result['completed_reviews'] == 1
    assert result['failed_reviews'][0]['group'] == 0


def test_actual_consumer_answer_exposes_the_shared_review_contract(prepared):
    root, directory, ref, args, original = prepared
    result = whole.propose(root, ref, FunctionProvider(receipt), directory/'grounded-review', **args)
    assert result['status'] == 'STRUCTURALLY_VALID_PROPOSAL'
    proposal = loads((directory/'grounded-review/answer-proposal.json').read_bytes())
    synthesis = loads((directory/'grounded-review/synthesis-request.json').read_bytes())
    req = whole.prepare_answer_review(original, proposal, synthesis_request_value=synthesis)
    assert req['answer']['answers'] == proposal['answers']
    assert req['evidence']['fields']
