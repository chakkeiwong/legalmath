"""Isolated closure attempts; valid evidence is distinct from criterion success."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from .contracts import digest, read, write

REL = "docs/implementation/prospectus-integration-closure"
PLAN = "docs/plans/prospectus-integration-closure-2026-10-08.md"
DAG = {"R0": [], "R1": ["R0"], "R2": ["R1"], "R3": ["R1"],
       "R4": ["R2", "R3"], "R5": ["R4"], "R6": ["R5"], "R7": ["R6"],
       "R8": ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]}
JOBS = {
    "R0": ("tests/prospectus_successor/test_closure_program.py", None),
    "R1": ("tests/prospectus_successor/test_integration_closure.py", "not solver and not z3"),
    "R2": ("tests/prospectus_successor/test_integration_closure.py", "solver or z3"),
    "R3": ("tests/prospectus_successor/test_closure_consumers.py tests/prospectus_successor/test_closure_meaning.py tests/prospectus_successor/test_closure_correction_images.py tests/prospectus_successor/test_closure_real_scan.py", "layout or poppler or correction or corrected"),
    "R4": ("tests/prospectus_successor/test_closure_consumers.py tests/prospectus_successor/test_closure_meaning.py tests/prospectus_successor/test_closure_references.py tests/prospectus_successor/test_closure_reference_replacement.py tests/prospectus_successor/test_closure_basf.py tests/prospectus_successor/test_closure_basf_notices.py tests/prospectus_successor/test_closure_basf_agent_notices.py tests/prospectus_successor/test_closure_basf_agent_capacity.py tests/prospectus_successor/test_closure_basf_global_exchange.py tests/prospectus_successor/test_closure_basf_global_records.py tests/prospectus_successor/test_closure_basf_amount_holder.py tests/prospectus_successor/test_closure_basf_status_pledge.py", "annotation or authored or disposition or priority or corrected or reference or cross_document or basf"),
    "R5": ("tests/prospectus_successor/test_closure_finance.py tests/prospectus_successor/test_closure_coupon_anchor.py tests/prospectus_successor/test_closure_consumers.py", "finance or coupon or calculation or published or bearer or schedule or selected_full"),
    "R6": ("tests/prospectus_successor/test_closure_runtime.py tests/prospectus_successor/test_closure_consumers.py tests/prospectus_successor/test_closure_recovery.py", "runtime or current_consume or missing_poppler or real_executor"),
    "R7": ("tests/prospectus_successor/test_closure_reviews.py", None),
    "R8": ("tests/prospectus_successor/test_closure_attribution.py", None),
}
REMAINING = {
    'R0': [],
    'R1': ['Broader real-document applicability/reference controls and source authentication remain conditional'],
    'R2': ['Finite controls and installed larger-domain cases do not establish unrestricted Boolean or legal completeness'],
    'R3': ['BES supplied corrections and complete qualifications pass; automatic row/qualification discovery, broader scan families and independent source review remain open'],
    'R4': ['Extend the combined BASF scalar/notice/agent consumer to remaining source meanings and onward references; B54 office authority, independent adjudication and real browser cross-document review remain open'],
    'R5': ['Independently review real-instrument conventions and broader entitlement/stub schedules; conditional Compass first coupon does not close full settlement'],
    'R6': ['Finite real OCR/XMI recovery and same-host tracing/mount-denial controls passed; complete native dependency binding, production confinement and second-host portability remain open'],
    'R7': ['Obtain actual qualified assignments, sealed first readings, adjudication and sign-offs on a frozen unexposed cohort'],
    'R8': ['Keep engineering and external acceptance separate; resolve remaining local code work and specified external inputs'],
}
PACKAGE_INPUTS = {'R3':['layout','scan','scan_de'], 'R4':['codec'], 'R5':['numeric','compass']}
# Status/pledge continuation: previous R4 2486.211s plus new admission
# (241.444s), P3 smoke (358.350s), remaining controls and scheduling headroom.
# The execution plan reviews this finite bound before the longer run.
PHASE_TIMEOUTS = {'R4': 4500}


def auxiliary_evidence(root, phase):
    """Validate preserved external exercise bytes; these are bounded diagnostics."""
    rows = []
    bases = [Path(root)/REL/'packages'/name for name in PACKAGE_INPUTS.get(phase, [])]
    if phase == 'R3':
        bases += [Path(root)/REL/'real-scan'/name for name in ('analysis', 'authoring', 'consumer')]
    if phase == 'R4':
        bases += [Path(root)/REL/name for name in ('basf-consumer', 'basf-notices', 'basf-agent-notices', 'basf-agent-capacity', 'basf-global-exchange', 'basf-global-records', 'basf-amount-holder', 'basf-status-pledge')]
    if phase == 'R6':
        bases += [Path(root)/REL/name for name in ('installed','layout-restoration','authoring-restoration')]
        bases += [Path(root)/REL/'worker-recovery'/name for name in
                  ('ocr-baseline', 'recovery-sequence', 'native-boundary')]
    for base in bases:
        attempts = sorted(base.glob('attempt-*'))
        # Installed application and separate optional-runtime evidence are distinct.
        if base.name == 'installed':
            profiles = {}
            for folder in attempts:
                if (folder/'result.json').is_file():
                    record = read(folder/'result.json')
                    profile = record.get('action') or ('application' if record.get('fresh_assess') else 'optional')
                    profiles[profile] = folder
            chosen = list(profiles.values())
        else:
            chosen = attempts[-1:]
        if not chosen:
            rows.append({'path':str(base.relative_to(root)), 'status':'MISSING'})
        for folder in chosen:
            try:
                manifest=read(folder/'manifest.json')
                result=read(folder/'result.json')
                actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
                if actual != set(manifest['files']) or any(digest((folder/p).read_bytes()) != h for p,h in manifest['files'].items()):
                    raise ValueError('Auxiliary evidence changed')
                rows.append({'path':str(folder.relative_to(root)), 'status':result['status'],
                             'manifest_sha256':digest((folder/'manifest.json').read_bytes()),
                             'scope':'Retained diagnostic at its recorded method, not current package certification'})
            except (OSError, ValueError, KeyError, TypeError):
                rows.append({'path':str(folder.relative_to(root)), 'status':'INVALID'})
    return rows


def command(*args):
    return ["python3", "-m", "scripts.prospectus_delivery", "--program", "closure", *args]


def bindings(root, phase):
    root = Path(root)
    paths = list((root / "src/legalmath/prospectus/successor").glob("*.py"))
    paths += [root / p for p in ("scripts/prospectus_delivery.py", "src/legalmath/cli.py", "pyproject.toml", PLAN)]
    paths += list((root / "tests/prospectus_successor").glob("*.py"))
    paths += list((root / 'scripts').glob('prospectus_closure_*.py'))
    paths += [root/'scripts/prospectus_integration_codec.py']
    if phase == 'R3':
        paths += [root/'docs/plans/prospectus-real-scan-2026-10-11.md']
        paths += list((root/REL/'real-scan').glob('*.py'))
        paths += [root/REL/'real-scan'/name for name in
                  ('oracle.json', 'source-review-freeze.json', 'baseline/attempt-001/manifest.json')]
    if phase == 'R4':
        paths += [root/'docs/plans/prospectus-basf-consumer-2026-10-09.md', root/REL/'basf-consumer/review.json',
                  root/'docs/plans/prospectus-basf-scalars-2026-10-09.md', root/REL/'basf-scalars/review.json',
                  root/'docs/plans/prospectus-basf-notices-2026-10-09.md', root/REL/'basf-notices/review.json',
                  root/'docs/plans/prospectus-basf-agent-notices-2026-10-10.md', root/REL/'basf-agent-notices/review.json',
                  root/'scripts/author_basf_agents_packet.py',
                  root/'docs/plans/prospectus-basf-agent-capacity-2026-10-10.md', root/REL/'basf-agent-capacity/review.json',
                  root/'scripts/author_basf_capacity_packet.py',
                  root/'docs/plans/prospectus-basf-global-exchange-2026-10-10.md', root/REL/'basf-global-exchange/review.json',
                  root/REL/'basf-global-exchange/SOURCE-REVIEW.md', root/'scripts/author_basf_global_exchange_packet.py',
                  root/'docs/plans/prospectus-basf-global-records-2026-10-10.md', root/REL/'basf-global-records/review.json',
                  root/REL/'basf-global-records/SOURCE-REVIEW.md', root/'scripts/author_basf_global_records_packet.py',
                  root/'docs/plans/prospectus-basf-amount-holder-execution-2026-10-10.md', root/REL/'basf-amount-holder/review.json',
                  root/REL/'basf-amount-holder/SOURCE-REVIEW.md', root/'scripts/author_basf_amount_holder_packet.py',
                  root/'docs/plans/prospectus-basf-status-pledge-execution-2026-10-10.md', root/REL/'basf-status-pledge/review.json',
                  root/REL/'basf-status-pledge/SOURCE-REVIEW.md', root/REL/'basf-status-pledge/OPTION-COMPARISON-CORRECTION.md',
                  root/'scripts/author_basf_status_pledge_packet.py']
    if phase == 'R5':
        paths += [root/'docs/plans/prospectus-coupon-anchor-repair-2026-10-10.md']
    if phase == 'R6':
        paths += [root/'docs/plans/prospectus-worker-recovery-2026-10-10.md']
        paths += list((root/REL/'worker-recovery').glob('*.py'))
    if phase == 'R8':
        paths += [root/REL/'attribution-review.json', root/REL/'gap-status.json']
    paths += list((root / REL / "inputs" / phase).rglob("*"))
    packages = {name: importlib.metadata.version(name) for name in ("legalmath", "pytest", "hypothesis", "z3-solver")}
    return {"files": {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(set(paths)) if p.is_file()},
            'auxiliary_evidence':auxiliary_evidence(root,phase),
            "environment": {"python": sys.version, "packages": packages, "mode": "CPU", "CUDA_VISIBLE_DEVICES": "-1",
                            "checkout_test_source": str(root / "src")}}


def preflight(root):
    return {"version": "closure-preflight.v1", "python": sys.executable,
            "cpu_gpu": "CPU; GPU intentionally hidden before imports", "gpu_probed": False,
            "executables": {name: shutil.which(name) for name in ("pdftotext", "pdfinfo", "java")},
            "runtime_paths": {str(p): p.exists() for p in (
                Path("/tmp/prospectus-adoption-tools/bin/python"), Path("/tmp/prospectus-adoption-models"))},
            "implemented_phases": sorted(JOBS), "plan": PLAN,
            "external_acceptance": "NOT_ESTABLISHED"}


def verified_attempt(root, folder):
    """A sealed receipt is the commit point; interrupted outputs remain evidence."""
    path = folder / "receipt.json"
    if not path.is_file():
        return None
    try:
        receipt = read(path)
        body = {k: v for k, v in receipt.items() if k != "sha256"}
        if receipt.get("sha256") != digest(body):
            return None
        actual = {p.name for p in folder.iterdir() if p.is_file() and p.name != "receipt.json"}
        if actual != set(receipt["outputs"]):
            return None
        for name, sha in receipt["outputs"].items():
            if Path(name).name != name or digest((folder / name).read_bytes()) != sha:
                return None
        return {**receipt, "directory": str(folder.relative_to(root))}
    except (KeyError, TypeError, ValueError, OSError):
        return None


def status(root):
    root = Path(root)
    rows = {}
    for phase, parents in DAG.items():
        attempts = [verified_attempt(root, p) for p in sorted((root / REL / "phases" / phase).glob("attempt-*"))]
        valid = [row for row in attempts if row]
        latest = valid[-1] if valid else None
        current = bool(latest and latest["method"] == digest(bindings(root, phase)) and all(
            rows[p]["current"] and latest["parents"].get(p) == rows[p]["receipt_sha256"] for p in parents))
        ready = phase in JOBS and all(rows[p]["current"] and rows[p]["engineering_checks"] == "PASS" for p in parents)
        rows[phase] = {"phase": phase, "handler_exists": phase in JOBS, "current": current,
            "artifact_valid": bool(latest), "execution": latest["execution"] if latest else "NOT_EXECUTED",
            "engineering_checks": latest["engineering_checks"] if latest else "NOT_CHECKED",
            "primary_criterion": latest["primary_criterion"] if latest else "NOT_CHECKED",
            "consumer_integration": latest["consumer_integration"] if latest else "NOT_CHECKED",
            "external_acceptance": "NOT_ESTABLISHED", "can_dispatch": ready,
            "receipt_sha256": latest["sha256"] if latest else None,
            "directory": latest["directory"] if latest else None,
            "remaining": latest.get("remaining", []) if latest else ["Implement and validate the phase handler"],
            "command": command("phase", "--phase", phase)}
    return {"version": "closure-status.v1", "phases": list(rows.values()), "automatic_release": False}


@contextmanager
def lock(root):
    folder = Path(root) / REL
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "controller.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def _refresh(root):
    result = status(root)
    result["next_command"] = next((r["command"] for r in result["phases"]
        if r["can_dispatch"] and not r["current"]), None)
    result['unfinished_capabilities']=[{'phase':r['phase'],'gaps':REMAINING[r['phase']],
        'action':'Repair code or acquire the specified evidence before rerunning; a current partial receipt is not completion'}
        for r in result['phases'] if REMAINING[r['phase']]]
    result['program_complete']=False
    if result['next_command'] is None:
        result['next_action']='Follow NEXT-PROGRAM.md: expand real source cases, validate native restrictions and obtain independent review; passing partial receipts does not finish these repairs'
    result["review"] = "Failed criteria require a changed repair; valid partial evidence may feed a reviewed path."
    write(Path(root) / REL / "next-phase.json", result)
    return result


def refresh(root):
    with lock(root):
        return _refresh(Path(root))


def execute(root, phase):
    root = Path(root)
    if phase not in DAG:
        raise ValueError("Unknown closure phase")
    with lock(root):
        before = status(root)
        row = next(r for r in before["phases"] if r["phase"] == phase)
        if row["current"] and row["engineering_checks"] == "PASS":
            return {**row, "reused": True}
        if not row["can_dispatch"]:
            return {**row, "execution": "HANDLER_OR_DEPENDENCY_MISSING"}
        method_inputs = bindings(root, phase)
        method = digest(method_inputs)
        base = root / REL / "phases" / phase
        previous = sorted(base.glob("attempt-*"))
        identical = [p for p in previous if (p / "started.json").exists() and read(p / "started.json")["method"] == method]
        if identical:
            raise ValueError("Unchanged failed/interrupted input requires a recorded repair before retry")
        folder = base / f"attempt-{len(previous)+1:03d}"
        folder.mkdir(parents=True)
        started = time.monotonic()
        parents = {r["phase"]: r["receipt_sha256"] for r in before["phases"] if r["phase"] in DAG[phase]}
        test_paths = JOBS[phase][0].split()
        argv = [sys.executable, "-m", "pytest", "-q", *test_paths, "--junitxml=" + str(folder / "tests.xml")]
        if JOBS[phase][1]:
            argv += ["-k", JOBS[phase][1]]
        record = {"phase": phase, "method": method, "bindings": method_inputs, "parents": parents,
                  "argv": argv, "plan": PLAN, "started_at": datetime.now(timezone.utc).isoformat(),
                  "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                  "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1", "random_seeds": "Deterministic fixtures; Hypothesis stores counterexamples",
                  "timeout_seconds": PHASE_TIMEOUTS.get(phase, 600)}
        write(folder / "started.json", record)
        try:
            run = subprocess.run(argv, cwd=root, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1",
                                 "PYTHONPATH": str(root / "src") + os.pathsep + str(root)},
                                 capture_output=True, timeout=record['timeout_seconds'])
            (folder / "command.log").write_bytes(run.stdout + run.stderr)
            suites = ET.parse(folder / "tests.xml").getroot()
            counts = {k: sum(int(s.get(k, 0)) for s in suites.iter("testsuite")) for k in ("tests", "failures", "errors", "skipped")}
            passed = run.returncode == 0 and counts["tests"] > 0 and not any(counts[k] for k in ("failures", "errors", "skipped"))
            if digest(bindings(root, phase)) != method:
                raise ValueError("Method or inputs changed during phase")
            auxiliary=method_inputs['auxiliary_evidence']
            if any(r['status'] != 'PASS' for r in auxiliary):
                passed=False
            if passed and phase == 'R8':
                from scripts.prospectus_closure_attribution import report
                write(folder/'attribution.json', report(root))
            pending = REMAINING[phase]
            result = {"execution": "COMPLETED" if run.returncode == 0 else "FAILED", "test_counts": counts,
                      "engineering_checks": "PASS" if passed else "FAIL",
                      "primary_criterion": ("PARTIAL" if pending else "PASS") if passed else "FAIL",
                      "consumer_integration": "SERVICE_TESTED" if passed and phase not in {"R0","R8"} else "NOT_APPLICABLE",
                      'auxiliary_evidence':auxiliary,
                      'dependency_assurance':'DECLARED_METHOD_AND_INPUTS_ONLY; native reads not confined',
                      "remaining": pending if passed else ["Repair the failing checks before repeating this phase"]}
        except Exception as exc:
            result = {"execution": "FAILED", "engineering_checks": "FAIL", "primary_criterion": "INVALID_RUN",
                      "consumer_integration": "NOT_CHECKED", "remaining": [type(exc).__name__ + ": " + str(exc)]}
        result.update(phase=phase, wall_seconds=time.monotonic() - started, external_acceptance="NOT_ESTABLISHED")
        write(folder / "result.json", result)
        receipt = {**result, "method": method, "parents": parents,
                   "outputs": {p.name: digest(p.read_bytes()) for p in folder.iterdir() if p.is_file()}}
        write(folder / "receipt.json", {**receipt, "sha256": digest(receipt)})
        _refresh(root)
        return {**result, "directory": str(folder.relative_to(root)), "reused": False}
