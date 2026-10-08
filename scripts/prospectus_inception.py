"""Bounded, localhost-only INCEpTION 38 integration and evidence retention."""
import argparse
import base64
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import signal
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
LOCAL = ROOT / ".localresources/prospectus-inception"
OUT = ROOT / "docs/implementation/prospectus-inception"
PLAN = "docs/plans/prospectus-inception-integration-2026-10-07.md"
JAR_NAME = "inception-app-webapp-38.0-standalone.jar"
JAR_SHA = "6c0b54c262a36d6ccaaa2e37796bc728c656fdf8ea0ae40c7854cb54bdb9c876"
JAR_URL = "https://github.com/inception-project/inception/releases/download/inception-38.0/" + JAR_NAME
SOURCE_URL = "https://github.com/inception-project/inception/archive/refs/tags/inception-38.0.tar.gz"
JAVA = ROOT / ".localresources/java-toolchain/jdk-17.0.20.1+1/bin/java"
API = "/api/aero/v1"


class LocalRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        before, after = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if (after.scheme, after.netloc) != (before.scheme, before.netloc):
            raise ValueError("Redirect outside isolated server refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def storage_bytes():
    return sum(p.stat().st_size for root in (LOCAL, OUT) for p in root.rglob("*") if p.is_file())


def check_storage():
    if storage_bytes() > 2_000_000_000:
        raise RuntimeError("Integration storage exceeds reviewed 2 GB bound")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def fetch(url, path, maximum):
    if path.exists():
        return
    partial = path.with_suffix(path.suffix + ".partial")
    ledger_path = LOCAL / "download-budget.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    if sum(row["reserved_requests"] for row in ledger) + 6 > 30 or sum(row["reserved_bytes"] for row in ledger) + maximum > 800_000_000:
        raise RuntimeError("Download budget exhausted; review before further fetches")
    ledger.append({"url": url, "reserved_requests": 6, "reserved_bytes": maximum})
    save(ledger_path, ledger)
    command = ["curl", "--fail", "--location", "--silent", "--show-error",
               "--max-redirs", "5",
               "--connect-timeout", "12", "--max-time", "300", "--max-filesize", str(maximum),
               "--output", str(partial), url]
    subprocess.run(command, check=True, timeout=315)
    partial.replace(path)


def runtime_identity():
    sidecar = "/tmp/prospectus-adoption-tools/bin/python"
    probe = "import cassis,importlib.metadata,json,hashlib,pathlib; p=pathlib.Path(cassis.__file__).parent; print(json.dumps({'version':importlib.metadata.version('dkpro-cassis'),'files':{str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob('*.py'))}}))"
    package = json.loads(subprocess.check_output([sidecar, "-c", probe], text=True, timeout=15))
    if package["version"] != "0.10.1":
        raise ValueError("Reviewed Cassis 0.10.1 sidecar required")
    browser = Path("/home/chakwong/python/legalmath/.localresources/browser/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell")
    return {"cassis": package, "sidecar_python": file_sha(sidecar), "application_python": file_sha(sys.executable),
            "java": file_sha(JAVA), "jar": file_sha(LOCAL/JAR_NAME), "browser": file_sha(browser)}


def prepare():
    LOCAL.mkdir(parents=True, exist_ok=True)
    (OUT / "sources").mkdir(parents=True, exist_ok=True)
    metadata = OUT / "sources/release.json"
    if not metadata.exists() and Path("/tmp/inception38-release.json").exists():
        shutil.copyfile("/tmp/inception38-release.json", metadata)
    fetch("https://api.github.com/repos/inception-project/inception/releases/tags/inception-38.0", metadata, 2_000_000)
    release = json.loads(metadata.read_text())
    asset = next(a for a in release["assets"] if a["name"] == JAR_NAME)
    if release["tag_name"] != "inception-38.0" or asset["digest"] != "sha256:" + JAR_SHA:
        raise ValueError("Release identity changed")
    fetch(JAR_URL, LOCAL / JAR_NAME, 400_000_000)
    if file_sha(LOCAL / JAR_NAME) != JAR_SHA:
        raise ValueError("Official INCEpTION release checksum mismatch")
    fetch(SOURCE_URL, LOCAL / "inception-38.0-source.tar.gz", 100_000_000)
    source_names = ["remote-api.adoc", "AeroProjectController.java", "AeroAnnotationController.java",
                    "AeroDocumentController.java", "SecurityProperties.java", "ExportedAnnotationLayer.java",
                    "ExportedAnnotationFeature.java", "LayerExporter.java", "CurationWorkflowExporter.java",
                    "ThresholdBasedMergeStrategy.java", "ThresholdBasedMergeStrategyTraits.java",
                    "ThresholdBasedMergeStrategyFactoryImpl.java", "CurationSidebarManagerPrefs.java",
                    "CurationSidebarBehavior.java", "ProjectPreferencesExporter.java"]
    sources = []
    with tarfile.open(LOCAL / "inception-38.0-source.tar.gz") as archive:
        for member in archive.getmembers():
            if member.isfile() and Path(member.name).name in source_names:
                raw = archive.extractfile(member).read()
                target = OUT / "sources" / Path(member.name).name
                if target.exists() and target.read_bytes() != raw:
                    raise ValueError("Retained source changed")
                target.write_bytes(raw)
                sources.append({"archive_path": member.name, "file": str(target.relative_to(ROOT)), "sha256": sha(raw)})
    version = subprocess.run([str(JAVA), "-version"], capture_output=True, text=True, check=True, timeout=15)
    if 'version "17.' not in version.stderr:
        raise ValueError("Reviewed Java 17 runtime required")
    receipt = {"release": "38.0", "jar": {"url": JAR_URL, "sha256": JAR_SHA, "bytes": (LOCAL/JAR_NAME).stat().st_size},
               "source_archive": {"url": SOURCE_URL, "sha256": file_sha(LOCAL/"inception-38.0-source.tar.gz")},
               "java": {"path": str(JAVA.resolve()), "sha256": file_sha(JAVA), "version": version.stderr.strip()},
               "sources": sources, "plan": PLAN, "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1"}
    path = OUT / "toolchain.json"
    if path.exists() and json.loads(path.read_text()) != receipt:
        raise ValueError("Toolchain receipt changed; preserve and review a new version")
    save(path, receipt)
    print(json.dumps({"status": "PREPARED", "receipt": str(path.relative_to(ROOT))}), flush=True)


class Client:
    """Fixed loopback transport; retain response bytes but never credentials."""

    def __init__(self, port, password, folder):
        self.base = f"http://127.0.0.1:{port}"
        self.auth = "Basic " + base64.b64encode(("trial-admin:" + password).encode()).decode()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), LocalRedirects())
        self.folder = folder
        self.records = []
        self.deadline = time.monotonic() + 300

    def request(self, method, path, *, fields=None, files=None, name=None, record=True):
        check_storage()
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Local relative API path required")
        headers = {"Authorization": self.auth}
        data = None
        if fields is not None or files:
            if files:
                boundary = "LegalMath" + secrets.token_hex(16)
                chunks = []
                for key, value in (fields or {}).items():
                    chunks.extend([f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n".encode(), str(value).encode(), b"\r\n"])
                for key, (filename, raw, content_type) in files.items():
                    chunks.extend([f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode(), raw, b"\r\n"])
                chunks.append(f"--{boundary}--\r\n".encode())
                data = b"".join(chunks)
                headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
            else:
                data = urllib.parse.urlencode(fields).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        started = time.monotonic()
        try:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Server request deadline exceeded")
            response = self.opener.open(request, timeout=min(90, remaining))
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read(100_000_001)
            if len(raw) > 100_000_000:
                raise ValueError("API response exceeds trial bound")
            status = response.status
            kind = response.headers.get("Content-Type", "")
        if record:
            filename = name or f"http-{len(self.records)+1:03d}.json"
            (self.folder / filename).write_bytes(raw)
            self.records.append({"method": method, "path": path, "status": status, "file": filename,
                                 "sha256": sha(raw), "seconds": time.monotonic()-started})
            save(self.folder / "http.json", self.records)
        if status >= 400:
            raise RuntimeError(f"HTTP {status} at {path}: " + raw[:2000].decode(errors="replace"))
        return json.loads(raw) if "json" in kind else raw


@contextmanager
def server(folder, *, guests=True):
    receipt = json.loads((OUT / "toolchain.json").read_text())
    if file_sha(LOCAL / JAR_NAME) != JAR_SHA or file_sha(JAVA) != receipt["java"]["sha256"]:
        raise ValueError("Runtime bytes changed")
    runtime = LOCAL / folder.name
    runtime.mkdir(exist_ok=False)
    password = secrets.token_urlsafe(20)
    encoded = subprocess.run(["/usr/bin/python3", "-c",
        "import crypt,sys; print(crypt.crypt(sys.stdin.read(), crypt.mksalt(crypt.METHOD_BLOWFISH)))"],
        input=password, capture_output=True, text=True, check=True, timeout=15).stdout.strip()
    if not encoded.startswith(("$2b$", "$2a$")):
        raise ValueError("BCrypt password generation failed")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    settings = {"server.address": "127.0.0.1", "server.port": str(port), "remote-api.enabled": "true",
                "security.default-admin-username": "trial-admin", "security.default-admin-remote-access": "true",
                "security.default-admin-password": "{bcrypt}" + encoded,
                "telemetry.enabled": "false", "matomo.enabled": "false",
                "sharing.invites.enabled": "true" if guests else "false", "sharing.invites.guests-enabled": "true" if guests else "false",
                "logging.level.root": "INFO", "debug": "false"}
    settings_path = runtime / "settings.properties"
    settings_path.write_text("\n".join(k+"="+v for k,v in settings.items()) + "\n")
    settings_path.chmod(0o600)
    save(folder / "server-settings.json", {k:v for k,v in settings.items() if "password" not in k})
    command = [str(JAVA), "-Xmx2g", "-XX:ActiveProcessorCount=2", "-Djava.awt.headless=true",
               "-Dinception.home=" + str(runtime), "-jar", str(LOCAL / JAR_NAME)]
    save(folder / "server-command.json", {"command": command, "runtime": str(runtime), "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1"})
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1"}
    client = Client(port, password, folder)
    with (folder / "server.log").open("w") as log:
        process = subprocess.Popen(command, cwd=runtime, env=env, stdout=log, stderr=subprocess.STDOUT)
        save(runtime / "connection.json", {"base": client.base, "user": "trial-admin", "password": password})
        (runtime / "connection.json").chmod(0o600)
        try:
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("INCEpTION exited during startup; see server.log")
                try:
                    ready = client.request("GET", API + "/projects", record=False)
                    if isinstance(ready, dict) and isinstance(ready.get("body"), list):
                        break
                except (OSError, RuntimeError):
                    pass
                startup_log = (folder / "server.log").read_text(errors="replace")
                if "Application run failed" in startup_log or "Hex-encoded string" in startup_log:
                    raise RuntimeError("INCEpTION application initialization failed; see server.log")
                time.sleep(1)
            else:
                raise TimeoutError("INCEpTION startup exceeded 300 seconds")
            print(json.dumps({"status": "SERVER_READY", "port": port}), flush=True)
            client.deadline = time.monotonic() + 900
            yield client, runtime
        finally:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            save(folder / "server-stop.json", {"pid": process.pid, "exit_code": process.returncode, "stopped": True})


def project_json(raw):
    archive = zipfile.ZipFile(io.BytesIO(raw))
    name = next(n for n in archive.namelist() if Path(n).name.startswith("exportedproject") and n.endswith(".json"))
    return archive, name, json.loads(archive.read(name))


def probe_workflow(client, folder, runtime):
    response = client.request("POST", API + "/projects", fields={"name": "legalmath-template", "title": "Synthetic tool integration template"})
    project = response["body"]["id"]
    raw = client.request("GET", f"{API}/projects/{project}/export.zip", name="template.zip")
    _, _, data = project_json(raw)
    save(folder / "template.json", data)
    return {"status": "FEASIBILITY_ONLY", "project": project, "independence": "NOT_ESTABLISHED"}


def packets(folder):
    from legalmath.prospectus.successor.annotation_bridge import export
    baseline = ROOT / "docs/implementation/prospectus-adoption/phases/A3/attempt-004/annotation-input.json"
    unicode_packet = json.loads(baseline.read_text())
    # Exact retained German line occurrences, with the join transformation recorded.
    lines_path = ROOT / "docs/implementation/prospectus-adoption/phases/A3/attempt-004/critical-spans-before-prediction.json"
    lines = [x for x in json.loads(lines_path.read_text()) if x["document"].startswith("basf")][:4]
    text = "\n".join(x["raw"] for x in lines)
    spans, offset = [], 0
    for line in lines:
        spans.append({"start": offset, "end": offset + len(line["raw"]), "quote": line["raw"]})
        offset += len(line["raw"]) + 1
    basf = export(text, {"document": lines[0]["document"], "source_sha256": lines[0]["source_sha256"],
                        "text_sha256": sha(text.encode())},
                  [{"id": "definition", "label": "provisional_definition", "spans": [spans[1]]},
                   {"id": "margin", "label": "provisional_margin", "spans": spans[2:]}],
                  [{"id": "attachment", "from": "margin", "to": "definition", "kind": "attachment_to_review"}])
    save(folder / "basf-source-map.json", {"input": str(lines_path.relative_to(ROOT)), "sha256": file_sha(lines_path),
         "transformation": "Join selected raw line occurrences with one LF; not continuous contract text",
         "lines": [{"id": line["id"], "page": line["page"], **span} for line,span in zip(lines,spans)],
         "cohort": "EXPOSED_DEVELOPMENT", "labels": "PROVISIONAL_IMPLEMENTER_TEST"})
    result = {"unicode": unicode_packet, "basf": basf}
    for name, packet in result.items():
        save(folder / (name+"-original.json"), packet)
        edited = deepcopy(packet)
        target = next(g for g in edited["groups"] if g["id"] == ("exception" if name == "unicode" else "definition"))
        target["label"] = "reviewed_for_exchange_only"
        save(folder / (name+"-expected-edit.json"), edited)
    return result


def codec(folder, operation, packet, xmi, types=None, output=None):
    command = ["/tmp/prospectus-adoption-tools/bin/python", "-m", "scripts.prospectus_inception_xmi", operation,
               "--packet", str(packet), "--xmi", str(xmi)]
    if types:
        command += ["--types", str(types)]
    if output:
        command += ["--output", str(output)]
    if operation == "decode":
        command += ["--expect-equal"]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30,
                         env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1"})
    log = folder / (Path(xmi).stem + "-" + operation + ".log")
    log.write_text(run.stdout + run.stderr)
    if run.returncode:
        raise RuntimeError("Annotation codec failed; inspect " + log.name)


def configured_project():
    from legalmath.prospectus.successor.annotation_xmi import project_layers
    provenance = json.loads((OUT / "template-provenance.json").read_text())
    if file_sha(OUT / "template.zip") != provenance["sha256"]:
        raise ValueError("Retained server template changed")
    archive, metadata_name, template = project_json((OUT / "template.zip").read_bytes())
    project = deepcopy(template)
    project.update(name="LegalMath annotation integration — synthetic trial", slug="legalmath-exchange",
                   description="Exposed development examples and synthetic accounts; no independent legal acceptance",
                   disableExport=False, anonymous_curation=True, project_permissions=[], project_users=[],
                   source_documents=[], annotation_documents=[], recommenders=[], learning_records=[])
    for layer in project["layers"]:
        layer["enabled"] = layer["name"].endswith((".Token", ".Sentence"))
    project["layers"] += project_layers()
    project["project_invites"] = [{"inviteId": "synthetic-local-session-test", "guestAccessible": True,
                                  "expirationDate": int((time.time() + 3600) * 1000),
                                  "invitationText": "Local synthetic account authorization test only",
                                  "askForEMail": "NOT_ALLOWED", "disableOnAnnotationComplete": False,
                                  "maxAnnotatorCount": 4, "userIdPlaceholder": "Synthetic reader name"}]
    project["default-preferences"] = [
        {"name": "annotation/editor/curation-sidebar/manager", "traits": json.dumps({"autoMergeCurationSidebar": False})},
        {"name": "curation/manager", "traits": json.dumps({"curationPageType": "integrated"})}]
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name in archive.namelist():
            target.writestr(name, json.dumps(project).encode() if name == metadata_name else archive.read(name))
    return raw.getvalue(), project


def check_configuration(project):
    from legalmath.prospectus.successor.annotation_xmi import SPAN, RELATION, IDENTITY
    if project.get("recommenders") != []:
        raise ValueError("Recommendations are configured")
    prefs = {p["name"]: json.loads(p["traits"]) for p in project["default-preferences"]}
    if prefs.get("annotation/editor/curation-sidebar/manager", {}).get("autoMergeCurationSidebar") is not False:
        raise ValueError("Automatic curation merge not disabled")
    if prefs.get("curation/manager", {}).get("curationPageType") != "integrated":
        raise ValueError("Legacy curation route would merge automatically")
    layers = {p["name"]: p for p in project["layers"]}
    for name in (SPAN, RELATION, IDENTITY):
        if name not in layers or layers[name]["anchoring_mode"] != "CHARACTERS" or not layers[name]["cross_sentence"]:
            raise ValueError("Required character-level layer missing")
    if layers[RELATION]["attach_type"]["name"] != SPAN:
        raise ValueError("Semantic relation layer detached")
    return {"recommendations": "NONE_CONFIGURED", "automatic_premerge": "DISABLED_IN_INTEGRATED_CURATION",
            "layer_schema": "CHARACTER_OFFSETS_AND_CROSS_SENTENCE_RELATIONS"}


def workflow(client, folder, runtime):
    packet_map = packets(folder)
    raw, config = configured_project()
    (folder / "project-import.zip").write_bytes(raw)
    save(folder / "project-intended.json", config)
    response = client.request("POST", API + "/projects/import", files={"file": ("project.zip", raw, "application/zip")})
    project = response["body"]["id"]
    exported = client.request("GET", f"{API}/projects/{project}/export.zip", name="project-before.zip")
    _, _, actual = project_json(exported)
    save(folder / "project-before.json", actual)
    configuration = check_configuration(actual)
    readers = []
    for label in ("Synthetic Reader A", "Synthetic Reader B"):
        created = client.request("POST", f"{API}/projects/{project}/users", fields={"name": label})
        readers.append(created["body"]["username"])
        client.request("POST", f"{API}/projects/{project}/permissions/{readers[-1]}", fields={"roles": "ANNOTATOR"})
    save(folder / "accounts.json", {"readers": readers, "authentic_independence": False})
    client.request("POST", f"{API}/projects/{project}/permissions/trial-admin", fields={"roles": "ANNOTATOR,CURATOR"})
    permissions = client.request("GET", f"{API}/projects/{project}/permissions", name="permissions.json")["body"]
    for user in readers:
        if {p["role"] for p in permissions if p["user"] == user} != {"ANNOTATOR"}:
            raise ValueError("Synthetic reader has unintended permissions")
    documents = {}
    for name, packet in packet_map.items():
        original = folder / (name+"-original.json")
        types = folder / (name+"-typesystem.xml")
        original_xmi = folder / (name+"-original.xmi")
        codec(folder, "encode", original, original_xmi, types=types)
        response = client.request("POST", f"{API}/projects/{project}/documents", fields={"name": name+".txt", "format": "text"},
                                  files={"content": (name+".txt", packet["text"].encode(), "text/plain; charset=utf-8")})
        document = response["body"]["id"]
        documents[name] = document
        for i, user in enumerate(["trial-admin", *readers]):
            client.request("POST", f"{API}/projects/{project}/documents/{document}/annotations/{user}", fields={"format": "xmi", "state": "IN-PROGRESS" if i == 0 else "COMPLETE"},
                           files={"content": (name+".xmi", original_xmi.read_bytes(), "application/xml")})
            filename = name+f"-original-reader-{i}.zip"
            client.request("GET", f"{API}/projects/{project}/documents/{document}/annotations/{user}?format=xmi", name=filename)
            codec(folder, "decode", original, folder / filename, output=folder/(filename+".json"))
    save(folder / "project-ids.json", {"project": project, "documents": documents, "readers": readers})
    ui = browser_edit(client, folder, runtime, project, documents, readers)
    for name, document in documents.items():
        for i, user in enumerate(["trial-admin", *readers]):
            filename = name+f"-after-reader-{i}.zip"
            client.request("GET", f"{API}/projects/{project}/documents/{document}/annotations/{user}?format=xmi", name=filename)
            expected = folder / (name + ("-expected-edit.json" if i == 0 else "-original.json"))
            codec(folder, "decode", expected, folder/filename, output=folder/(filename+".json"))
    exported = client.request("GET", f"{API}/projects/{project}/export.zip?format=xmi", name="project-final.zip")
    _, _, actual = project_json(exported)
    save(folder / "project-final.json", actual)
    check_configuration(actual)
    return {"status": "SERVER_EXCHANGE_PASS", "configuration": configuration,
            "rest_roundtrips": "TWO_PACKETS_THREE_ORIGINAL_AND_THREE_POST_EDIT_EXPORTS_EACH",
            "ui": ui, "project": project, "independence": "SYNTHETIC_TEST_ACCOUNTS_ONLY"}


def browser_edit(client, folder, runtime, project, documents, readers):
    from playwright.sync_api import sync_playwright
    browser_path = Path("/home/chakwong/python/legalmath/.localresources/browser/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell")
    connection = json.loads((runtime / "connection.json").read_text())
    with sync_playwright() as automation:
        browser = automation.chromium.launch(executable_path=str(browser_path), headless=True, args=["--disable-gpu"])
        browser_context = browser.new_context(viewport={"width": 1440, "height": 1000})
        browser_context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(client.base + "/") else route.abort())
        page = browser_context.new_page()
        page.goto(client.base + "/login.html")
        page.locator('input[name="username"]').fill(connection["user"])
        page.locator('input[name="password"]').fill(connection["password"])
        page.locator('button[type="submit"], input[type="submit"]').first.click()
        page.wait_for_load_state("networkidle")
        try:
            for name, document in documents.items():
                page.goto(client.base + f"/p/{project}/annotate/{document}")
                page.wait_for_load_state("networkidle")
                if page.get_by_text("Choose Document", exact=True).is_visible():
                    page.get_by_text(name+".txt", exact=True).click()
                page.locator("svg [data-span-id]").first.wait_for(state="visible", timeout=30000)
                label = "exception | exception |" if name == "unicode" else "definition | provisional_definition |"
                page.locator("div.sticky-top").filter(has_text=label).locator("..").get_by_title("Select", exact=True).click()
                field = page.locator(".fe-input").filter(has=page.locator("label span").filter(has_text=re.compile("^label$"))).locator("input")
                field.wait_for(state="visible")
                field.fill("reviewed_for_exchange_only")
                field.press("Tab")
                page.locator("svg g.span").filter(has_text="reviewed_for_exchange_only").first.wait_for(state="visible")
                page.screenshot(path=str(folder / (name+"-edited.png")), full_page=True)
                save_html(page, folder / (name+"-edited.html"))
                # A fresh page must load the persisted edit; DOM mutation alone cannot pass.
                page.reload()
                page.locator("svg g.span").filter(has_text="reviewed_for_exchange_only").first.wait_for(state="visible")
            for name, document in documents.items():
                page.goto(client.base + f"/p/{project}/curate/{document}")
                page.wait_for_load_state("networkidle")
                if page.get_by_text("Choose Document", exact=True).is_visible():
                    page.get_by_text(name+".txt", exact=True).click()
                page.locator("#annotationDetailEditorPanel").wait_for(state="visible", timeout=30000)
                page.screenshot(path=str(folder / (name+"-curation.png")), full_page=True)
                save_html(page, folder / (name+"-curation.html"))
                raw = client.request("GET", f"{API}/projects/{project}/documents/{document}/curation?format=xmi", name=name+"-curation.zip")
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    tree = ET.fromstring(archive.read(next(n for n in archive.namelist() if n.endswith(".xmi"))))
                if any(n.tag.endswith(("LegalEvidence", "LegalRelation")) for n in tree):
                    raise ValueError("Curation contains automatically merged annotations")
                original = json.loads((folder/(name+"-original.json")).read_text())
                if next(n for n in tree if n.tag.endswith("}Sofa")).get("sofaString") != original["text"]:
                    raise ValueError("Curation export text mismatch")
            access_checks = []
            for index, user in enumerate(readers):
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(client.base + "/") else route.abort())
                reader_page = context.new_page()
                try:
                    reader_page.goto(client.base + f"/p/{project}/join-project/synthetic-local-session-test")
                    reader_page.locator('input[name$="username"]').fill("Synthetic Reader " + ("A" if index == 0 else "B"))
                    with reader_page.expect_response(lambda r: r.request.method == "POST"):
                        reader_page.get_by_role("button", name="Join project").click()
                    reader_page.goto(client.base + f"/p/{project}/annotate/{documents['unicode']}")
                    reader_page.wait_for_load_state("networkidle")
                    if reader_page.get_by_text("Choose Document", exact=True).is_visible():
                        reader_page.get_by_text("unicode.txt", exact=True).click()
                    reader_page.locator("svg g.span").filter(has_text="exception | exception |").wait_for(state="visible")
                    if reader_page.locator("svg g.span").filter(has_text="reviewed_for_exchange_only").count():
                        raise ValueError("Reader sees the administrator's edited annotation")
                    save_html(reader_page, folder / f"reader-{index}-own.html")
                    for peer in ("trial-admin", readers[1-index]):
                        # AnnotationPageBase moves document/owner parameters into the
                        # Wicket URL fragment (`#!d=...&u=...`). Query parameters
                        # reopen the document chooser and never exercise access control.
                        reader_page.goto(client.base + f"/p/{project}/annotate#!d={documents['unicode']}&u={urllib.parse.quote(peer, safe='')}")
                        denial = reader_page.get_by_text("Requested document does not exist or you have no permissions to access it.", exact=True)
                        denial.wait_for(state="attached")
                        tag = "admin" if peer == "trial-admin" else "peer"
                        save_html(reader_page, folder / f"reader-{index}-{tag}-denied.html")
                        access_checks.append({"reader": user, "requested_owner": peer, "denial": denial.text_content(),
                                              "document": documents["unicode"], "page": reader_page.url})
                finally:
                    save_html(reader_page, folder / f"reader-{index}-last.html")
                    (folder / f"reader-{index}-last.txt").write_text(reader_page.locator("body").inner_text())
                    context.close()
            save(folder / "access-checks.json", {"checks": access_checks, "scope": "SESSION_AUTHORIZATION_ONLY_GUEST_IDENTITIES_NOT_AUTHENTICATED"})
        finally:
            page.screenshot(path=str(folder / "editor.png"), full_page=True)
            save_html(page, folder / "editor.html")
            (folder / "editor-text.txt").write_text(page.locator("body").inner_text())
            browser.close()
    return {"status": "TWO_BROWSER_EDITS_PERSISTED", "curation": "TWO_EMPTY_CURATION_EXPORTS_AFTER_OPENING",
            "access": "FOUR_CROSS_ACCOUNT_REQUESTS_DENIED"}


def save_html(page, path):
    # Session CSRF tokens have no evidentiary value in a saved editor snapshot.
    raw = re.sub(r'(<meta name="csrftoken" content=")[^"]*', r'\1REDACTED', page.content())
    path.write_text(raw)


def execute(kind):
    OUT.mkdir(parents=True, exist_ok=True)
    attempts = sorted(OUT.glob(kind + "-*"))
    next_index = max((int(p.name.split("-")[-1]) for p in attempts), default=0) + 1
    folder = OUT / f"{kind}-{next_index:03d}"
    started = time.monotonic()
    method_files = [Path(__file__), ROOT / "scripts/prospectus_inception_xmi.py",
                    ROOT / "src/legalmath/prospectus/successor/annotation_xmi.py",
                    ROOT / "src/legalmath/prospectus/successor/annotation_bridge.py", ROOT / PLAN,
                    ROOT / "src/legalmath/prospectus/successor/contracts.py",
                    ROOT / "scripts/prospectus_inception_verify.py",
                    ROOT / "docs/implementation/prospectus-adoption/phases/A3/attempt-004/annotation-input.json",
                    ROOT / "docs/implementation/prospectus-adoption/phases/A3/attempt-004/critical-spans-before-prediction.json",
                    OUT / "toolchain.json"]
    method_files += [OUT / "sources/supplementary-inventory.json"]
    if kind == "run":
        method_files += [OUT / "template.zip", OUT / "template-provenance.json"]
    method = {str(p.relative_to(ROOT)): file_sha(p) for p in method_files}
    fingerprint = sha(json.dumps(method, sort_keys=True).encode())
    if sum(json.loads(p.read_text()).get("method_fingerprint") == fingerprint
           for p in OUT.glob(kind + "-*/manifest.json")) >= 3:
        raise RuntimeError("Three attempts already used for unchanged method/input")
    check_storage()
    folder.mkdir()
    manifest = {"plan": PLAN, "command": [sys.executable, "-m", "scripts.prospectus_inception", kind],
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "driver_sha256": file_sha(__file__), "method": method, "method_fingerprint": fingerprint,
                "environment": sys.executable,
                "runtime_identity": runtime_identity(),
                "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1", "random_seeds": "N/A; deterministic exchange assertions",
                "result_file": str((folder / "result.json").relative_to(ROOT)), "status": "RUNNING"}
    save(folder / "manifest.json", manifest)
    try:
        with server(folder) as (client, runtime):
            def expired(signum, frame):
                raise TimeoutError("Workflow exceeded reviewed 900-second bound")
            previous_handler = signal.signal(signal.SIGALRM, expired)
            signal.alarm(900)
            try:
                result = probe_workflow(client, folder, runtime) if kind == "probe" else workflow(client, folder, runtime)
                if any(file_sha(ROOT / p) != expected for p, expected in method.items()):
                    raise RuntimeError("Method changed during trial")
                if runtime_identity() != manifest["runtime_identity"]:
                    raise RuntimeError("Runtime changed during trial")
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, previous_handler)
        manifest["status"] = result["status"]
        save(folder / "result.json", result)
        if kind == "probe" and not (OUT / "template.zip").exists():
            shutil.copyfile(folder / "template.zip", OUT / "template.zip")
            save(OUT / "template-provenance.json", {"source": str((folder / "template.zip").relative_to(ROOT)),
                 "sha256": file_sha(OUT / "template.zip"), "release": "38.0", "status": "ACTUAL_SERVER_EMPTY_PROJECT_EXPORT"})
    except Exception:
        manifest["status"] = "FAILED"
        (folder / "failure.txt").write_text(traceback.format_exc())
        raise
    finally:
        manifest["wall_seconds"] = time.monotonic()-started
        manifest["storage_bytes"] = storage_bytes()
        manifest["outputs"] = {p.name: file_sha(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name != "manifest.json"}
        save(folder / "manifest.json", manifest)
        print(json.dumps({"status": manifest["status"], "directory": str(folder.relative_to(ROOT))}), flush=True)


def main():
    application_python = ROOT / ".venv/bin/python"
    if Path(sys.executable).absolute() != application_python.absolute():
        os.execv(str(application_python), [str(application_python), "-m", "scripts.prospectus_inception", *sys.argv[1:]])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "probe", "run", "verify"])
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "verify":
        from scripts.prospectus_inception_verify import verify
        verify()
    else:
        execute(args.command)


if __name__ == "__main__":
    main()
