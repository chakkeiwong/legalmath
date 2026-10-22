"""Isolated closure attempts; valid evidence is distinct from criterion success."""
from contextlib import contextmanager
import ast
from datetime import datetime, timezone
import fcntl
import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
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
    "R3": ("tests/prospectus_successor/test_closure_consumers.py tests/prospectus_successor/test_closure_meaning.py tests/prospectus_successor/test_closure_correction_images.py tests/prospectus_successor/test_closure_real_scan.py tests/prospectus_successor/test_ocr_geometry.py", "layout or poppler or correction or corrected or geometry"),
    "R4": ("tests/prospectus_successor/test_closure_consumers.py tests/prospectus_successor/test_closure_meaning.py tests/prospectus_successor/test_closure_references.py tests/prospectus_successor/test_closure_reference_replacement.py tests/prospectus_successor/test_closure_basf.py tests/prospectus_successor/test_closure_basf_notices.py tests/prospectus_successor/test_closure_basf_agent_notices.py tests/prospectus_successor/test_closure_basf_agent_capacity.py tests/prospectus_successor/test_closure_basf_global_exchange.py tests/prospectus_successor/test_closure_basf_global_records.py tests/prospectus_successor/test_closure_basf_amount_holder.py tests/prospectus_successor/test_closure_basf_status_pledge.py tests/prospectus_successor/test_report_scope.py tests/prospectus_successor/test_archive_observations.py tests/prospectus_successor/test_governing_interpretation.py tests/prospectus_successor/test_meaning_coverage.py tests/prospectus_successor/test_relation_discovery.py tests/prospectus_successor/test_relation_scope.py", "annotation or authored or disposition or priority or corrected or reference or cross_document or basf or report_scope or archive_observations or governing_interpretation or meaning_coverage or relation_discovery or relation_scope"),
    "R5": ("tests/prospectus_successor/test_closure_finance.py tests/prospectus_successor/test_closure_coupon_anchor.py tests/prospectus_successor/test_initial_coupon.py tests/prospectus_successor/test_closure_consumers.py", "finance or coupon or calculation or published or bearer or schedule or selected_full"),
    "R6": ("tests/prospectus_successor/test_closure_runtime.py tests/prospectus_successor/test_closure_consumers.py tests/prospectus_successor/test_closure_recovery.py tests/prospectus_successor/test_native_inputs.py", "runtime or current_consume or missing_poppler or real_executor or native_inputs"),
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
BINDING_VERSION = "closure-bindings.v3"
PHASE_SUPPORT = {
    "R1": ["tests/prospectus_successor/test_successor.py"],
    "R2": ["tests/prospectus_successor/test_successor.py"],
    "R3": ["tests/prospectus_successor/test_successor.py", "scripts/prospectus_closure_fixtures.py"],
    "R4": ["tests/prospectus_successor/test_successor.py", "scripts/prospectus_closure_fixtures.py"],
    "R5": ["scripts/prospectus_closure_fixtures.py"],
    "R6": ["scripts/prospectus_closure_fixtures.py"],
    "R7": ["scripts/prospectus_closure_fixtures.py"],
    "R8": ["scripts/prospectus_closure_attribution.py"],
}
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
            invalid = []
            for folder in attempts:
                if (folder/'result.json').is_file():
                    try:
                        record = read(folder/'result.json')
                        if not isinstance(record, dict):
                            raise ValueError('Installed result is not a record')
                        profile = record.get('action') or ('application' if record.get('fresh_assess') else 'optional')
                        profiles[profile] = folder
                    except (OSError, ValueError, TypeError):
                        invalid.append(folder)
                else:
                    invalid.append(folder)
            chosen = sorted(set(profiles.values()) | set(invalid))
        else:
            chosen = attempts[-1:]
        if not chosen:
            rows.append({'path':str(base.relative_to(root)), 'status':'MISSING'})
        for folder in chosen:
            try:
                manifest=read(folder/'manifest.json')
                result=read(folder/'result.json')
                if (not isinstance(manifest, dict) or not isinstance(manifest.get('files'), dict)
                        or not isinstance(result, dict)):
                    raise ValueError('Auxiliary record has an invalid shape')
                actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
                if actual != set(manifest['files']) or any(digest((folder/p).read_bytes()) != h for p,h in manifest['files'].items()):
                    raise ValueError('Auxiliary evidence changed')
                rows.append({'path':str(folder.relative_to(root)), 'status':result['status'],
                             'manifest_sha256':digest((folder/'manifest.json').read_bytes()),
                             'scope':'Retained diagnostic at its recorded method, not current package certification'})
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                rows.append({'path':str(folder.relative_to(root)), 'status':'INVALID'})
    return rows


def command(*args):
    return ["python3", "-m", "scripts.prospectus_delivery", "--program", "closure", *args]


def phase_test_paths(root, phase):
    root = Path(root)
    paths = [root / value for value in JOBS[phase][0].split()]
    paths += [root / value for value in PHASE_SUPPORT.get(phase, [])]
    # Pytest loads these without an explicit import in a selected test module.
    paths += [root / value for value in ("tests/__init__.py", "tests/conftest.py",
                                         "tests/prospectus_successor/conftest.py")]
    if phase == "R4":
        paths += sorted((root / "scripts").glob("prospectus_closure_basf*.py"))
    return paths


def local_module_index(root):
    """Index importable project modules for phase-scoped dependency closure."""
    root = Path(root)
    index = {}
    for base, prefix in ((root / "src", ""), (root / "scripts", "scripts"),
                         (root / "tests/prospectus_successor", "")):
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            parts = path.relative_to(base).with_suffix("").parts
            parts = parts[:-1] if parts[-1] == "__init__" else parts
            if prefix:
                module = ".".join((prefix, *parts))
            elif base == root / "src":
                module = ".".join(parts)
            else:
                module = ".".join(("tests", "prospectus_successor", *parts))
            index.setdefault(module, path)
            if base == root / "tests/prospectus_successor" and len(parts) == 1:
                index.setdefault(parts[0], path)
    return index


def imported_project_files(root, initial):
    """Return initial files plus their local Python import closure."""
    root = Path(root)
    index = local_module_index(root)
    queue = [Path(path) for path in initial if Path(path).is_file()]
    seen = set()
    result = set()

    def include_module(name):
        # Importing a child also executes each regular package initializer.
        while name:
            candidate = index.get(name)
            if candidate is not None:
                queue.append(candidate)
            name = name.rpartition(".")[0]

    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        result.add(path)
        if path.suffix != ".py":
            continue
        module = next((name for name, candidate in index.items() if candidate == path), "")
        package = (module if path.name == "__init__.py" else module.rpartition(".")[0])
        include_module(module)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = package.split(".") if package else []
                    base_parts = parts[:len(parts)-node.level+1]
                    base = ".".join(base_parts + ([base] if base else []))
                names.append(base)
                names.extend((base + "." + alias.name).strip(".") for alias in node.names)
        for name in names:
            include_module(name)
    return result


def packaging_binding(root):
    """Bind executable build, project and pytest choices; omit known unrelated data."""
    path = Path(root) / "pyproject.toml"
    if not path.is_file():
        return {"status": "MISSING", "path": "pyproject.toml"}
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {"status": "INVALID", "error": type(exc).__name__}
    try:
        document = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return {"status": "INVALID", "error": type(exc).__name__, "raw_sha256": digest(raw)}
    tool = document.get("tool", {})
    project = document.get("project", {})
    build = document.get("build-system", {})
    if not all(isinstance(value, dict) for value in (tool, project, build)):
        return {"status": "INVALID", "error": "SECTION_TYPE", "raw_sha256": digest(raw)}
    if (any(key in project and not isinstance(project[key], str) for key in
            ("name", "version", "requires-python")) or
            any(key in project and (not isinstance(project[key], list) or
                any(not isinstance(value, str) for value in project[key]))
                for key in ("dependencies", "dynamic"))):
        return {"status": "INVALID", "error": "PROJECT_TYPE", "raw_sha256": digest(raw)}
    setuptools = tool.get("setuptools", {})
    pytest = tool.get("pytest", {})
    if not isinstance(setuptools, dict) or not isinstance(pytest, dict):
        return {"status": "INVALID", "error": "TOOL_TYPE", "raw_sha256": digest(raw)}
    package_data = setuptools.get("package-data", {})
    if not isinstance(package_data, dict) or any(
            not isinstance(name, str) or not isinstance(patterns, list) or
            any(not isinstance(pattern, str) for pattern in patterns)
            for name, patterns in package_data.items()):
        return {"status": "INVALID", "error": "PACKAGE_DATA_TYPE", "raw_sha256": digest(raw)}
    retained_data = {name: sorted(pattern for pattern in patterns
                                 if not (name == "legalmath" and pattern.startswith("interpretation/")))
                     for name, patterns in package_data.items()
                     if name != "legalmath.interpretation" and not name.startswith("legalmath.interpretation.")}
    result = {
        "status": "VALID",
        "build_system": build,
        "project": project,
        "setuptools": {**setuptools, "package-data": retained_data},
        "pytest": pytest,
    }
    try:
        digest(result)
    except (ValueError, TypeError):
        return {"status": "INVALID", "error": "NON_JSON_CONFIGURATION", "raw_sha256": digest(raw)}
    return result


def package_versions():
    versions = {}
    for name in ("legalmath", "pytest", "hypothesis", "z3-solver"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "MISSING"
    return versions


def bindings(root, phase):
    root = Path(root)
    from .native_inputs import environment_bindings, file_state
    interpreter = os.environ.get("LEGALMATH_OCR_PYTHON", str(root / ".localresources/prospectus/ocr/bin/python"))
    try:
        ocr_runtime = file_state(interpreter)
    except (OSError, ValueError, RuntimeError) as exc:
        ocr_runtime = {"path": interpreter, "state": "UNAVAILABLE", "error": type(exc).__name__}
    paths = list((root / "src/legalmath/prospectus/successor").glob("*.py"))
    paths += list((root / "src/legalmath/prospectus/successor").glob("*.json"))
    paths += [root / p for p in ("scripts/prospectus_delivery.py", PLAN)]
    if phase == "R6":
        paths.append(root / "src/legalmath/cli.py")
    paths += phase_test_paths(root, phase)
    if phase == "R4":
        paths += [root / "scripts/prospectus_integration_codec.py"]
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
    paths = list(imported_project_files(root, paths))
    required = ["scripts/prospectus_delivery.py", PLAN, "src/legalmath/prospectus/successor/closure_program.py",
                *JOBS[phase][0].split()]
    if phase == "R4":
        required.append("src/legalmath/prospectus/successor/basf_scope_review.json")
    if phase == "R6":
        required.append("src/legalmath/cli.py")
    packaging = packaging_binding(root)
    issues = ["Missing required input: " + value for value in required if not (root / value).is_file()]
    if packaging["status"] != "VALID":
        issues.append("Invalid prospectus packaging/pytest configuration: " + packaging["status"])
    return {"binding_version": BINDING_VERSION,
            "files": {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(set(paths)) if p.is_file()},
            "packaging": packaging, "binding_issues": issues,
            'auxiliary_evidence':auxiliary_evidence(root,phase),
            "environment": {"python": sys.version, "packages": package_versions(), "mode": "CPU", "CUDA_VISIBLE_DEVICES": "-1",
                            "selected_native_environment": environment_bindings(), "ocr_interpreter": ocr_runtime,
                            "checkout_test_source": str(root / "src")}}


def preflight(root):
    return {"version": "closure-preflight.v1", "python": sys.executable,
            "binding_version": BINDING_VERSION, "packaging_binding": packaging_binding(root),
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
        if (not isinstance(receipt, dict) or
                not isinstance(receipt.get("outputs"), dict) or
                not isinstance(receipt.get("parents"), dict) or
                not isinstance(receipt.get("remaining"), list) or
                receipt.get("phase") != folder.parent.name or
                not all(isinstance(receipt.get(key), str) for key in
                        ("method", "execution", "engineering_checks", "primary_criterion", "consumer_integration")) or
                "result.json" not in receipt["outputs"] or
                not all(isinstance(name, str) and isinstance(sha, str)
                            for name, sha in receipt["outputs"].items())):
            return None
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
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return None


def unchanged_attempt(folder, method, parents):
    """Return whether a prior attempt has the identical method/parent state."""
    try:
        record = read(Path(folder) / "started.json")
    except (OSError, ValueError, TypeError):
        return True  # An unidentifiable interrupted attempt needs review.
    if not isinstance(record, dict):
        return True
    if not isinstance(record.get("method"), str) or not isinstance(record.get("parents", {}), dict):
        return True
    return record.get("method") == method and record.get("parents", {}) == parents


def status(root):
    root = Path(root)
    rows = {}
    for phase, parents in DAG.items():
        attempt_paths = sorted((root / REL / "phases" / phase).glob("attempt-*"))
        latest_path = attempt_paths[-1] if attempt_paths else None
        latest = verified_attempt(root, latest_path) if latest_path else None
        invalid_latest = latest_path is not None and latest is None
        method_inputs = bindings(root, phase)
        method = digest(method_inputs)
        parent_receipts = {p: rows[p]["receipt_sha256"] for p in parents}
        current = bool(latest and not method_inputs["binding_issues"] and
            latest["method"] == method and all(
            rows[p]["current"] and latest["parents"].get(p) == rows[p]["receipt_sha256"] for p in parents))
        retry_blocked = not (current and latest["engineering_checks"] == "PASS") and any(
            unchanged_attempt(path, method, parent_receipts) for path in attempt_paths)
        ready = phase in JOBS and not method_inputs["binding_issues"] and all(
            rows[p]["current"] and rows[p]["engineering_checks"] == "PASS" for p in parents) and not retry_blocked
        rows[phase] = {"phase": phase, "handler_exists": phase in JOBS, "current": current,
            "artifact_valid": bool(latest),
            "execution": latest["execution"] if latest else ("INVALID_ATTEMPT" if invalid_latest else "NOT_EXECUTED"),
            "engineering_checks": latest["engineering_checks"] if latest else "NOT_CHECKED",
            "primary_criterion": latest["primary_criterion"] if latest else "NOT_CHECKED",
            "consumer_integration": latest["consumer_integration"] if latest else "NOT_CHECKED",
            "external_acceptance": "NOT_ESTABLISHED", "can_dispatch": ready,
            "binding_issues": method_inputs["binding_issues"],
            "retry_blocked": retry_blocked,
            "receipt_sha256": latest["sha256"] if latest else None,
            "directory": latest["directory"] if latest else (str(latest_path.relative_to(root)) if latest_path else None),
            "remaining": latest.get("remaining", []) if latest else
                        (["Newest attempt is invalid or incomplete; record a changed repair before retry"]
                         if invalid_latest else ["Implement and validate the phase handler"]),
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
        blocked = [r for r in result['phases'] if r['binding_issues'] or
                   r['retry_blocked'] or
                   (r['current'] and r['engineering_checks'] != 'PASS') or
                   r['execution'] == 'INVALID_ATTEMPT']
        result['next_action'] = ("Review blocked or invalid phase evidence: " +
            ", ".join(r['phase'] for r in blocked)) if blocked else (
            'Follow NEXT-PROGRAM.md: expand real source cases, validate native restrictions and obtain independent review; passing partial receipts does not finish these repairs')
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
        if row["retry_blocked"]:
            return {**row, "execution": "REPAIR_REQUIRED"}
        if not row["can_dispatch"]:
            return {**row, "execution": "HANDLER_OR_DEPENDENCY_MISSING"}
        method_inputs = bindings(root, phase)
        if method_inputs["binding_issues"]:
            raise ValueError("; ".join(method_inputs["binding_issues"]))
        method = digest(method_inputs)
        base = root / REL / "phases" / phase
        parents = {r["phase"]: r["receipt_sha256"] for r in before["phases"] if r["phase"] in DAG[phase]}
        previous = sorted(base.glob("attempt-*"))
        identical = [p for p in previous if unchanged_attempt(p, method, parents)]
        if identical:
            raise ValueError("Unchanged failed/interrupted input and parent receipts require a recorded repair before retry")
        folder = base / f"attempt-{len(previous)+1:03d}"
        folder.mkdir(parents=True)
        started = time.monotonic()
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
