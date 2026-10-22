"""Bounded source-only preparation of the retained official CDM bond fixture."""
from copy import deepcopy
from decimal import Decimal
import json
import os
from pathlib import Path
import signal
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
OUT = BASE / "attempts/cdm-roundtrip/attempt-001"
HISTORY = BASE / "reviews/cdm-source-prep-183/history.json"
PLAN = "docs/plans/prospectus-cdm-field-preparation-2026-10-17.md"
REVIEW = "docs/implementation/prospectus-execution-authority/reviews/cdm-source-prep-183/REVIEW.md"
SOURCES = {
    "example_input": "docs/research/prospectus-adoption-2026-10-07/sources/cdm-bond-input/source.json",
    "example_description": "docs/research/prospectus-adoption-2026-10-07/sources/cdm-bond/source.md",
    "settlement_model": "docs/research/prospectus-adoption-2026-10-07/sources/cdm-settlement/source.txt",
    "python_readme": "docs/implementation/prospectus-integration-repair/official-sources/cdm-python-readme.txt",
    "source_pom": "docs/implementation/prospectus-integration-repair/official-sources/cdm-pom.txt",
}
RECEIPTS = {
    "example_input": "docs/research/prospectus-adoption-2026-10-07/sources/cdm-bond-input/receipt.json",
    "example_description": "docs/research/prospectus-adoption-2026-10-07/sources/cdm-bond/receipt.json",
    "settlement_model": "docs/research/prospectus-adoption-2026-10-07/sources/cdm-settlement/receipt.json",
    "python_readme": "docs/implementation/prospectus-integration-repair/official-sources/cdm-python-readme.json",
    "source_pom": "docs/implementation/prospectus-integration-repair/official-sources/cdm-pom.json",
}
LIMITS = {"max_seconds": 30, "max_new_bytes": 5 * 1024**2,
          "network": 0, "package_install": 0, "cdm_runtime": 0,
          "java_or_native_process": 0, "production_edits": 0}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field: " + key)
        result[key] = value
    return result


def parsed(path):
    return json.loads(path.read_text(), parse_float=Decimal, object_pairs_hook=unique_fields,
                      parse_constant=lambda value: require(False, "Nonfinite JSON number: " + value))


def package():
    folder = ROOT / "src/legalmath"
    return {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def all_fields(value, path=""):
    rows = {}
    if isinstance(value, dict):
        rows[path] = {"type": "object", "keys": sorted(value)}
        for key, child in value.items():
            rows.update(all_fields(child, path + "/" + key.replace("~", "~0").replace("/", "~1")))
    elif isinstance(value, list):
        rows[path] = {"type": "array", "length": len(value)}
        for index, child in enumerate(value):
            rows.update(all_fields(child, path + "/" + str(index)))
    else:
        rows[path] = {"type": type(value).__name__, "value": ds(value) if isinstance(value, Decimal) else value}
    return rows


def references(value):
    definitions, refs = {}, []
    def visit(node, path):
        if isinstance(node, dict):
            for scope in ("scoped", "external"):
                key, ref = "@key:" + scope, "@ref:" + scope
                if key in node:
                    ident = (scope, node[key])
                    require(ident not in definitions, "Duplicate reference definition")
                    definitions[ident] = path
                if ref in node:
                    refs.append((scope, node[ref], path))
            for key, child in node.items():
                visit(child, path + "/" + key)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, path + "/" + str(index))
    visit(value, "")
    for scope, target, path in refs:
        require((scope, target) in definitions, "Unresolved " + scope + " reference at " + path)
    return [{"scope": scope, "key": target, "from": path, "to": definitions[(scope, target)]}
            for scope, target, path in refs]


def ds(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def source_line(name, needle):
    text = (ROOT / SOURCES[name]).read_text()
    start = text.index(needle)
    end = text.find("\n", start)
    if end < 0:
        end = len(text)
    return {"path": SOURCES[name], "sha256": file_hash(ROOT / SOURCES[name]),
            "start": start, "end": end, "line": text.count("\n", 0, start)+1,
            "quote": text[start:end]}


def identity():
    result = {}
    for name, relative in SOURCES.items():
        source = ROOT / relative
        receipt = read(ROOT / RECEIPTS[name])
        actual = file_hash(source)
        expected = receipt["sha256"]
        require(actual == expected, "Pinned source differs from receipt: " + name)
        result[name] = {"path": relative, "sha256": actual, "receipt_path": RECEIPTS[name],
                        "url": receipt["url"], "http_status": receipt.get("http_status") or
                        receipt.get("transport", {}).get("http_code"),
                        "retrieved_utc": receipt["retrieved_utc"]}
    return result


def allowed_route():
    authority = Authority(ROOT)
    program, tasks, _ = authority.spec()
    require(program["revision"] == 183, "Reviewed preparation revision changed")
    task = tasks["cdm-roundtrip"]
    require(task["depends_on"] == [] and task.get("source_preparation_only") == LIMITS
            and task.get("actual_exchange_depends_on") == ["cdm-profile"],
            "Only the admitted source-only preparation is authorized")
    routes = read(authority.path(program["continuation_review"]["routes"]))
    row = next(r for r in routes["tasks"] if r["task"] == "cdm-roundtrip")
    require("source-field" in row["next_action"] and row["mode"] == "local",
            "Reviewed route no longer permits local source preparation")
    state = authority.status()
    status = next(r for r in state["tasks"] if r["id"] == "cdm-roundtrip")
    predecessor = next(r for r in state["tasks"] if r["id"] == "cdm-profile")
    admission = read(OUT / "admission.json")
    require(status["state"] == "ADMITTED" and status["attempt"] == str(OUT.relative_to(ROOT))
            and predecessor["state"] == "WAITING_EXTERNAL", "Admitted preparation and unprovided receiver required")
    require(admission["task_spec"] == task and admission["binding"] == authority.binding(task)
            and admission["program_sha256"] == digest(program), "Admitted preparation changed")
    require(package() == read(HISTORY)["package"] and len(package()) == 441,
            "Protected production files changed")
    return {"revision": program["revision"], "route": row, "task_state": status["state"],
            "profile_state": predecessor["state"], "actual_exchange_profile_requirement_preserved": True}


def extract(source):
    refs = references(source)
    execution = source["instruction"][0]["primitiveInstruction"]["execution"]
    payout = execution["product"]["economicTerms"]["payout"][0]
    prices = execution["priceQuantity"][0]
    price = prices["price"][0]
    qty = prices["quantity"]
    security = prices["observable"]["@data"]
    ids = {r["identifierType"]: r["identifier"]["@data"] for r in security["identifier"]}
    party_by_key = {r["@key:external"]: r for r in execution["parties"]}
    role_by_party = {r["role"]: r["partyReference"]["@ref:external"] for r in execution["counterparty"]}
    payer_role = payout["payerReceiver"]["payer"]
    receiver_role = payout["payerReceiver"]["receiver"]
    composite = price["composite"]
    dirty = price["value"]
    base, accrued = composite["baseValue"], composite["operand"]
    amount_dirty = Decimal(qty["value"]) * dirty
    amount_clean = Decimal(qty["value"]) * base
    amount_accrued = Decimal(qty["value"]) * accrued
    return {
        "trade": {"event_date": source["eventDate"], "trade_date": execution["tradeDate"]["@data"],
                  "effective_date": source["effectiveDate"], "trade_identifier": execution["tradeIdentifier"][0]["assignedIdentifier"][0]["identifier"]["@data"]},
        "security": {"type": security["@type"], "isin": ids.get("ISIN"), "name": ids.get("Name"),
                     "quantity_value": qty["value"], "quantity_unit": qty["unit"]},
        "price": {"value": ds(dirty), "unit": price["unit"], "per_unit_of": price["perUnitOf"],
                  "price_type": price["priceType"], "composite": {"base_value": ds(base),
                  "operand": ds(accrued), "operator": composite["arithmeticOperator"],
                  "operand_type": composite["operandType"]},
                  "derived_dirty_gbp": ds(amount_dirty), "derived_clean_gbp": ds(amount_clean),
                  "derived_accrued_gbp": ds(amount_accrued)},
        "literal_payout": {"type": payout["@type"], "payer_role": payer_role,
                        "payer_party_key": role_by_party[payer_role],
                        "payer_name": party_by_key[role_by_party[payer_role]]["name"]["@data"],
                        "receiver_role": receiver_role,
                        "receiver_party_key": role_by_party[receiver_role],
                        "receiver_name": party_by_key[role_by_party[receiver_role]]["name"]["@data"],
                        "settlement_type": payout["settlementTerms"]["transferSettlementType"],
                        "settlement_date": payout["settlementTerms"]["settlementDate"]["adjustableOrRelativeDate"]["adjustedDate"]["@data"],
                        "security_settlement_centre": payout["settlementTerms"].get("securitySettlementCentre"),
                        "cash_settlement_centre": payout["settlementTerms"].get("cashSettlementCentre"),
                        "legacy_settlement_centre": payout["settlementTerms"].get("settlementCentre"),
                        "settlement_type_field": payout["settlementTerms"].get("settlementType"),
                        "interpretation": "LITERAL_INPUT_ROLES; GENERATED_CASH_SECURITY_FLOW_NOT_EXECUTED"},
        "reference_resolution": refs,
        "parties": {k: {"name": v["name"]["@data"], "identifier_scheme": v["partyId"][0]["identifier"]["@scheme"],
                         "identifier": v["partyId"][0]["identifier"]["@data"]} for k, v in party_by_key.items()},
        "prose_only_claims": {"cash_buyer": "Mega Bank Inc", "cash_seller": "Global Bank",
                              "settlement_system": "Euroclear", "security_payer_role": "Party2",
                              "security_issuer": "His Majesty's Treasury",
                              "security_issuer_lei": "ECTRVYYCEF89VWYS6K36",
                              "security_transferable_product_present_in_input": False},
        "receiver_specific": {"named_receiver": None, "receiver_version": None, "receiver_profile": None,
                              "supported_runtime": None, "required_native_functions": None},
    }


def integrity_controls(source, expected):
    def set_path(obj, path, value):
        cur = obj
        for key in path[:-1]:
            cur = cur[key]
        cur[path[-1]] = value
    changes = [
        ("changed_isin", ["priceQuantity", 0, "observable", "@data", "identifier", 0, "identifier", "@data"], "GB0000000000"),
        ("changed_quantity", ["priceQuantity", 0, "quantity", "value"], 19000000),
        ("changed_quantity_currency", ["priceQuantity", 0, "quantity", "unit", "currency", "@data"], "GBX"),
        ("changed_dirty_price", ["priceQuantity", 0, "price", 0, "value"], Decimal("1.023")),
        ("changed_clean_component", ["priceQuantity", 0, "price", 0, "composite", "baseValue"], Decimal("1.019")),
        ("changed_accrued_component", ["priceQuantity", 0, "price", 0, "composite", "operand"], Decimal("0.003")),
        ("changed_cash_payer", ["product", "economicTerms", "payout", 0, "payerReceiver", "payer"], "Party2"),
        ("changed_cash_receiver", ["product", "economicTerms", "payout", 0, "payerReceiver", "receiver"], "Party1"),
        ("unresolved_party", ["counterparty", 1, "partyReference", "@ref:external"], "MissingParty"),
        ("changed_settlement_date", ["product", "economicTerms", "payout", 0, "settlementTerms", "settlementDate", "adjustableOrRelativeDate", "adjustedDate", "@data"], "2020-09-25"),
        ("changed_transfer_type", ["product", "economicTerms", "payout", 0, "settlementTerms", "transferSettlementType"], "Cash"),
        ("unresolved_quantity", ["product", "economicTerms", "payout", 0, "priceQuantity", "quantitySchedule", "@ref:scoped"], "missing-quantity"),
        ("wrong_reference_target", ["product", "economicTerms", "payout", 0, "priceQuantity", "quantitySchedule", "@ref:scoped"], "price-1"),
        ("inserted_settlement_default", ["product", "economicTerms", "payout", 0, "settlementTerms", "settlementType"], "Cash"),
    ]
    actual = []
    for name, path, value in changes:
        candidate = deepcopy(source)
        set_path(candidate["instruction"][0]["primitiveInstruction"]["execution"], path, value)
        try:
            observed = extract(candidate)
        except (KeyError, IndexError, TypeError, ValueError) as error:
            actual.append({"name": name, "detected": True, "reason": type(error).__name__})
        else:
            actual.append({"name": name, "detected": observed != expected or all_fields(candidate) != all_fields(source), "reason": "source-field-map-difference"})
        require(actual[-1]["detected"], "Source integrity control missed: " + name)
        actual[-1]["mutation"] = {"execution_relative_path": path,
                                    "replacement": ds(value) if isinstance(value, Decimal) else value}
    candidate = deepcopy(source)
    composite = candidate["instruction"][0]["primitiveInstruction"]["execution"]["priceQuantity"][0]["price"][0]["composite"]
    composite.update(baseValue=Decimal("1.021"), operand=Decimal("0.001"))
    observed = extract(candidate)
    require(observed["price"]["derived_dirty_gbp"] == expected["price"]["derived_dirty_gbp"]
            and observed != expected, "Conserved total concealed component reallocation")
    actual.append({"name": "same_dirty_total_wrong_components", "detected": True,
                   "reason": "clean/accrued amounts differ while dirty total unchanged",
                   "actual_price": observed["price"]})
    return {"scope": "LOCAL_FIXTURE_INTEGRITY_ONLY_NOT_CDM_VALIDATION", "count": len(actual), "results": actual}


def main():
    start = time.monotonic()
    def expire(_sig, _frame):
        raise TimeoutError("30-second CDM source-preparation bound")
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(LIMITS["max_seconds"])
    def guard(event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "socket.__new__",
                     "socket.connect", "ctypes.dlopen"}:
            raise RuntimeError("Forbidden source-preparation execution: " + event)
    sys.addaudithook(guard)
    try:
        require(OUT.is_dir() and not (OUT / "started.json").exists(), "Admitted new attempt required; no unchanged rerun")
        route = allowed_route()
        admission = read(OUT / "admission.json")
        write(OUT / "started.json", {"command": ["timeout", "40", ".venv/bin/python", "-m", "scripts.prospectus_cdm_source_prep"],
              "git_commit": admission["git_commit"], "plan": PLAN, "limits": LIMITS,
              "method_sha256": file_hash(Path(__file__))}, exclusive=True)
        identities = identity()
        source_path = ROOT / SOURCES["example_input"]
        source = parsed(source_path)
        expected_narrative = (ROOT / SOURCES["example_description"]).read_text()
        require("20000000" in expected_narrative and "1.022 GBP" in expected_narrative
                and "1.02 GBP" in expected_narrative and "40000 GBP" in expected_narrative
                and "Euroclear" in expected_narrative and "payer is set to Party2" in expected_narrative,
                "Pinned official example prose changed")
        mapped = extract(source)
        require(mapped["trade"]["event_date"] == mapped["trade"]["trade_date"] == "2020-09-22",
                "Trade/event date disagreement")
        require(mapped["trade"]["effective_date"] is None, "Fixture effectiveDate must remain absent")
        require(mapped["security"]["isin"] == "GB00B24FF097" and mapped["security"]["quantity_value"] == 20000000,
                "Pinned security or notional changed")
        require(mapped["price"]["composite"]["operator"] == "Add"
                and Decimal(mapped["price"]["value"]) == Decimal(mapped["price"]["composite"]["base_value"])
                    + Decimal(mapped["price"]["composite"]["operand"]), "Dirty/clean/accrued relation changed")
        require(Decimal(mapped["price"]["derived_dirty_gbp"]) == 20440000
                and Decimal(mapped["price"]["derived_clean_gbp"]) == 20400000
                and Decimal(mapped["price"]["derived_accrued_gbp"]) == 40000,
                "Exact amount arithmetic changed")
        require(mapped["literal_payout"]["settlement_type"] == "DeliveryVersusPayment"
                and mapped["literal_payout"]["settlement_date"] == "2020-09-24",
                "Pinned DvP or settlement date changed")
        require(mapped["literal_payout"]["payer_name"] == "Mega Bank"
                and mapped["literal_payout"]["receiver_name"] == "Global Bank",
                "Party role reference did not resolve to the retained counterparty")
        require(mapped["literal_payout"]["security_settlement_centre"] == "SecuritySettlementCentre"
                and mapped["literal_payout"]["cash_settlement_centre"] == "CashSettlementCentre"
                and mapped["literal_payout"]["legacy_settlement_centre"] is None,
                "Centre role values changed")
        controls = integrity_controls(source, mapped)
        model = (ROOT / SOURCES["settlement_model"]).read_text()
        for token in ("type PayoutBase:", "payerReceiver PayerReceiver", "type SettlementBase:",
                      "settlementCentre SettlementCentreEnum", "Optional settlement centre as an enumerated list: Euroclear, Clearstream.",
                      "securitySettlementCentre AssetAncillaryPartyRoleEnum", "cashSettlementCentre AssetAncillaryPartyRoleEnum"):
            require(token in model, "Retained settlement definition changed: " + token)
        readme = (ROOT / SOURCES["python_readme"]).read_text()
        pom = (ROOT / SOURCES["source_pom"]).read_text()
        require("Python 3.11 or later" in readme and "NotImplementedError" in readme
                and "LoadCodeList" in readme and "rune_register_native" in readme,
                "Retained Python runtime prerequisites changed")
        require("<java.enforced.version>[21,22)</java.enforced.version>" in pom
                and "<maven.compiler.release>11</maven.compiler.release>" in pom,
                "Retained build Java21 versus parent target11 distinction changed")
        fields = [
            {"field": "security", "source_path": "execution.priceQuantity[0].observable.@data", "source_value": mapped["security"], "receiver_question": "Does the target require instrument units/shares rather than a GBP currency unit for this bond quantity?"},
            {"field": "dirty_price", "source_path": "execution.priceQuantity[0].price[0]", "source_value": mapped["price"], "receiver_question": "Does target preserve the composite clean-price plus accrued-interest expression and exact price basis?"},
            {"field": "cash_direction", "source_path": "economicTerms.payout[0].payerReceiver", "source_value": mapped["literal_payout"], "receiver_question": "Does the receiving exchange interpret Party1 as buyer/Mega Bank paying Party2 seller/Global Bank?"},
            {"field": "security_direction", "source_path": "retained example prose only", "source_value": {"payer_role": "Party2", "seller": "Global Bank", "buyer": "Mega Bank Inc", "serialized_product_present": False}, "receiver_question": "Where is the separate transferable-security leg generated, and does it reverse the cash direction?"},
            {"field": "settlement_centre", "source_path": "economicTerms.payout[0].settlementTerms", "source_value": {"serialized_security_role": mapped["literal_payout"]["security_settlement_centre"], "serialized_cash_role": mapped["literal_payout"]["cash_settlement_centre"], "prose_institution": "Euroclear", "legacy_centre": None}, "receiver_question": "How does receiver identify Euroclear from the generic role fields, if at all?"},
            {"field": "parties", "source_path": "execution.parties/counterparty", "source_value": mapped["parties"], "receiver_question": "Are the dummy-party identifiers acceptable or must actual LEIs be supplied?"},
            {"field": "security_issuer", "source_path": "retained example prose only", "source_value": {"name": mapped["prose_only_claims"]["security_issuer"], "lei": mapped["prose_only_claims"]["security_issuer_lei"], "serialized_in_fixture": False}, "receiver_question": "Where does the security issuer identity and LEI map in the receiver profile?"},
            {"field": "receiver_profile", "source_path": "not supplied", "source_value": mapped["receiver_specific"], "receiver_question": "User must identify receiving system, CDM version/profile, runtime and required native functions."},
            {"field": "missing_required_settlement_type", "source_path": "economicTerms.payout[0].settlementTerms; model SettlementBase",
             "source_value": {"in_input": False, "model_cardinality": "1..1"},
             "receiver_question": "Does the intended function supply settlementType, or does actual explicit model/condition validation reject the example?"},
        ]
        unresolved = [r["receiver_question"] for r in fields]
        require(len(mapped["reference_resolution"]) == 5, "All five fixture references required")
        require(mapped["literal_payout"]["settlement_type_field"] is None,
                "Retained omitted settlementType changed")
        quotes = [source_line("settlement_model", "settlementType SettlementTypeEnum (1..1)"),
                  source_line("settlement_model", "securitySettlementCentre AssetAncillaryPartyRoleEnum"),
                  source_line("settlement_model", "cashSettlementCentre AssetAncillaryPartyRoleEnum"),
                  source_line("source_pom", "<java.enforced.version>"),
                  source_line("source_pom", "<maven.compiler.release>"),
                  source_line("python_readme", "- **Native Java function implementations**"),
                  source_line("python_readme", "- **Code list data loading**")]
        result = {"status": "PASS", "scope": "SOURCE_PREPARATION_ONLY", "task_complete": False,
                  "task": "cdm-roundtrip", "dependency": "cdm-profile", "profile_dependency_satisfied": False,
                  "fixture_is_authenticated_live_trade": False, "official_roundtrip_executed": False,
                  "cdm_python_or_java_imported": False, "receiver_compatibility_established": False,
                  "package_defect_established": False, "retained_source_count": len(identities),
                  "field_map_count": len(fields), "fixture_integrity_controls_detected": controls["count"],
                  "unresolved_receiver_questions": unresolved, "production_files_changed": 0,
                  "measured_body_seconds": time.monotonic() - start,
                  "timing_scope": "Measured before artifact writing;30second alarm covers full worker including sealing"}
        OUT.mkdir(parents=True, exist_ok=True)
        write(OUT / "source-identities.json", identities, exclusive=True)
        write(OUT / "field-map.json", {"source_commit": "65996cfa8defcd1f15eb457f9d2c50295b3e9691",
              "fixture": mapped, "fields": fields,
              "source_claim_boundaries": ["English example prose is not serialized fixture output",
                  "Fixture names and dummy identifiers do not authenticate a transaction or participant",
                  "Generic SecuritySettlementCentre/CashSettlementCentre values are not Euroclear",
                  "Literal payout roles and prose-only transferable-product direction need actual generated flow validation",
                  "No actual receiver profile, version, runtime or native-function list is supplied"]}, exclusive=True)
        write(OUT / "all-source-fields.json", all_fields(source), exclusive=True)
        write(OUT / "source-quotes.json", quotes, exclusive=True)
        (OUT / "retained-fixture.json").write_bytes(source_path.read_bytes())
        write(OUT / "integrity-controls.json", controls, exclusive=True)
        write(OUT / "result.json", result, exclusive=True)
        write(OUT / "run-manifest.json", {"git_commit": admission["git_commit"],
              "command": ["timeout", "40", ".venv/bin/python", "-m", "scripts.prospectus_cdm_source_prep"],
              "environment": sys.executable, "python": sys.version.split()[0],
              "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1; no GPU/framework import",
              "random_seeds": "N/A deterministic field extraction and Decimal arithmetic",
              "plan": PLAN, "result": "result.json", "source_hashes": identities,
              "measured_seconds_before_sealing": time.monotonic() - start,
              "timing_scope": result["timing_scope"], "official_runtime_calls": 0,
              "network_install_subprocess_native_gpu_calls": 0,
              "production_source_file_count": 441}, exclusive=True)
        (OUT / "RESULT.md").write_text("""# CDM bond fixture preparation

The pinned FINOS function-input example now has a complete JSON field inventory,
five resolved local references, a source-bound semantic map and fifteen actual
fixture-integrity controls. The controls include changing clean and accrued
components while preserving the dirty total. These are checks of our retained
fixture comparison, not observations from a CDM runtime or receiving system.

The arithmetic is exact: GBP20,000,000 nominal times1.022 gives GBP20,440,000;
the1.02 clean component gives GBP20,400,000 and the0.002 accrued component gives
GBP40,000. The input's payout is Party1/Mega Bank to Party2/Global Bank, with
2020-09-24 settlement. The description names Global Bank as seller and Mega Bank
Inc as buyer. Whether the generating function produces the expected cash and
opposite security legs remains untested.

The prose names Euroclear, a Treasury issuer and issuer LEI; those identities are
absent from this JSON. Its centre fields name generic roles. Its bond quantity
uses GBP rather than an instrument-unit field. The same-commit SettlementBase
definition requires settlementType, but the function-input fixture omits it.
These are concrete mapping and validation questions. Do not silently insert
defaults or conclude that the model is defective: the actual generating function,
official output, receiver profile and runtime conditions have not been exercised.
The party identifiers use the explicitly dummy identifier scheme.

The source POM enforces build JDK21 and separately declares parent compiler target11,
with an override comment. This is not proof of the user's runtime compatibility.
The Python README requires3.11+, explicit model/condition validation, and native
replacements for any required Java stubs such as LoadCodeList. No runtime was
installed or invoked. All441 production files remain identical.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
|---|---|---|---|---|---|
| Retain source preparation | Pinned source identities, exact amounts and15 controls pass | No corrupt source, lost field or production drift | Fixture assumptions and source/prose differences | Use the retained field map when the receiver is identified | No CDM conformance or package verdict |
| Keep actual exchange gated | No receiver exchange exists | Named profile/runtime/native functions absent | Actual generated legs, conditions and receiver behavior | Restore cdm-profile dependency, then review genuine supplied profile | Task and program remain incomplete |

Post-run review: an intended function may supply omitted values or interpret GBP
as bond nominal, and the prose may lag the fixture model. Exact matching official
function/output code and receiver validation would distinguish those explanations.
The weakest evidence is the absent real runtime result. This packet consumes the
first original CDM admission and leaves the second under the original allowance;
it does not reset public-source calls or permit an unchanged rerun.
""")
        require(identity() == identities and package() == read(HISTORY)["package"], "Final source/production drift")
        files = {str(p.relative_to(OUT)): file_hash(p) for p in sorted(OUT.rglob("*")) if p.is_file()}
        require(sum((OUT / n).stat().st_size for n in files) < LIMITS["max_new_bytes"]-65536, "Evidence storage bound exceeded")
        write(OUT / "outputs.json", files, exclusive=True)
        print(json.dumps(result, ensure_ascii=False))
    except BaseException as error:
        if OUT.is_dir() and not (OUT / "failure.json").exists():
            write(OUT / "failure.json", {"status": "FAIL", "error": repr(error),
                  "elapsed_seconds": time.monotonic()-start}, exclusive=True)
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
