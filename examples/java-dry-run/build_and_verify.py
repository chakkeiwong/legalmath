"""Generate, compile, package, execute and compare the actual Java decision code."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import sys

from compile_java import compile_bundle, java_string as js
from prepare import build, AT, EARLY, LATE
from reference import evaluate, consent, canonical, digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PKG = "hk.legalmath.spi."


def read(name):
    return json.loads((HERE / "spec" / name).read_text())


def call(args):
    return subprocess.run([str(a) for a in args], cwd=HERE, check=True, text=True, capture_output=True).stdout


def fact(f):
    if f["status"] == "unknown":
        return f'Fact.unknown({js(f["type"])}, {js(f["reason"])})'
    ids = "List.of(" + ",".join(js(x) for x in f.get("evidence_ids", [])) + ")"
    if f["status"] == "conflict":
        return f'Fact.conflict({js(f["type"])}, {ids})'
    value = str(f["value"]).lower() if f["type"] == "bool" else f'new BigInteger({js(f["value"])})'
    return f'Fact.known({js(f["type"])}, {value}, {ids}, {js(f["valid_from"])}, {js(f["valid_until"])}, {js(f["recorded_at"])})'


def snapshot(s):
    return 'new Snapshot('+js(s["subject_id"])+', Map.ofEntries(\n'+",\n".join(
        'Map.entry('+js(n)+', '+fact(f)+')' for n,f in sorted(s["facts"].items()))+'))'


def event(e):
    return 'new ConsentReplay.Event('+','.join(js(e[k]) for k in ("id","kind","occurred_at","recorded_at"))+','+str(e["sequence"])+')'


def java_inputs(cases, events):
    header = 'package hk.legalmath.spi;\nimport java.util.*;\nimport java.math.BigInteger;\nimport static hk.legalmath.spi.DecisionRuntime.*;\n'
    lines = [header, 'public final class FixtureRunner {', 'public static void main(String[] args) {']
    for c in cases:
        lines += ['System.out.println('+js(c["id"]+"\t")+'+GeneratedSpi.evaluate('+snapshot(c["snapshot"])+','+js(c["valid_at"])+','+js(c["known_at"])+').json());']
    for c in events:
        expr='ConsentReplay.replay(List.of('+','.join(event(e) for e in c["events"])+'),'+','.join(js(c[k]) for k in ("valid_at","known_at","complete_through","completeness_recorded_at"))+')'
        lines += ['System.out.println('+js(c["id"]+"\t")+'+DecisionRuntime.json('+expr+'));']
    lines += ['}', '}']
    (HERE / "generated/FixtureRunner.java").write_text('\n'.join(lines)+'\n')
    # This separate caller uses only the library's public API and is not in the JAR.
    h = [header, 'public final class BankHostExample {',
         'public static void main(String[] args) {',
         'var snapshot = '+snapshot(cases[0]["snapshot"])+ ';',
         'var before = GeneratedSpi.evaluate(snapshot,'+js(AT)+','+js(AT)+');',
         'System.out.println("BEFORE_WITHDRAWAL " + before.disposition());',
         'var consent = ConsentReplay.replay(List.of('+','.join(event(e) for e in events[1]["events"])+'), "2026-09-21T02:10:00.000000Z", "2026-09-21T02:10:00.000000Z", "2026-09-21T02:10:00.000000Z", "2026-09-21T02:10:00.000000Z");',
         'if (!consent.equals("FALSE")) throw new AssertionError("withdrawal replay");',
         'snapshot = snapshot.with("active_consent", Fact.known("bool", false, List.of("consent.withdraw.1"), "2026-09-21T02:05:00.000000Z", null, "2026-09-21T02:06:00.000000Z"));',
         'var after = GeneratedSpi.evaluate(snapshot,"2026-09-21T02:10:00.000000Z","2026-09-21T02:10:00.000000Z");',
         'System.out.println("AFTER_WITHDRAWAL " + after.disposition());',
         'if (!after.status().equals("FALSE")) throw new AssertionError("consent omitted");',
         'System.out.println("RESULT_AUTHORITY DEMONSTRATION_ONLY");', '}', '}']
    (HERE / "generated/BankHostExample.java").write_text('\n'.join(h)+'\n')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--jdk", type=Path, required=True, help="Directory containing bin/javac and bin/java")
    args=parser.parse_args()
    jdk=args.jdk.resolve(); javac=jdk/"bin/javac"; java=jdk/"bin/java"; jar=jdk/"bin/jar"
    start=time.monotonic()
    build()
    bundle=read("spi-control.bundle.json"); cases=read("decision-cases.json"); events=read("consent-cases.json")
    for span in bundle["source_spans"]:
        stem="23EC35-"+span["source_id"].split("/")[-1]
        source_text=(ROOT/".localresources/sfc"/(stem+".txt")).read_text().removeprefix("\ufeff").replace("\r\n","\n")
        source_pdf=(ROOT/".localresources/sfc"/(stem+".pdf")).read_bytes()
        assert span["raw_sha256"]==hashlib.sha256(source_pdf).hexdigest()
        assert span["text_sha256"]==hashlib.sha256(source_text.encode()).hexdigest()
        assert span["quote_sha256"]==hashlib.sha256(source_text[span["start"]:span["end"]].encode()).hexdigest()
        assert source_text[:span["start"]].count("\f")+1==span["page"]
    reference={}
    for c in cases:
        v=evaluate(bundle,c["snapshot"],c["valid_at"],c["known_at"])
        assert v["status"]==c["expected_status"], (c["id"],v)
        assert v["blocking_inputs"]==c["expected_blocking_inputs"], (c["id"],v)
        reference[c["id"]]=v
    for c in events:
        v=consent(c["events"],c["valid_at"],c["known_at"],c["complete_through"],c["completeness_recorded_at"])
        assert v==c["expected"], (c["id"],v)
        reference[c["id"]]=v
    generated=compile_bundle(bundle)
    (HERE/"generated/GeneratedSpi.java").write_text(generated)
    assert generated == compile_bundle(deepcopy(bundle)), "Nondeterministic emitter"
    java_inputs(cases,events)
    support=sorted((HERE/"src/main/java").rglob("*.java"))
    classes=HERE/"build/classes"; classes.mkdir(parents=True,exist_ok=True)
    compile_cmd=[javac,"--release","17","-Xlint:all","-Werror","-d",classes,*support,HERE/"generated/GeneratedSpi.java"]
    call(compile_cmd)
    jarfile=HERE/"build/spi-controls-demo.jar"
    call([jar,"--create","--file",jarfile,"--date=2026-09-21T00:00:00Z","-C",classes,"."])
    with tempfile.TemporaryDirectory(prefix="spi-rebuild-") as tmp:
        tmp=Path(tmp);fresh=tmp/"classes";fresh.mkdir()
        call([javac,"--release","17","-Xlint:all","-Werror","-d",fresh,*support,HERE/"generated/GeneratedSpi.java"])
        call([jar,"--create","--file",tmp/"repeat.jar","--date=2026-09-21T00:00:00Z","-C",fresh,"."])
        assert jarfile.read_bytes()==(tmp/"repeat.jar").read_bytes(), "Nonreproducible Java build"
    clients=HERE/"build/clients";clients.mkdir(exist_ok=True)
    call([javac,"--release","17","-Xlint:all","-Werror","-cp",jarfile,"-d",clients,HERE/"generated/FixtureRunner.java",HERE/"generated/BankHostExample.java"])
    output=call([java,"-cp",str(jarfile)+":"+str(clients),PKG+"FixtureRunner"])
    actual={k:json.loads(v) for k,v in (line.split("\t",1) for line in output.splitlines())}
    assert actual==reference, [(k,actual.get(k),v) for k,v in reference.items() if actual.get(k)!=v]
    host=call([java,"-cp",str(jarfile)+":"+str(clients),PKG+"BankHostExample"])
    (HERE/"build/host-output.txt").write_text(host)
    (HERE/"build/decision-results.json").write_text(json.dumps(actual,indent=2)+"\n")
    mutants=[]
    for name in ("strict_portfolio_boundary","conjoined_wealth_routes","consent_bypassed"):
        b=deepcopy(bundle)
        if name=="strict_portfolio_boundary":b["rules"][0]["body"]["args"][0]["cmp"]="gt"
        elif name=="conjoined_wealth_routes":b["rules"][0]["body"]["op"]="all"
        else:
            target=next(r for r in b["rules"] if r["id"]=="spi.arrangement")["body"]["args"]
            i=next(i for i,n in enumerate(target) if n.get("name")=="active_consent")
            target[i]=dict(node_id="mutant.any",op="any",args=[target[i],dict(node_id="mutant.true",op="literal",type="bool",value=True)])
        path=HERE/"build/mutations"/name;path.mkdir(parents=True,exist_ok=True)
        (path/"GeneratedSpi.java").write_text(compile_bundle(b))
        call([javac,"--release","17","-cp",jarfile,"-d",path,path/"GeneratedSpi.java"])
        out=call([java,"-cp",str(path)+":"+str(jarfile)+":"+str(clients),PKG+"FixtureRunner"])
        mutated={k:json.loads(v) for k,v in (line.split("\t",1) for line in out.splitlines())}
        caught=[c["id"] for c in cases if mutated[c["id"]]["status"]!=c["expected_status"]]
        assert caught, name
        mutants.append(dict(mutation=name,caught_by=caught))
    # A typed, schema-valid but unsupported operation must fail compilation.
    unsupported=deepcopy(bundle)
    unsupported["rules"][0]["body"]["args"][0]["left"]={"node_id":"unsupported.scale","op":"scale","arg":unsupported["rules"][0]["body"]["args"][0]["left"],"numerator":"1","denominator":"1"}
    try:compile_bundle(unsupported)
    except ValueError as e:assert str(e).startswith("E_UNSUPPORTED"), str(e)
    else:raise AssertionError("unsupported operation compiled")
    javap=call([jdk/"bin/javap","-verbose","-cp",jarfile,PKG+"GeneratedSpi"])
    assert "major version: 61" in javap
    hashed={}
    for p in [*sorted((HERE/"spec").glob("*.json")),*sorted((HERE/"generated").glob("*.java")),jarfile,*support,HERE/"prepare.py",HERE/"compile_java.py",HERE/"reference.py",HERE/"build_and_verify.py"]:
        hashed[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    report=dict(profile="SPI-Demo1", authority="DEMONSTRATION_ONLY", decision_cases=len(cases),consent_cases=len(events),
                full_result_differential_comparison="PASS", mutations=mutants,unsupported_operation_rejected=True,
                separate_host_against_jar="PASS",reproducible_fresh_java_build="PASS",source_spans_verified=len(bundle["source_spans"]),compiler=call([javac,"-version"]).strip(),java_class_major=61,
                command=f"python3 examples/java-dry-run/build_and_verify.py --jdk {jdk}",
                executed_at_utc=datetime.now(timezone.utc).isoformat(),
                environment=dict(python=sys.version.split()[0],jsonschema=version("jsonschema"),accelerator_use="none; CPU-only Java and document checks",git_commit="N/A: not a Git repository",seed="N/A: deterministic fixtures"),
                jdk_archive_sha256="3808d1d15e3ec6bd5b84057fb5d84c33d8a1536a258146bcea2e603fc726e08e" if jdk.name=="jdk-17.0.20.1+1" else "not recorded for supplied alternate JDK",
                wall_seconds=round(time.monotonic()-start,3),sha256=hashed,
                not_implemented=["complete RuleIR 0.1 runtime","legal approval","source-to-rule language model","reviewer workbench","production host adapter","formal compiler proof"])
    (HERE/"build/verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("decision_cases","consent_cases","full_result_differential_comparison","separate_host_against_jar","compiler")},indent=2))
    print(host,end="")


if __name__=="__main__":main()
