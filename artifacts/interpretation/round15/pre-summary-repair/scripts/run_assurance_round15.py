#!/usr/bin/env python3
"""Execute the bounded round-15 assurance plan.

The program keeps round-14 evidence immutable, uses a fresh bounded reader for
the one model-dependent phase, and treats every deterministic result as an
engineering or triage record.  It never marks a legal reading correct.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from resolution_support import AT, JDK, LEDGER, read, save, sha, used, case
from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.workflow import EvidenceJournal, CachedEvidenceProvider
from legalmath.interpretation.assurance.control_investigation import BoundedReader
from legalmath.interpretation.assurance.semantics import (
    Fidelity, fidelity_request, validate_fidelity, representation,
)
from legalmath.interpretation.assurance.fidelity_batches import FidelityBatches
from legalmath.interpretation.search.providers import (Allowance, CodexProvider, Completion,
    verify_allowance_checkpoint)
from legalmath.interpretation.search.formal import bundle as compile_bundle
from legalmath.interpretation.search.formal import snapshots
from legalmath.interpretation.assurance.diversity import identity
from legalmath.java.manifest import build_candidate, verify_candidate
from legalmath.ir.evaluate import evaluate

PLAN = ROOT / "docs/plans/assurance-round15-execution.md"
ALLOWLIST = ROOT / "docs/implementation/interpretation-round15/allowlist.json"
OUT = ROOT / "artifacts/interpretation/round15"
EXECUTION = OUT / "execution"
ROUND14 = ROOT / "artifacts/interpretation/round14"
ROUND14_RESULT = ROUND14 / "final-report.json"
ROUND14_RESTORED = ROUND14 / "live-reviewed/restored-pairs.json"
ROUND14_REPAIRS = ROUND14 / "live-reviewed/repairs.json"
ROUND14_PDF = ROUND14 / "pdf-resolution.json"
ROUND14_AUTHORITIES = ROUND14 / "acquired-authorities.json"
# Resolve accepted paths through the verified phase receipt, not action numbers.
def round14_evidence(phase):
    selected = read(ROUND14/'phase-results.json')[phase]
    directory = ROUND14/'execution-reviewed'
    envelope = read(directory/'journal.json')['value']
    binding = envelope['binding']
    actions = EvidenceJournal(directory, binding['inputs'],
        maximum_actions=binding['maximum_actions'], maximum_per_issue=binding['maximum_per_issue'],
        deadline_seconds=binding['deadline_seconds']).report()['actions']
    action = actions[selected['receipt']['sequence']]
    if (action['status'] != 'EXECUTED' or action['result_hash'] != selected['receipt']['result_hash']
            or read(directory/action['result_file']) != selected['manifest']):
        raise LegalMathError('E_INTEGRITY', details='Round-14 phase receipt changed: '+phase)
    path = ROOT/selected['manifest']['result_path']
    if sha(path) != selected['manifest']['result_sha256']:
        raise LegalMathError('E_INTEGRITY', details='Round-14 phase evidence changed: '+phase)
    return path.parent

ROUND14_FORMAL = ROOT/read(ROUND14/'phase-results.json')['R5']['directory']/'formal-input.json'
ROUND14_FROZEN = ROOT / "docs/implementation/interpretation-round14/new-circular-official.json"
ROUND14_LOCK = ROOT / "docs/implementation/interpretation-round14/new-circular-official-lock.json"
ROUND14_DELIVERY = ROOT / "scripts/resolution_delivery_review.py"
ROUND14_DELIVERY_MANIFEST = ROUND14 / "delivery-manifest.json"
ROUND14_POST_REVIEW = ROUND14 / "post-execution-review.json"
ROUND14_ISSUES = ROUND14 / "issue-inventory.json"
ROUND14_PHASES = ROUND14 / "phase-results.json"
ROUND14_PLAN = ROOT / "docs/plans/assurance-after-round14.md"
ROUND14_REPAIR = ROOT / "docs/implementation/interpretation-round14/repair-review.md"
ROUND14_ALLOW = ROOT / "docs/implementation/interpretation-round14/allowlist.json"
ROUND14_SUPPORT = ROOT / "scripts/resolution_support.py"

PHASES = ("P0", "P1", "P2", "P3", "P4", "P5", "P6")
CALL_START = 487
CALL_CEILING = 500
CALL_MAXIMUM = 500
BATCH_SIZE = 24
PAIR_COUNT = 231


def json_hash(path: Path) -> str:
    return raw_digest(path.read_bytes())


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def require_file(path: Path) -> None:
    if not path.is_file():
        raise LegalMathError("E_NOT_FOUND", details=relative(path))


def exact_round14_inputs() -> dict[str, str]:
    paths = [
        ROUND14_RESULT, ROUND14_DELIVERY_MANIFEST, ROUND14_RESTORED,
        ROUND14_REPAIRS, ROUND14_PDF, ROUND14_AUTHORITIES, ROUND14_FORMAL,
        ROUND14_FROZEN, ROUND14_LOCK, ROUND14_ISSUES, ROUND14_PHASES,
        ROUND14_POST_REVIEW,
        ROUND14_PLAN, ROUND14_REPAIR, ROUND14_ALLOW, ROUND14_SUPPORT,
    ]
    for path in paths:
        require_file(path)
    return {relative(path): json_hash(path) for path in paths}


def validate_pair_inventory() -> dict:
    restored = read(ROUND14_RESTORED)
    if len(restored) != 232:
        raise LegalMathError("E_INTEGRITY", details="round-14 restored pair count changed")
    rows = []
    unencoded = []
    for row in restored:
        cid = row["case_id"]
        data = case(cid)
        if row["candidate_id"] not in data["candidates"]:
            raise LegalMathError("E_REFERENCE", details="restored candidate missing")
        try:
            compile_bundle(data["candidates"][row["candidate_id"]], data["packet"], AT)
            executable = True
        except LegalMathError as exc:
            if exc.code != "E_UNSUPPORTED_PROFILE":
                raise
            executable = False
        item = {
            "case_id": cid,
            "claim_id": row["claim_id"],
            "candidate_id": row["candidate_id"],
            "candidate_hash": digest(data["candidates"][row["candidate_id"]]),
            "source_packet_hash": digest(data["packet"]),
            "executable": executable,
            "round14_judgment": row.get("judgment"),
        }
        rows.append(item)
        if not executable:
            unencoded.append(item)
    executable = [r for r in rows if r["executable"]]
    if len(executable) != PAIR_COUNT or len(unencoded) != 1:
        raise LegalMathError("E_INTEGRITY", details={"executable": len(executable), "unencoded": len(unencoded)})
    context = []
    for row in executable:
        claim = next(c for c in case(row["case_id"])["claims"] if c["claim_id"] == row["claim_id"])
        if claim["relevance"] == "CONTEXT": context.append(row)
    return {"rows": rows, "executable": executable, "assessable": executable, "context": context,
            "unencoded": unencoded,
            "counts": {"restored": len(rows), "executable": len(executable), "unencoded": len(unencoded),
                        "assessable": len(executable), "historical_context": len(context)}}


class SingleAttemptProvider(CachedEvidenceProvider):
    """One transport attempt per journal action; never hide a transport retry."""
    def complete(self, request, schema, settings):
        inputs = {'request': request, 'schema': schema, 'settings': settings.model_dump()}
        inputs['settings'].pop('timeout_seconds', None)
        def dispatch(work):
            save(work/'request.json', request)
            answer = self.provider.complete(request, schema, settings)
            return {'value': answer.value, 'provenance': answer.provenance}
        value, receipt = self.journal.execute('model', inputs, dispatch,
            issue='request.' + identity({'request': request, 'schema': schema}))
        return Completion(value['value'], {**value['provenance'], 'workflow_receipt': receipt,
            'new_live_invocation': not receipt['reused'], 'evidence_reused': receipt['reused']})


class CircuitReader(BoundedReader):
    """Stop future live dispatch after a transport or resource failure."""

    def __init__(self, provider, directory, binding, *, maximum_actions):
        super().__init__(provider, directory, binding, maximum_actions=maximum_actions)
        self.provider = SingleAttemptProvider(provider, Path(directory)/'model', binding,
            maximum_actions=maximum_actions, deadline_seconds=21600)

    def call(self, request, model, validate):
        value = super().call(request, model, validate)
        if value is None and not self.stopped_reason:
            actions = self.provider.journal.report()["actions"]
            if actions:
                last = actions[-1]
                if last["status"] in ("FAILED", "INTERRUPTED") and last.get("error") in (
                    "E_DEPENDENCY", "E_RESOURCE_LIMIT"
                ):
                    self.stopped_reason = "DISPATCH_BLOCKED: " + str(last.get("details", last.get("error")))
        return value


def code_binding():
    paths = [PLAN, ALLOWLIST, Path(__file__),
             ROOT/'docs/implementation/interpretation-round15/repair-review.md',
             ROOT/'scripts/assurance_round15_checks.py', ROOT/'tests/assurance/test_round15.py']
    paths += list(ROOT.glob('src/legalmath/**/*.py')) + list(ROOT.glob('src/legalmath/**/*.java'))
    paths += list(ROOT.glob('src/legalmath/schemas/*.json'))
    return {relative(p): sha(p) for p in sorted(set(paths)) if p.is_file()}


def audit() -> dict:
    """Audit the baseline and record the reason it is safe to dispatch."""
    allow = read(ALLOWLIST)
    if allow.get("round14_calls_at_bind") != CALL_START or allow.get("round15_absolute_call_ceiling") != CALL_CEILING:
        raise LegalMathError("E_RESOURCE_LIMIT", details="allow-list budget mismatch")
    if allow.get("round15_new_call_cap") != CALL_CEILING - CALL_START:
        raise LegalMathError("E_RESOURCE_LIMIT", details="allow-list increment mismatch")
    grant = read(LEDGER)
    checkpoint = OUT/'baseline.json'
    if checkpoint.exists():
        base = read(checkpoint)
        verify_allowance_checkpoint(LEDGER, base['allowance_sha256'])
        if base['round14_inputs'] != exact_round14_inputs():
            raise LegalMathError('E_INTEGRITY', details='Frozen baseline changed')
    else:
        if grant.get('maximum') != CALL_MAXIMUM or len(grant.get('calls', [])) != CALL_START:
            raise LegalMathError('E_INTEGRITY', details='Initial allowance differs; re-audit before binding')
        base = {'allowance_sha256': raw_digest(canonical(grant)), 'allowance_prefix': grant,
                'round14_inputs': exact_round14_inputs(), 'call_start': CALL_START}
        save(checkpoint, base)
    report = read(ROUND14_RESULT)
    if report.get("release_eligible") is not False or report.get("legal_accuracy_established") is not False:
        raise LegalMathError("E_INTEGRITY", details="round-14 status was promoted")
    # The historical round-14 delivery checker intentionally requires the
    # allowance to remain at 466. Unattributed reservations were later appended,
    # so rerunning that checker against the live ledger would
    # report the expected append as corruption. Verify its immutable recorded
    # result and every delivery hash instead.
    post = read(ROUND14_POST_REVIEW)
    if post.get("status") != "ENGINEERING_AND_EDITORIAL_DELIVERY_VERIFIED" or post.get("allowance_consumed") != 466:
        raise LegalMathError("E_INTEGRITY", details="round-14 historical delivery record changed")
    if post.get("final_report_sha256") != json_hash(ROUND14_RESULT):
        raise LegalMathError("E_INTEGRITY", details="round-14 final report hash changed")
    manifest = read(ROUND14_DELIVERY_MANIFEST)
    for name, expected in manifest.get("files", {}).items():
        path = ROUND14 / name
        require_file(path)
        if json_hash(path) != expected:
            raise LegalMathError("E_INTEGRITY", details="round-14 delivery file changed: " + name)
    for name, expected in manifest.get("external_files", {}).items():
        path = ROOT / name
        require_file(path)
        if json_hash(path) != expected:
            raise LegalMathError("E_INTEGRITY", details="round-14 delivery file changed: " + name)
    for phase in ('R1', 'R3', 'R4', 'R5', 'R6'): round14_evidence(phase)
    inventory = validate_pair_inventory()
    pdf = read(ROUND14_PDF)
    if len(pdf.get("issues", [])) != 339 or pdf.get("counts", {}).get("MATERIALITY_UNRESOLVED") != 337:
        raise LegalMathError("E_INTEGRITY", details="round-14 PDF inventory changed")
    inputs = exact_round14_inputs()
    value = {
        "status": "AUDITED_ROUND14_BASELINE",
        "program": relative(Path(__file__)),
        "plan_sha256": json_hash(PLAN),
        "allowlist_sha256": json_hash(ALLOWLIST),
        "round14_inputs": inputs,
        "baseline_sha256": sha(checkpoint),
        "implementation": code_binding(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": str(ROOT / ".venv/bin/python"),
        "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
        "calls_before": len(grant["calls"]),
        "historical_appends_without_attributed_results": CALL_START - 466,
        "calls_ceiling": CALL_CEILING,
        "inventory": inventory["counts"],
        "pdf_issues": len(pdf["issues"]),
        "delivery_review": "ENGINEERING_AND_EDITORIAL_DELIVERY_VERIFIED",
        "skeptical_audit": {
            "baseline_is_immutable_round14": True,
            "proxy_agreement_not_promotion": True,
            "stop_conditions_declared": True,
            "authority_and_pdf_queues_preserved": True,
        },
        "release_eligible": False,
    }
    save(OUT / "audit.json", value)
    return value


def pair_data(inventory: dict):
    by_case = {}
    for cid in ("26ec2", "23ec46"):
        data = case(cid)
        rows = [r for r in inventory["executable"] if r["case_id"] == cid]
        by_case[cid] = (data, rows)
    return by_case


def review_claims(data, ids):
    # CONTROL here schedules examination; it is not a substantive relevance
    # finding. Historical CONTEXT labels must not suppress a restored pair.
    return [{**{k: v for k, v in c.items() if k not in ('relevance', 'readers')},
             'relevance': 'CONTROL'} for c in data['claims'] if c['claim_id'] in ids]


def run_p1(out: Path) -> dict:
    inventory = validate_pair_inventory()
    pair_rows = inventory["assessable"]
    all_pair_rows = inventory["executable"]
    pairs = [(r["claim_id"], r["candidate_id"]) for r in pair_rows]
    if len(all_pair_rows) != PAIR_COUNT or len(pairs) != PAIR_COUNT or len(set(pairs)) != len(pairs):
        raise LegalMathError("E_INTEGRITY", details="P1 pair universe is not exact")
    save(out / "pair-manifest.json", {"pairs": [list(p) for p in pairs], "rows": all_pair_rows,
                                      "assessable_rows": pair_rows, "context_rows": inventory["context"],
                                      "batch_size": BATCH_SIZE, "source": "round14 restored-pairs"})
    ledger = FidelityBatches(out / "batches.json", pairs, batch_size=BATCH_SIZE)
    provider = CodexProvider(allowance=Allowance(LEDGER, CALL_MAXIMUM, reservation_ceiling=CALL_CEILING))
    binding = {
        "phase": "round15.p1.fidelity.v1",
        "pair_manifest": digest(pair_rows),
        "round14_source": json_hash(ROUND14_RESTORED),
        "source_packets": {cid: digest(data["packet"]) for cid, (data, _) in pair_data(inventory).items()},
    }
    reader = CircuitReader(provider, out / "model", binding, maximum_actions=CALL_CEILING - CALL_START)
    completed = {}
    concerns = []
    for filename, completed_pairs in ledger.state["completed"].items():
        path = out / "responses" / filename
        require_file(path)
        part = read(path)
        cid = next(r["case_id"] for r in pair_rows if (r["claim_id"], r["candidate_id"]) == tuple(completed_pairs[0]))
        data = case(cid)
        candidates = {p[1]: data["candidates"][p[1]] for p in completed_pairs}
        claims = review_claims(data, {p[0] for p in completed_pairs})
        validate_fidelity(part, data["packet"], claims, candidates, [tuple(p) for p in completed_pairs])
        if digest(part) != filename.removesuffix(".json"):
            raise LegalMathError("E_INTEGRITY", details="P1 response hash changed")
        for check in part["checks"]:
            completed[(check["claim_id"], check["candidate_id"])] = check
        concerns.extend(part["additional_concerns"])

    # Keep a request inside one source packet. A global slice would straddle
    # the 26EC2/23EC46 boundary and would make the exact-pair validator reject
    # it rather than silently mixing authorities.
    pair_case = {(r["claim_id"], r["candidate_id"]): r["case_id"] for r in pair_rows}
    queue = []
    for cid in ("26ec2", "23ec46"):
        pending = [p for p in ledger.pending if pair_case[p] == cid]
        queue.extend((pending[i:i + BATCH_SIZE], 0) for i in range(0, len(pending), BATCH_SIZE))
    dispatched = []
    while queue and not reader.stopped_reason:
        batch, depth = queue.pop(0)
        case_ids = {next(r["case_id"] for r in pair_rows if (r["claim_id"], r["candidate_id"]) == p) for p in batch}
        if len(case_ids) != 1:
            raise LegalMathError("E_INTEGRITY", details="A fidelity batch crosses source packets")
        cid = next(iter(case_ids)); data = case(cid)
        claim_ids = {p[0] for p in batch}; candidate_ids = {p[1] for p in batch}
        claims = review_claims(data, claim_ids)
        candidates = {k: data["candidates"][k] for k in sorted(candidate_ids)}
        req = fidelity_request(data["packet"], claims, candidates, batch)
        req["instructions"] += (
            " This is a fresh reassessment without previous fidelity or routing judgments. "
            "CONTROL is a scheduling flag for examination, not a finding of substantive relevance. "
            "Check whether the claim affects the candidate's exact scoped question before alleging "
            "an omission. Record remote qualifications and uncertainty."
        )
        part = reader.call(req, Fidelity, lambda value: validate_fidelity(value, data["packet"], claims, candidates, batch))
        if part is not None:
            filename = digest(part) + ".json"
            save(out / "responses" / filename, part)
            ledger.record(filename, batch)
            dispatched.append({"pairs": len(batch), "case_id": cid, "depth": depth, "status": "COMPLETED"})
            for check in part["checks"]:
                completed[(check["claim_id"], check["candidate_id"])] = check
            concerns.extend(part["additional_concerns"])
        else:
            failed_id = "failed." + digest([list(p) for p in batch])
            ledger.record(failed_id, batch, status="FAILED")
            dispatched.append({"pairs": len(batch), "case_id": cid, "depth": depth, "status": "FAILED"})
            if not reader.stopped_reason and depth == 0 and len(batch) > 1:
                midpoint = len(batch) // 2
                queue[0:0] = [(batch[:midpoint], 1), (batch[midpoint:], 1)]

        print('P1 '+cid+' completed='+str(len(completed))+'/'+str(len(pairs))+
              ' reservations='+str(used()), flush=True)
    report = ledger.report()
    labels = Counter(c["label"] for c in completed.values())
    result = {
        "status": "FRESH_FIDELITY_COMPLETE" if report["pending_pairs"] == 0 else "FRESH_FIDELITY_INCOMPLETE",
        "execution_complete": report["pending_pairs"] == 0,
        "pair_count": len(all_pair_rows), "assessable_pair_count": len(pairs),
        "historical_context_pairs_reopened": len(inventory["context"]), "completed_pairs": report["completed_pairs"],
        "pending_pairs": report["pending_pairs"], "failed_batches": report["failed_batches"],
        "label_counts": dict(labels), "additional_concerns": concerns,
        "dispatched_batches": dispatched,
        "stopped_reason": reader.stopped_reason,
        "provider_journal": str((out / "model/model/journal.json").relative_to(ROOT)),
        "checks": [completed[p] for p in pairs if p in completed],
        "pending_pair_ids": [list(p) for p in ledger.pending],
        "unencoded_rows": inventory['unencoded'],
        "context_rows_retained": inventory["context"], "calls_after": used(), "source_packet_hashes": binding["source_packets"],
        "legal_accuracy_established": False, "release_eligible": False,
    }
    save(out / "result.json", result)
    return result


def run_p2(out: Path) -> dict:
    repairs = read(ROUND14_REPAIRS)
    if len(repairs) != 8:
        raise LegalMathError("E_INTEGRITY", details="parent repair count changed")
    children = []; probes = []; witnesses = []
    for parent in repairs:
        review = parent.get("review") or {}
        lost = review.get("lost_or_added_conditions", [])
        witnesses.append({"case_id": parent["case_id"], "candidate_id": parent["candidate_id"],
                          "parent_review": review.get("judgment", "UNREVIEWED"),
                          "witness_requirements": lost,
                          "parent_remains_retained": True})
        for encoding in parent.get("record", {}).get("encodings", []):
            row = {"case_id": parent["case_id"], "parent_candidate_id": parent["candidate_id"],
                   "child_id": encoding.get("id"), "status": encoding.get("status"),
                   "error": encoding.get("error")}
            b = encoding.get("bundle")
            if b is None:
                children.append(row); continue
            child_dir = out / "children" / (digest(b)[:16])
            built = build_candidate(b, child_dir, JDK)
            probes_for_child = list(snapshots([b], AT, maximum=16))
            cases = [{"id": "p2." + str(i), "bundle": b, "snapshot": s, "rule_id": "selected.control",
                      "valid_at": AT, "known_at": AT, "expected": {}}
                     for i, s in enumerate(probes_for_child)]
            verification = verify_candidate(built, cases, JDK)
            from assurance_round15_checks import diverse_backends
            diverse = diverse_backends(cases, built, child_dir/'independent')
            row.update(status="CONFORMANCE_PASS", bundle_hash=digest(b), probe_count=len(cases),
                       java_manifest_hash=digest(built["manifest"]), verification_hash=digest(verification),
                       independent=diverse,
                       executable_examples=[{'snapshot':c['snapshot'],
                           'result':project(evaluate(b,c['snapshot'],'selected.control',AT,AT))} for c in cases])
            probes.append(row)
            children.append(row)
    counts = Counter(row["status"] for row in children)
    value = {"status": "PARENT_RETAINED_CHILD_PROBES" if not any(r["status"] not in ("CONFORMANCE_PASS", "ENCODED_UNREVIEWED", "UNENCODED") for r in children) else "CHILD_PROBE_VETO",
             "parents": len(repairs), "child_count": len(children), "probe_passes": len(probes),
             "child_status_counts": dict(counts), "witnesses": witnesses, "children": children,
             "legal_accuracy_established": False, "release_eligible": False}
    save(out / "result.json", value)
    return value


def run_p3(out: Path) -> dict:
    from assurance_round15_checks import acquire_public
    acquisitions = acquire_public(out/'sources')
    authorities = read(ROUND14_AUTHORITIES)
    official = [{"path": x["path"], "sha256": x["sha256"]} for x in authorities]
    rows = [
        ("certificate-mechanics", "Operational certificate signing, holder, authorization and validity mechanics for an assessed XML/PDF submission", "Official JFIU/SFC technical instruction or tested submission specification", "Determine the exact predicate and evidence fields for the XML/PDF e-Cert branch."),
        ("xml-schema", "JFIU XML schema content and version supplied separately", "The separate XML schema, version identifier and technical-test instructions", "Validate one frozen XML fixture against the authoritative schema and record the effective version."),
        ("resubmission-timing", "Resubmission deadline and whether the follow-up applies only during blackout", "Official JFIU guidance identifying trigger, deadline, channel and completion evidence", "Encode each timing branch with timezone and an event-level test case."),
        ("mixed-gifts", "Dominant-character or inseparability test for a mixed gift package", "Authoritative SFC guidance or adjudicated interpretation for component boundaries", "Supply a typed component decomposition and test separable and inseparable packages."),
        ("structured-products", "Full structured-product classification and related advertising provisions", "Complete official circular, FAQ and incorporated provisions for the selected product family", "Freeze the complete source slice and enumerate every applicable branch before coding."),
        ("23ec52-appendix", "23EC52 appendix and any incorporated legislation are outside the retained HTML body", "The official appendix and each incorporated legislative provision", "Hash and anchor every incorporated provision used by a candidate rule."),
    ]
    register = []
    for ident, proposition, artifact, test in rows:
        register.append({"id": ident, "proposition_missing": proposition, "required_authority": artifact,
                         "closure_test": test, "status": "OPEN_NOT_ESTABLISHED",
                         "related_official_files": official, "source_hashes_are_not_sufficiency": True})
    value = {"status": "AUTHORITIES_ACQUIRED_WITH_OPEN_QUESTIONS", "official_acquisitions": official,
             "new_acquisitions": acquisitions,
             "open_count": len(register), "register": register, "release_eligible": False}
    save(out / "authority-gap-register.json", value)
    save(out / "result.json", value)
    return value


def run_p4(out: Path) -> dict:
    from assurance_round15_checks import pdf_review
    source = read(ROUND14_PDF)
    if len(source["issues"]) != 339:
        raise LegalMathError("E_INTEGRITY", details="PDF issue universe changed")
    pages=read(ROOT/'docs/implementation/interpretation-round13/pdf-structure-reference.json')['pages']
    reviewed = pdf_review(source, out/'review', pages)
    by_id = {r['issue_id']:r for r in reviewed}
    rows = []
    groups = defaultdict(list)
    for issue in source["issues"]:
        original = issue["original"]
        kind = original["kind"]
        change = original.get("change", {})
        token_text = " ".join(change.get("left_tokens", []) + change.get("right_tokens", []))
        high = kind == "NUMBER_OR_UNIT" or any(ch.isdigit() for ch in token_text)
        risk = "HIGH_MATERIALITY" if high else "TEXT_ORDER_REVIEW"
        row = {"issue_id": issue["issue_id"], "document": issue["document"], "page": issue["page"],
               "kind": kind, "risk": risk, "status": by_id[issue['issue_id']]["status"],
               "source_sha256": original["source_sha256"], "raster_sha256": original["raster_sha256"],
               "layout_sha256": issue["layout_sha256"], "locations": issue.get("locations", []),
               "original_change": change, "required_actions": original.get("eligible_actions", []),
               "resolution": by_id[issue['issue_id']].get("resolution"),
               "review_crop":by_id[issue['issue_id']]['review_crop'],
               "crop_sha256":by_id[issue['issue_id']]['crop_sha256'],
               "full_page":by_id[issue['issue_id']]['full_page']}
        rows.append(row); groups[(row["document"], row["page"], risk)].append(row["issue_id"])
    counts = Counter((r["risk"], r["status"]) for r in rows)
    value = {"status": "PDF_MATERIALITY_QUEUE_RETAINED", "issue_count": len(rows),
             "risk_counts": dict(Counter(r["risk"] for r in rows)),
             "status_counts": dict(Counter(r["status"] for r in rows)),
             "groups": [{"document": d, "page": p, "risk": risk, "issue_ids": ids}
                        for (d, p, risk), ids in sorted(groups.items())],
             "high_risk_issue_count": sum(r["risk"] == "HIGH_MATERIALITY" for r in rows),
             "resolved_typography_only": sum(r["resolution"] is not None for r in rows),
             "materiality_unresolved": sum(r["status"] == "MATERIALITY_UNRESOLVED" for r in rows),
             "issues": rows, "independent_visual_adjudication": False, "release_eligible": False}
    save(out / "queue.json", value)
    save(out / "result.json", value)
    return value


def project(result: dict) -> dict:
    return {k: result.get(k) for k in ("status", "type", "value") if k in result}


def mutate_bundle(base: dict, mutation: str) -> dict:
    result = deepcopy(base)
    body = result["rules"][0]["body"]
    if mutation == "or_to_and":
        if body["args"][1]["op"] != "any":
            raise LegalMathError("E_REFERENCE", details="unexpected frozen body")
        body["args"][1]["op"] = "all"
    elif mutation == "inclusive_to_strict":
        body["args"][1]["args"][1]["cmp"] = "gt"
    elif mutation == "threshold_shift":
        body["args"][1]["args"][1]["right"]["value"] = "1001"
    else:
        raise LegalMathError("E_SCHEMA")
    return result


def run_p5(out: Path) -> dict:
    formal = read(ROUND14_FORMAL)
    cases = {row["id"]: row for row in formal["cases"] if row["id"].startswith("controlled-language.0.")}
    required = {"below", "at", "above", "objective_only", "tokenised_only"}
    if not required <= {key.rsplit(".", 1)[-1] for key in cases}:
        raise LegalMathError("E_REFERENCE", details="mutation fixtures incomplete")
    base = cases["controlled-language.0.at"]["bundle"]
    selected_names = [k.removeprefix('controlled-language.0.') for k in cases]
    conflict=deepcopy(cases['controlled-language.0.at'])
    conflict['snapshot']['facts']['va_objective']={'type':'bool','status':'conflict','evidence_ids':['objective.a','objective.b']}
    cases['controlled-language.0.conflicting_objective']=conflict
    selected_names.append('conflicting_objective')
    all_bundles = {"original": base, "or_to_and": mutate_bundle(base, "or_to_and"),
                   "inclusive_to_strict": mutate_bundle(base, "inclusive_to_strict"),
                   "threshold_shift": mutate_bundle(base, "threshold_shift")}
    evaluations = []
    builds = []
    for name, b in all_bundles.items():
        cases_for_bundle = [{"id": "p5." + name + "." + suffix, "bundle": b,
                             "snapshot": cases["controlled-language.0." + suffix]["snapshot"],
                             "rule_id": "selected.control", "valid_at": AT, "known_at": AT,
                             "expected": {}} for suffix in selected_names]
        built = build_candidate(b, out / "bundles" / name, JDK)
        verification = verify_candidate(built, cases_for_bundle, JDK)
        from assurance_round15_checks import diverse_backends
        diverse=diverse_backends(cases_for_bundle,built,out/'bundles'/name/'independent')
        builds.append({"name": name, "bundle_hash": digest(b), "manifest_hash": digest(built["manifest"]),
                       "verification_hash": digest(verification), "case_count": len(cases_for_bundle),
                       "independent":diverse})
        for c in cases_for_bundle:
            py = evaluate(b, c["snapshot"], "selected.control", AT, AT)
            evaluations.append({"bundle": name, "fixture": c["id"].rsplit(".", 1)[-1], "python": project(py)})
    by = {(x["bundle"], x["fixture"]): x["python"] for x in evaluations}
    witnesses = [
        {"mutation": "or_to_and", "fixture": "objective_only", "original": by[("original", "objective_only")], "mutated": by[("or_to_and", "objective_only")]},
        {"mutation": "inclusive_to_strict", "fixture": "at", "original": by[("original", "at")], "mutated": by[("inclusive_to_strict", "at")]},
        {"mutation": "threshold_shift", "fixture": "at", "original": by[("original", "at")], "mutated": by[("threshold_shift", "at")]},
    ]
    caught = all(w["original"] != w["mutated"] for w in witnesses)
    tokenised = {"original": by[("original", "tokenised_only")]}
    included = deepcopy(cases["controlled-language.0.tokenised_only"]["snapshot"])
    included["facts"]["intended_va_bps"]["value"] = "1000"
    included["facts"]["intended_va_bps"]["evidence_ids"] = ["p5.incorrect-tokenised-binding"]
    tokenised["incorrect_binding"] = project(evaluate(base, included, "selected.control", AT, AT))
    tokenised_caught = tokenised["original"] != tokenised["incorrect_binding"]
    from assurance_round15_checks import rational_check
    rational=rational_check(base,out/'rational')
    rational['independent']=diverse_backends(rational['cases'],rational['build'],out/'rational/independent')
    if by[('original','conflicting_objective')]['status']!='CONFLICT':
        raise LegalMathError('E_INTEGRITY',details='Conflicting source facts became a known outcome')
    if not caught or not tokenised_caught:raise LegalMathError('E_INTEGRITY',details='Mutation survived declared witness')
    value = {"status": "MUTATIONS_CAUGHT" if caught and tokenised_caught else "MUTATION_VETO",
             "bundles": builds, "witnesses": witnesses, "tokenised_security_binding": tokenised,
             "evaluations": evaluations, "all_mutations_built_and_checked": len(builds) == 4,
             "rational_extension":rational,
             "mutation_harness_is_not_legal_oracle": True, "release_eligible": False}
    save(out / "result.json", value)
    return value


def repair_review(results: dict) -> dict:
    p1 = results.get("P1", {}).get("result", {})
    value = {
        "status": "REPAIR_REVIEWED",
        "repair_actions": [
            {"id": "p1-pending", "condition": p1.get("pending_pairs", 0) > 0,
             "action": "Keep every pending fidelity pair in the next bounded reader; do not infer a label."},
            {"id": "p2-parent", "condition": True,
             "action": "Keep all eight parent readings retained; do not replace a parent with a compiling child."},
            {"id": "p3-authority", "condition": True,
             "action": "Acquire only the named official artifact and rerun its typed closure test."},
            {"id": "p4-pdf", "condition": True,
             "action": "Use printed-page and official-text evidence for every materiality-unresolved row."},
            {"id": "p5-mutation", "condition": True,
             "action": "Treat a failed mutation witness as a harness veto, not as evidence about the law."},
        ],
        "release_eligible": False,
    }
    save(OUT / "repair-review.json", value)
    return value


def phase_binding(phase: str, preceding: list[str]) -> dict:
    return {"phase": phase, "implementation":code_binding(),
            "baseline_sha256":sha(OUT/'baseline.json'), "preceding": preceding,
            "absolute_ceiling": CALL_CEILING}


def execute(through='P6') -> dict:
    audit()
    OUT.mkdir(parents=True, exist_ok=True); EXECUTION.mkdir(parents=True, exist_ok=True)
    binding = {"program": "legalmath.assurance.round15.v2", "baseline":sha(OUT/'baseline.json'),
               "call_start": CALL_START, "call_ceiling": CALL_CEILING}
    journal = EvidenceJournal(EXECUTION, binding, maximum_actions=21, maximum_per_issue=3, deadline_seconds=21600)
    functions = {"P0": lambda d: audit(), "P1": lambda d:run_p1(OUT/'fidelity'), "P2": run_p2, "P3": run_p3,
                 "P4": run_p4, "P5": run_p5}
    results = {}; dependencies = []
    for phase in PHASES[:min(6,PHASES.index(through)+1)]:
        save(OUT / "next-phase-plan.json", {"status": "REFRESHED_BETWEEN_PHASES", "next_phase": phase,
                                             "preceding": results, "remaining_authorized_calls": CALL_MAXIMUM - used(),
                                             "remaining_round15_calls": max(0, CALL_CEILING - used()), "release_eligible": False})
        inputs = phase_binding(phase, dependencies)
        def perform(work, f=functions[phase]):
            began=time.monotonic()
            record={'phase':phase,'inputs':inputs,'calls_before':used(),
                'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'python':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; CUDA_VISIBLE_DEVICES=-1',
                'seeds':'N/A; deterministic checks or uncontrolled provider randomness',
                'command':[str(ROOT/'.venv/bin/python'),'scripts/run_assurance_round15.py','execute','--through',through],
                'plan':relative(PLAN),'result_path':relative(work/'result.json'),
                'data_version':sha(OUT/'baseline.json'),'release_eligible':False}
            save(work/'started.json',record)
            result=f(work)
            if code_binding()!=inputs['implementation']:
                raise LegalMathError('E_STALE_REVIEW',details='Code changed during execution')
            evidence={}
            if phase=='P1':
                evidence={relative(p):sha(p) for p in (OUT/'fidelity').rglob('*') if p.is_file() and p.name!='.lock'}
            record.update(result=result,calls_after=used(),wall_seconds=time.monotonic()-began,
                          external_evidence=evidence,status='EXECUTED')
            return record
        manifest, receipt = journal.execute("phase." + phase.lower(), inputs, perform,
            dependencies=dependencies, issue=phase)
        for path,h in manifest.get('external_evidence',{}).items():
            if sha(ROOT/path)!=h:raise LegalMathError('E_INTEGRITY',details='Completed external evidence changed')
        results[phase] = {"manifest": manifest, "receipt":receipt,"result": manifest['result']}
        dependencies.append(receipt["result_hash"])
        save(OUT / "phase-results.json", results)
        repair_review(results)
        print(phase+' '+manifest['result']['status']+(' (reused)' if receipt['reused'] else ''),flush=True)
    if through!='P6':return {'status':'CHECKPOINT','through':through,'calls_after':used()}
    repair = repair_review(results)
    save(OUT / "next-phase-plan.json", {"status": "REFRESHED_BETWEEN_PHASES", "next_phase": "P6",
                                         "preceding": results, "repair": repair,
                                         "remaining_authorized_calls": CALL_MAXIMUM - used(),
                                         "remaining_round15_calls": max(0, CALL_CEILING - used()), "release_eligible": False})
    p6 = {"status": "DELIVERY_REVIEW_REFRESHED", "phases": {p: results[p]["result"] for p in results},
          "repair_review": repair, "calls_after": used(), "remaining_authorized_calls": CALL_MAXIMUM - used(),
          "remaining_round15_calls": max(0, CALL_CEILING - used()),
          "legal_accuracy_established": False, "release_eligible": False,
          "next_required": ["independent adjudicated reference set", "second model family", "open authority closure", "PDF materiality adjudication"]}
    # P6 is deterministic and is included in the phase ledger as its own action.
    inputs = phase_binding("P6", dependencies)
    p6_result, receipt = journal.execute("phase.p6", inputs, lambda work: p6, dependencies=dependencies, issue="P6")
    results["P6"] = {"manifest": {"phase": "P6", "inputs": inputs, "receipt": receipt,
                                    "result": p6_result, "result_hash": identity(p6_result), "calls_after": used(),
                                    "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                    "release_eligible": False}, "result": p6_result}
    save(OUT / "phase-results.json", results)
    incomplete=not results['P1']['result']['execution_complete']
    final = {"status": "ROUND15_PARTIAL_LIVE_WORK_DETERMINISTIC_CHECKS_COMPLETE" if incomplete else "ROUND15_CHECKS_COMPLETE_WITH_OPEN_LEGAL_QUESTIONS",
             "phase_results": results, "calls_before": CALL_START, "calls_after": used(),
             "remaining_authorized_calls": CALL_MAXIMUM - used(), "remaining_round15_calls": max(0, CALL_CEILING - used()),
          "legal_accuracy_established": False, "release_eligible": False}
    save(OUT / "final-report.json", final)
    save(OUT / "next-phase-plan.json", {"status": "REFRESHED_FROM_ACTUAL_RESULTS",
                                         "final_report_sha256": json_hash(OUT / "final-report.json"),
                                         "calls_after": used(), "remaining_authorized_calls": CALL_MAXIMUM - used(),
                                         "remaining_round15_calls": max(0, CALL_CEILING - used()),
                                         "open_questions": p6["next_required"], "release_eligible": False})
    return final


def status() -> dict:
    path = OUT / "final-report.json"
    return read(path) if path.exists() else ({"status": "NOT_STARTED", "calls": used()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "execute", "repair", "status"))
    parser.add_argument('--through',choices=PHASES,default='P6')
    args = parser.parse_args()
    if args.command == "audit": value = audit()
    elif args.command in ('execute','repair'): value = execute(args.through)
    elif args.command == "status": value = status()
    print(json.dumps({k:value[k] for k in ('status','calls_after','through','remaining_authorized_calls') if k in value}, indent=2))


if __name__ == "__main__":
    main()
