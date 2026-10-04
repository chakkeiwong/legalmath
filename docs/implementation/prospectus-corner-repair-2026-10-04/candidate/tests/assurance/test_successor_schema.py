"""Reject known interface errors before spending a live reservation."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
from legalmath.errors import LegalMathError
from legalmath.canonical import digest
from legalmath.interpretation.search.schema import validate_output_schema
from legalmath.interpretation.search.providers import CodexProvider
from legalmath.interpretation.search.models import Generation, Reconstruction, Settings
from legalmath.interpretation.assurance.semantics import Inventory, Fidelity
from legalmath.interpretation.assurance.arguments import Criticism
from legalmath.interpretation.assurance.abstractions import AbstractionBatch
from legalmath.interpretation.assurance.decomposition import CrossPieceCheck
from legalmath.interpretation.assurance.complete_investigation import Questions
from legalmath.interpretation.assurance.authority_arguments import AuthorityArguments
from legalmath.interpretation.assurance.controls import Routing
from legalmath.interpretation.assurance.issue_search import Hypotheses, IssueAudit
from legalmath.interpretation.assurance.fidelity_v2 import FidelityV2
from legalmath.interpretation.assurance.meaning_bridges import output_schema
from legalmath.interpretation.assurance.repair import mapping_output_schema
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from .test_successor_grants import grant
from .test_successor_meaning import bridge_fixture

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from assurance_successor_live import AuthorityAnswer, RegionBatch, migrate_failed_schema_journal
from assurance_successor_evaluate import CaseMappings


@pytest.mark.parametrize('model',[Generation,Reconstruction,Inventory,Fidelity,Criticism,
    AbstractionBatch,CrossPieceCheck,Questions,AuthorityArguments,Routing,Hypotheses,
    IssueAudit,FidelityV2,AuthorityAnswer,RegionBatch,CaseMappings])
def test_live_contracts_pass_necessary_structural_checks(model):
    assert validate_output_schema(model.model_json_schema())['provider_acceptance_not_guaranteed']


def test_open_dictionary_is_rejected_without_dispatch_or_reservation(tmp_path):
    allowance,_=grant(tmp_path);p=CodexProvider(allowance=allowance)
    p.command=lambda *a:pytest.fail('An invalid output schema must not launch a provider')
    schema={'type':'object','properties':{'evidence':{'type':'object','additionalProperties':{'type':'string'}}},
            'required':['evidence'],'additionalProperties':False}
    with pytest.raises(LegalMathError) as caught:p.complete({'public':'source'},schema,Settings())
    assert caught.value.code=='E_SCHEMA' and allowance.verify()['used']==0
    assert not (tmp_path/'provider-evidence').exists()


def test_bridge_wire_schema_requires_exact_original_fact_names():
    left,right,_=bridge_fixture()
    for schema,fields in ((output_schema(left,right),'bridge'),
        (mapping_output_schema(left['reading'],right['reading']),'mapping')):
        validate_output_schema(schema)
        props=schema['$defs']['DerivedMapping']['properties'] if fields=='bridge' else schema['properties']
        for side,model in (('left',left),('right',right)):
            expected={f['name'] for f in model['reading']['formalization']['facts']}
            assert set(props[side]['properties'])==expected==set(props[side]['required'])
            assert props[side]['additionalProperties'] is False


def test_schema_migration_keeps_failed_action_deadline_and_original_file(tmp_path):
    binding={'request':digest('unchanged question'),'schema':digest('old open schema'),
             'route':'controlled','rendered_image':None}
    old=EvidenceJournal(tmp_path/'old',binding,maximum_actions=3,maximum_per_issue=3,deadline_seconds=3600)
    def fail(work):raise LegalMathError('E_DEPENDENCY',details='invalid_json_schema')
    with pytest.raises(LegalMathError):old.execute('judgment',{'attempt':0},fail,issue='same.question')
    before=old.path.read_bytes();prior=old.report();newbinding={**binding,'schema':digest('corrected schema')}
    migrated=migrate_failed_schema_journal(old.path,tmp_path/'new',newbinding)
    assert migrated.report()['actions']==prior['actions']
    assert migrated.report()['started_ms']==prior['started_ms']
    for i in (1,2):migrated.execute('judgment',{'attempt':i},lambda w:{'status':'CONTROLLED'},issue='same.question')
    with pytest.raises(LegalMathError) as caught:
        migrated.execute('judgment',{'attempt':3},lambda w:{},issue='same.question')
    assert caught.value.code=='E_RESOURCE_LIMIT'
    again=migrate_failed_schema_journal(old.path,tmp_path/'new',newbinding)
    assert again.report()['consumed_actions']==3 and old.path.read_bytes()==before
    with pytest.raises(LegalMathError):
        migrate_failed_schema_journal(old.path,tmp_path/'different-question',{**newbinding,'request':digest('changed')})


@pytest.mark.parametrize('mutation',['required','open','conditional'])
def test_nested_invalid_shapes_are_rejected(mutation):
    schema=deepcopy(AuthorityAnswer.model_json_schema())
    obj=schema['$defs']['AuthorityEvidence']
    if mutation=='required':obj['required']=[]
    elif mutation=='open':obj['additionalProperties']=True
    else:obj['if']={'type':'object'}
    with pytest.raises(LegalMathError):validate_output_schema(schema)
