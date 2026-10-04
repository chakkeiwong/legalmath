from pathlib import Path
from tempfile import TemporaryDirectory

from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify
from legalmath.interpretation.assurance import source_references
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .test_integration import source, settings
from .test_successor_workflow import complete_responder
from .test_continuation_references import encode_quotes


def test_all_source_span_transport_and_fair_review_run_through_complete_investigation():
    root = Path(__file__).resolve().parents[2]
    def responder(request):
        value = complete_responder(request)
        return encode_quotes(value, request['source_references']) if 'source_references' in request else value
    with TemporaryDirectory(prefix='continuation-integration-', dir=root/'artifacts') as path:
        provider = FunctionProvider(responder)
        runner = CompleteInvestigation(root, path, provider, root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
            settings=settings(), maximum_scoped_actions=12, scoped_rounds=1,
            reference_protocol=source_references.PROTOCOL, scoped_schedule='round-first', machine_qualification=True)
        result = runner.run([source()], 'Selected gift control')
        assert result['execution_complete'] and result['qualifications']
        assert result['scoped']['schedule'] == 'round-first'
        assert verify(root, result)['status'] == 'FILE_BOUND_INVESTIGATION_VERIFIED'
        stages = {r['task'] for r in provider.requests if 'source_references' in r}
        assert {'SOURCE_INVENTORY', 'DEFINE_EXACT_QUESTIONS', 'SCOPED_SOURCE_FIDELITY'} <= stages
        assert all(r['report']['summary']['legal_correctness'] == 'NOT_ESTABLISHED' for r in result['qualifications'])
