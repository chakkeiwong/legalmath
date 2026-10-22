"""Execute the admitted complete supplied Note22 reader and offline installation."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from pathlib import Path
import os
import shutil
import sys
import tempfile

from scripts import prospectus_basf_pension_source as source
from scripts.prospectus_installed_profile_worker import execution_guard
from legalmath.prospectus import basf_pension_note as note, basf_pension_spec as spec, basf_hedge_note
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

ROOT,HERE,PRIOR=source.ROOT,source.HERE,source.PRIOR
save,load,require=source.save,source.load,source.require
RUNNER=ROOT/"scripts/prospectus_installed_pension_runner.py"
TEST="tests/prospectus/test_basf_pension_note.py"
os.environ.update(PIP_NO_INDEX="1",PIP_DISABLE_PIP_VERSION_CHECK="1",PIP_NO_CACHE_DIR="1",PYTHONNOUSERSITE="1",PYTHONPATH="")


def methods():
    paths=[Path(__file__),Path(source.__file__),RUNNER,ROOT/TEST,ROOT/source.PLAN,HERE/"IMAGE-REVIEW.md",HERE/"IMPLEMENTATION-REVIEW.md",
           ROOT/"scripts/prospectus_installed_profile_worker.py",ROOT/"pyproject.toml"]
    paths+=sorted((ROOT/"src/legalmath").rglob("*.py"))
    return {str(p.relative_to(ROOT)):file_hash(p) for p in paths}


def profile():
    require((HERE/"IMAGE-REVIEW.md").is_file(),"Original images must be reviewed")
    current=methods();save("methods.json",current)
    for name,expected in current.items():
        target=HERE/"methods"/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("xb") as stream:stream.write((ROOT/name).read_bytes())
        require(file_hash(target)==expected,"Method snapshot changed")
    graph=load(HERE/"products.json.gz")["P1"]["payload"]["graph"]
    units={u["id"]:u for u in graph["units"]}
    def group(page,selectors):
        out=[]
        for selector in selectors:
            n=int(str(selector).split(":")[0]);u=units[note.DOCUMENT+":p"+str(page)+":l"+str(n)]
            start,end=note.original_span(u,selector)
            out.append(anchor(u,start,end))
        return out
    tables={}
    for key,t in spec.TABLES.items():
        p=t["page"]
        tables[key]={"page":p,"kind":t["kind"],"scope":t["scope"],
            "title":group(p,t["title"]),"unit":group(p,t["unit"]),
            "columns":[{"id":name,"anchors":group(p,ids)} for name,ids in t["columns"]],
            "groups":[{"members":members,"anchors":group(p,ids)} for ids,members in t["groups"]],
            "rows":[{"id":r["id"],"parent":r["parent"],"label":group(p,r["label"]),
                "cells":{c[0]:group(p,ids) for c,ids in zip(t["columns"],r["cells"])}} for r in t["rows"]]}
    value={"version":note.VERSION,"graph_sha256":digest(graph),
        "prior_sha256":digest(load(PRIOR/"hedge-consumer.json.gz")),
        "reviewer":{"identity":"Codex original-image reading2026-10-16","basis":"AGENT_EXPOSED_DEVELOPMENT_REVIEW","independent":False},
        "source":{k:v for k,v in read(HERE/"rendered-source.json").items() if k!="renderer"},
        "metadata":{str(p):group(p,[0,1,2]) for p in spec.COUNTS},
        "prose":{k:{"column":column,"meaning":meaning,"anchors":group(p,ids)} for k,(p,ids,column,meaning) in spec.PROSE.items()},
        "tables":tables,"typographic":{str(p):group(p,ids) for p,ids in spec.TYPOGRAPHIC.items()},
        "shared_separators":group(261,[str(n)+":separator" for n in spec.SHARED]),
        "excluded_note23":group(266,spec.EXCLUDED),"selected_reading":None,"financial_values_validated":False}
    save("profile.json",value);save("profile-pin.json",{"sha256":digest(value)})
    save("prior-profiles.json",read(PRIOR/"prior-profiles.json"))
    save("hedge-profile.json",read(PRIOR/"profile.json"))
    return {"tables":len(tables),"printed_cells":sum(len(r["cells"]) for t in tables.values() for r in t["rows"]),
            "source_occurrences":753,"note_occurrences":704,"excluded_occurrences":49}


def baseline():
    old=read(HERE/"prior-profiles.json");hp=read(HERE/"hedge-profile.json")
    value=basf_hedge_note.consume(load(HERE/"products.json.gz"),old,hp,ROOT,
        expected_prior_profiles_sha256=digest(old),expected_profile_sha256=digest(hp))
    save("baseline-consumer.json.gz",value)
    require(value==load(PRIOR/"hedge-consumer.json.gz"),"Current complete historical consumer differs")
    return {"complete_previous_output_equal":True,"current_consumer_of_retained_products":True}


def compare():
    old=read(HERE/"prior-profiles.json");hp=read(HERE/"hedge-profile.json");p=read(HERE/"profile.json")
    value=note.consume(load(HERE/"products.json.gz"),old,hp,p,ROOT,
        expected_prior_profiles_sha256=digest(old),expected_hedge_profile_sha256=digest(hp),expected_profile_sha256=digest(p))
    baseline=load(HERE/"baseline-consumer.json.gz")
    require({k:value[k] for k in baseline}==baseline,"Complete prior outputs changed")
    review=value["pension_note_review"]
    require((review["page_occurrences_accounted"],review["note_occurrences"],review["excluded_occurrences"])==(753,704,49),"Incomplete source accounting")
    require(value["pension_explanation"]["sensitivity"]["combined_change_addition_permitted"] is False,"Source sensitivity qualification lost")
    require(value["pension_explanation"]["oci"]["unique_complete_bridge_established"] is False,"Unsupported complete bridge")
    save("pension-consumer.json.gz",value)
    save("downstream-comparison.json",{"baseline_without_note22":digest(baseline),"extended_consumer":digest(value),
        "all_prior_outputs_equal":True,"omission_has_no_pension_explanation":"pension_explanation" not in baseline,
        "new_explanation":value["pension_explanation"],"automatic_interpretation":False})
    summary={"status":"PASS","source_occurrences":753,"note_occurrences":704,"excluded_occurrences":49,
        "tables":len(review["tables"]),"printed_cells":review["printed_cells"],"complete_prior_output_equal":True,
        "comparison_statuses":{s:sum(c["status"]==s for c in review["comparisons"]) for s in sorted({c["status"] for c in review["comparisons"]})},
        "printed_differences":[{"name":c["name"],"left_minus_right":c["left_minus_right"]} for c in review["comparisons"] if c["status"]=="PRINTED_DIFFERENCE"],
        "financial_values_validated":False,"legal_scope_selected":False,"independent_legal_acceptance":False}
    save("comparison.json",summary);return summary


def controls():
    p=read(HERE/"profile.json");products=load(HERE/"products.json.gz");prior=load(HERE/"baseline-consumer.json.gz")
    names=("wrong-year","wrong-country","cross-row","cross-column","omitted-cell","duplicate-cell",
        "dash-as-zero","zero-as-dash","rate-as-money","percent-as-money","lost-of-which","omitted-table",
        "omitted-sensitivity-limit","changed-liability-condition","changed-ceiling-rule","note23-leak",
        "omitted-excluded-context","wrong-shared-span","omitted-separator","invented-substring-box",
        "omitted-split-letter","omitted-soft-hyphen","changed-source","changed-image","legal-selection",
        "independent-review","financial-validation","stale-prior","stale-pin")
    results=[]
    for name in names:
        value=deepcopy(p);t=value["tables"];dbo=t["dbo"]["rows"];fund=t["funding"]["rows"]
        if name=="wrong-year":t["dbo"]["columns"].reverse()
        elif name=="wrong-country":t["obligation_assumptions"]["groups"][0]["members"]=["us:2022","us:2021"]
        elif name=="cross-row":dbo[0]["cells"],dbo[1]["cells"]=dbo[1]["cells"],dbo[0]["cells"]
        elif name=="cross-column":dbo[0]["cells"]["2022"],dbo[0]["cells"]["2021"]=dbo[0]["cells"]["2021"],dbo[0]["cells"]["2022"]
        elif name=="omitted-cell":dbo[0]["cells"]["2022"]=[]
        elif name=="duplicate-cell":dbo[0]["cells"]["2022"]*=2
        elif name=="dash-as-zero":fund[0]["cells"]["2022:assets"][0]["quote"]="0"
        elif name=="zero-as-dash":t["net"]["rows"][3]["cells"]["2021"][0]["quote"]="–"
        elif name=="rate-as-money":t["obligation_assumptions"]["kind"]="million_eur"
        elif name=="percent-as-money":t["asset_structure"]["kind"]="million_eur"
        elif name=="lost-of-which":dbo[8]["parent"]=None
        elif name=="omitted-table":del t["mortality"]
        elif name=="omitted-sensitivity-limit":value["prose"]["sensitivity_limit"]["anchors"].pop()
        elif name=="changed-liability-condition":value["prose"]["subsidiary_liability"]["meaning"]="All plans are defined contribution regardless of employer recourse."
        elif name=="changed-ceiling-rule":value["prose"]["asset_ceiling"]["meaning"]="Every pension surplus is available to the employer."
        elif name=="note23-leak":value["prose"]["government_contributions"]["anchors"].append(deepcopy(value["excluded_note23"][0]))
        elif name=="omitted-excluded-context":value["excluded_note23"].pop()
        elif name=="wrong-shared-span":value["prose"]["valuation"]["anchors"][-2]["end"]+=1
        elif name=="omitted-separator":value["shared_separators"].pop()
        elif name=="invented-substring-box":value["prose"]["valuation"]["anchors"][-2]["bbox"]=[42,427,287,438]
        elif name=="omitted-split-letter":value["prose"]["discount_change"]["anchors"].pop(0)
        elif name=="omitted-soft-hyphen":value["typographic"]["261"].pop()
        elif name=="changed-source":value["source"]["sha256"]="0"*64
        elif name=="changed-image":value["source"]["images"][5]["sha256"]="0"*64
        elif name=="legal-selection":value["selected_reading"]="full-financial-statements"
        elif name=="independent-review":value["reviewer"]["independent"]=True
        elif name=="financial-validation":value["financial_values_validated"]=True
        elif name=="stale-prior":value["prior_sha256"]="0"*64
        else:value["reviewer"]["identity"]+=" changed"
        pin=digest(p) if name=="stale-pin" else digest(value)
        save("adverse-inputs/"+name+".json.gz",{"profile":value,"expected_profile_sha256":pin})
        try:note.evaluate(products["P1"]["payload"]["graph"],prior,value,ROOT,expected_profile_sha256=pin)
        except ValueError as error:results.append({"case":name,"refused":True,"repinned":name!="stale-pin","reason":str(error)})
        else:raise ValueError("Altered pension profile accepted: "+name)
    save("actual-controls.json",results)
    return {"actual_refusals":len(results),"repinned":len(results)-1}


def tests():
    with (HERE/"tests.log").open("x") as log,redirect_stdout(log),redirect_stderr(log):
        import pytest
        code=int(pytest.main(["-q","-p","no:cacheprovider",TEST,"--junitxml="+str(HERE/"tests.xml")]))
    require(code==0,"Pension focused tests failed")
    return {"tests":checked_tests(HERE/"tests.xml",1),"exit_code":code}


def workspace():return Path(read(HERE/"workspace.json")["directory"])


def dependencies(env):
    site=env/"lib/python3.11/site-packages"
    return {str(p.relative_to(site)):file_hash(p) for p in sorted(site.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc"
        and not p.relative_to(site).parts[0].startswith(("legalmath",))}


def install_prepare():
    history=read(source.REVIEW/"history.json")
    old=Path(history["environment"]);old_package=history["original_package"]
    require(source.files(old/"lib/python3.11/site-packages/legalmath")==old_package,"Current434-file installed baseline changed")
    needed=sum(p.stat().st_size for p in old.rglob("*") if p.is_file())
    needed+=sum(p.stat().st_size for p in (ROOT/"src").rglob("*") if p.is_file())
    require(source.storage()+needed+64*1024**2<498*1024**2,"Measured installation cannot fit with64MiB reserve")
    temp=Path(tempfile.mkdtemp(prefix="installed-basf-pension-",dir=ROOT/".localresources/prospectus"))
    save("workspace.json",{"directory":str(temp),"cloned_from":str(old),"measured_copy_bytes":needed})
    shutil.copytree(old,temp/"environment",symlinks=True)
    (temp/"source").mkdir()
    shutil.copyfile(ROOT/"pyproject.toml",temp/"source/pyproject.toml")
    shutil.copytree(ROOT/"src",temp/"source/src",ignore=shutil.ignore_patterns("__pycache__","*.pyc","*.egg-info"))
    shutil.copyfile(RUNNER,temp/"runner.py")
    package=source.files(temp/"source/src/legalmath")
    require(all(package.get(k)==v for k,v in old_package.items()),"Preexisting source package changed")
    require(sorted(set(package)-set(old_package))==["prospectus/basf_pension_note.py","prospectus/basf_pension_spec.py"],"Unexpected package additions")
    save("source-package.json",package);save("dependency-files.json",dependencies(temp/"environment"))
    save("package-preservation.json",{"preexisting_files":len(old_package),"unchanged":True,"new_files":len(package)-len(old_package)})
    return {"source_files":len(package),"prior_files_unchanged":len(old_package),"dependency_entries":len(dependencies(temp/"environment"))}


def build():
    (HERE/"wheel").mkdir()
    source.child("build",[str(workspace()/"environment/bin/python"),"-m","pip","wheel","--no-deps","--no-build-isolation",
        "--no-index","--wheel-dir",str(HERE/"wheel"),str(workspace()/"source")])
    wheels=list((HERE/"wheel").glob("*.whl"));require(len(wheels)==1,"Exactly one offline wheel required")
    value={"path":str(wheels[0].relative_to(HERE)),"sha256":file_hash(wheels[0])}
    save("built-wheel.json",value);return value


def install():
    wheel=read(HERE/"built-wheel.json")
    require(file_hash(HERE/wheel["path"])==wheel["sha256"],"Built wheel changed")
    source.child("install",[str(workspace()/"environment/bin/python"),"-m","pip","install","--no-index","--no-deps",
        "--force-reinstall",str(HERE/wheel["path"])])
    require(dependencies(workspace()/"environment")==read(HERE/"dependency-files.json"),"Dependencies changed during installation")
    return {"installed":True,"dependencies_unchanged":True}


def replay():
    source.child("replay",[str(workspace()/"environment/bin/python"),"-I",str(workspace()/"runner.py"),str(HERE),str(ROOT)])
    return read(HERE/"installed-results/result.json")


def verify():
    value=read(HERE/"installed-results/result.json")
    require(value["status"]=="PASS" and value["complete_output_equal"] and value["earlier_outputs_unchanged"],"Installed pension result incomplete")
    require(value["process_guard"]=={"starts":0,"blocked":0},"Unexpected installed source/native execution")
    package=workspace()/"environment/lib/python3.11/site-packages/legalmath"
    expected=read(HERE/"source-package.json")
    require(source.files(package)==expected==read(HERE/"installed-results/package-files.json"),"Installed package differs")
    require(expected==source.files(ROOT/"src/legalmath"),"Current source package drift")
    require(dependencies(workspace()/"environment")==read(HERE/"dependency-files.json"),"Dependency drift")
    proof=read(HERE/"installed-results/import-proof.json")
    require(proof["isolated"]==1,"Installed process not isolated")
    for item in proof["modules"].values():
        p=Path(item["path"]).resolve()
        require(p.is_relative_to(package) and file_hash(p)==item["sha256"]==expected[str(p.relative_to(package))],"Wrong installed module identity")
    require(load(HERE/"installed-results/pension-consumer.json.gz")==load(HERE/"pension-consumer.json.gz"),"Complete installed output differs")
    require(read(HERE/"installed-results/controls.json")==read(HERE/"actual-controls.json"),"Actual installed refusals differ")
    require(len(source.process_ledger.checked(HERE/"command-ledger.json")["reservations"])==4,"Outer process count differs")
    require(len(source.process_ledger.checked(HERE/"native-ledger.json")["reservations"])==1,"Source render count differs")
    result={**read(HERE/"comparison.json"),"installed_complete_output_equal":True,"actual_refusals":value["controls"],
        "exact_package_files":len(expected),"preexisting_package_files_unchanged":434,
        "unchanged_dependency_entries":len(read(HERE/"dependency-files.json")),"outer_children":4,"native_source_renders":1,
        "new_extractions":0,"source_http_calls":0,"different_host_portability":False}
    save("verified-result.json",result);return result


def seal():
    require((HERE/"RESULT.md").is_file(),"Actual pension result analysis required")
    require(read(HERE/"verified-result.json")["status"]=="PASS","Verified pension result missing")
    require(methods()==read(HERE/"methods.json"),"Frozen pension methods changed")
    return {"validated":True,"task_complete":False,"independent_legal_acceptance":False}


if __name__=="__main__":
    stage=sys.argv[1]
    require(stage in source.STAGES[2:],"Choose admitted pension consumer stage")
    action=globals()[stage.replace("-","_")]
    def guarded():
        if stage in ("build","install","replay"):
            return action()
        with execution_guard() as guard:
            result=action()
            require(guard.result()=={"starts":0,"blocked":0},"Unexpected pension process action")
        return {**result,"process_guard":guard.result()}
    raise SystemExit(source.run(stage,guarded))
