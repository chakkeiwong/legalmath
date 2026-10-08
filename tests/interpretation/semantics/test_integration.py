from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from legalmath.canonical import loads,canonical,digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.complete_investigation import verify
from legalmath.interpretation.assurance import investigation_observations as obs
from legalmath.interpretation.semantics import integration
from scripts.legal_interpretation_demo import execute

@pytest.fixture(scope="module")
def execution():
    root=Path(__file__).resolve().parents[3]
    with TemporaryDirectory(prefix="semantic-complete-",dir=root/"artifacts") as td:
        root,runner,dossier=execute(td,17)
        ref=loads((Path(td)/"current.json").read_bytes())
        yield root,runner,dossier,ref

def test_actual_route_executes_java_and_preserves_legacy_replay_above_16(execution):
    root,runner,dossier,ref=execution
    assert dossier["execution_complete"] and dossier["replay"]
    candidates=loads((root/dossier["candidates"]["path"]).read_bytes())
    assert 1<=len(candidates)<=16
    reports=dossier["semantic_stage"]["report"]["branch_reports"]
    assert len(reports)==len(candidates)*17
    assert len({r["identity"]["branch"] for r in reports})==len(reports)
    assert all(r["target"]["java"]=="EXECUTED" and len(r["target"]["executions"])==2 for r in reports)
    assert verify(root,dossier)["execution_complete"]
    checked=obs.check_stages(root,dossier,obs.method(runner),runner)
    assert "semantics" in checked["stage_started_ms"]
    assert checked["semantic_summary_hash"]

@pytest.mark.parametrize("mutation",["missing","duplicate","swap","settings"])
def test_branch_inventory_and_configuration_mutations_rejected(execution,mutation):
    root,runner,dossier,ref=execution
    path=root/dossier["semantic_stage"]["directory"]
    original=(path/"result.json").read_bytes()
    value=loads(original)
    if mutation=="missing": value["branch_reports"].pop()
    elif mutation=="duplicate": value["branch_reports"][1]=deepcopy(value["branch_reports"][0])
    elif mutation=="swap": value["branch_reports"][0],value["branch_reports"][1]=value["branch_reports"][1],value["branch_reports"][0]
    else: value["configuration"]["settings"][0]["max_arguments"]+=1
    inputs=loads((path/"inputs.json").read_bytes())
    try:
        (path/"result.json").write_bytes(canonical(value))
        with pytest.raises(LegalMathError) as error:
            integration.verify(path,inputs["packet"],inputs["candidates"],inputs["questions"],inputs["options"],inputs["at"],
                               target=dossier["binding"]["investigation_method"]["toolchains"]["java"],context=inputs["context"])
        assert error.value.code==("E_STALE_REVIEW" if mutation=="settings" else "E_REFERENCE")
    finally: (path/"result.json").write_bytes(original)

def test_missing_semantic_stage_and_changed_method_rejected(execution,monkeypatch):
    root,runner,dossier,ref=execution
    altered=deepcopy(dossier);del altered["semantic_stage"]
    with pytest.raises(LegalMathError) as error: verify(root,altered)
    assert error.value.code=="E_REFERENCE"
    old=deepcopy(runner.semantic_options);old["settings"][0]["max_arguments"]+=1
    monkeypatch.setattr(runner,"semantic_options",old)
    with pytest.raises(LegalMathError) as error: obs.check_stages(root,dossier,dossier["binding"]["investigation_method"],runner)
    assert error.value.code=="E_STALE_REVIEW"

def test_legacy_adapter_refuses_priorities_it_cannot_apply():
    from scripts.legal_interpretation_demo import options
    opts=options(1);opts["settings"][0]["ordering"]="last-link"
    opts["settings"][0]["priorities"]=[{"stronger":"r","weaker":"s",
        "premise":{"id":"pref","statement":"Declared priority","status":"declared","dependencies":[]}}]
    with pytest.raises(LegalMathError) as error:integration.configuration(opts)
    assert error.value.code=="E_UNSUPPORTED_PROFILE"
