"""Economic preparation only; this module never invokes an ACTUS implementation."""
from copy import deepcopy
from datetime import date, datetime, timezone
from fractions import Fraction
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
REVIEW = BASE / "reviews/actus-economic-181"
HERE = BASE / "attempts/actus-prerequisites/attempt-003"
PRIOR = BASE / "attempts/actus-prerequisites/attempt-002"
PLAN = "docs/plans/prospectus-actus-economic-preparation-2026-10-17.md"
GUIDE = ROOT / "docs/implementation/prospectus-integration-repair/official-sources/actus-pam-guide.txt"
CPP = BASE / "attempts/finance-conventions/attempt-003/quantlib-v1.38-thirty360.cpp"
SELECTOR = {"version": "economic-preparation.v1", "maximum_stage_seconds": 30,
            "maximum_new_seconds": 150, "maximum_stage_invocations": 5,
            "maximum_new_bytes": 10 * 1024**2, "seal_reserve_bytes": 256 * 1024,
            "official_core_executions": 0, "production_edits": 0}
REQUIRED = ("contractDealDate", "contractID", "contractRole", "contractType",
            "counterpartyID", "creatorID", "currency", "dayCountConvention",
            "initialExchangeDate", "maturityDate", "nominalInterestRate",
            "notionalPrincipal", "statusDate")
STAGES = ("prepare", "reference", "controls", "seal")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(name, value):
    write(HERE / name, value, exclusive=True)


def package():
    folder = ROOT / "src/legalmath"
    return {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def size(folder):
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def bound():
    authority = Authority(ROOT)
    program, tasks, _ = authority.spec()
    task = tasks["actus-prerequisites"]
    admission = read(HERE / "admission.json")
    event = next(e for e in reversed(authority.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT)),
            "Current prerequisite preparation admission required")
    require(task.get("economic_preparation") == SELECTOR and admission["task_spec"] == task
            and admission["program_sha256"] == digest(program)
            and admission["binding"] == authority.binding(task), "Admitted methods or inputs changed")
    require(not (HERE / "outputs.json").exists(), "Preparation already sealed")
    history = read(REVIEW / "history.json")
    require(package() == history["package"] and len(history["package"]) == 441,
            "Production source changed")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()),
            "Protected prior evidence changed")
    started = list((HERE / "stages").glob("*/started.json"))
    completed = list((HERE / "stages").glob("*/result.json"))
    failed = list((HERE / "stages").glob("*/failure.json"))
    require(len(started) < SELECTOR["maximum_stage_invocations"], "Invocation bound exhausted")
    require(not failed, "Failed stage needs reviewed repair; no unchanged retry")
    require(sum(read(p)["wall_seconds"] for p in completed) < SELECTOR["maximum_new_seconds"],
            "Cumulative worker-time bound exhausted")
    require(size(HERE) < SELECTOR["maximum_new_bytes"] - SELECTOR["seal_reserve_bytes"],
            "New preparation storage reserve exhausted")
    require(tasks["actus-comparison"]["depends_on"] == ["actus-prerequisites"],
            "Actual numerical dependency changed")
    return admission


def fraction_text(value):
    f = Fraction(value)
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def european_days(start, end):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    require(a < b, "Positive date interval required")
    return 360 * (b.year-a.year) + 30 * (b.month-a.month) + min(b.day, 30)-min(a.day, 30)


def validate_terms(t):
    expected = {"kind", "currency", "principal", "rate", "initial_date", "maturity_date",
                "coupon_dates", "day_count_definition", "business_day_adjustment", "eom",
                "fees", "fx", "scaling", "optionality", "default", "rate_reset"}
    require(isinstance(t, dict) and set(t) == expected, "Complete explicit economic terms required")
    require(t["kind"] == "SYNTHETIC_ECONOMIC_REFERENCE" and t["currency"] == "GBP",
            "Only the nominated synthetic GBP baseline is in scope")
    for key in ("principal", "rate", "fees"):
        require(isinstance(t[key], str) and re.fullmatch(r"-?\d+(?:/\d+)?", t[key]) is not None,
                "Canonical exact rational terms required")
    require(Fraction(t["principal"]) == 1000 and Fraction(t["rate"]) == Fraction(1, 20)
            and Fraction(t["fees"]) == 0, "Retained principal/rate/no-fee baseline required")
    require(t["initial_date"] == "2025-01-15" and t["maturity_date"] == "2026-01-15"
            and t["coupon_dates"] == [t["maturity_date"]], "Retained single annual coupon required")
    require(t["day_count_definition"] == "360*dY+30*dM+min(end_day,30)-min(start_day,30)",
            "Explicit European endpoint formula required; package enum unverified")
    require(t["business_day_adjustment"] == "NONE" and type(t["eom"]) is bool and not t["eom"],
            "Explicit unadjusted/no-EOM scenario required")
    require(all(type(t[k]) is bool and not t[k] for k in
                ("fx", "scaling", "optionality", "default", "rate_reset")),
            "Explicit absent synthetic features required")
    return t


def economic_reference(terms):
    t = validate_terms(terms)
    principal = Fraction(t["principal"])
    interest = principal * Fraction(t["rate"]) * Fraction(
        european_days(t["initial_date"], t["maturity_date"]), 360)
    def state(p, i):
        return {"principal_receivable": fraction_text(p), "interest_receivable": fraction_text(i)}
    def leg(kind, value):
        return {"kind": kind, "amount": fraction_text(value), "currency": t["currency"]}
    return {"schema": "pam-economic-reference.v1", "origin": "SYNTHETIC_HARNESS_CONTROL",
            "state_scope": "ATOMIC_DATE_GROUPS_NOT_ACTUS_INTERNAL_STATES",
            "groups": [
                {"date": t["initial_date"], "before": state(0, 0),
                 "legs": [leg("INITIAL_ADVANCE", -principal)], "after": state(principal, 0)},
                {"date": t["maturity_date"], "before": state(principal, interest),
                 "legs": [leg("INTEREST", interest), leg("PRINCIPAL", principal)], "after": state(0, 0)}]}


def compare_economic(observed, expected):
    """Strict economic-schema comparison, never an official-engine verdict."""
    diffs = []
    def walk(a, b, path):
        if type(a) is not type(b):
            diffs.append(path + ":type")
        elif isinstance(b, dict):
            if set(a) != set(b):
                diffs.append(path + ":fields")
            for key in sorted(set(a) & set(b)):
                walk(a[key], b[key], path + "." + key)
        elif isinstance(b, list):
            if len(a) != len(b):
                diffs.append(path + ":length")
            for n, (x, y) in enumerate(zip(a, b)):
                walk(x, y, path + f"[{n}]")
        elif a != b:
            diffs.append(path + ":value")
    walk(observed, expected, "economic")
    return {"economic_match": not diffs, "differences": diffs,
            "official_core_result": False, "package_acceptance": False}


def execution_gate(_untrusted_claim):
    """A supplied trace/claim cannot replace accepted current prerequisites."""
    authority = Authority(ROOT)
    state = authority.status()
    row = next(r for r in state["tasks"] if r["id"] == "actus-prerequisites")
    prior = read(PRIOR / "result.json")
    require(not prior["numerical_trial_executed"] and row["state"] != "COMPLETE",
            "Preparation scope changed: actual prerequisite acceptance needs a new plan")
    return {"execution_allowed": False, "reason": "AUTHORIZED_CORE_SOURCE_TESTS_TERMS_AND_AUDITED_MAPPING_ABSENT",
            "prerequisite_state": row["state"], "numerical_trial_executed": False}


def prepare():
    request = (PRIOR / "CORE-REQUEST.md").read_text()
    start = request.index("The first trial remains")
    end = request.index("Audit PAM schedule", start)
    guide = GUIDE.read_text()
    required_section = guide.split("## Required Terms\n", 1)[1].split("## Conditional Groups", 1)[0]
    require(tuple(line[2:] for line in required_section.splitlines() if line.startswith("- ")) == REQUIRED,
            "Pinned PAM required-term scope changed")
    terms = {"kind": "SYNTHETIC_ECONOMIC_REFERENCE", "currency": "GBP", "principal": "1000",
             "rate": "1/20", "initial_date": "2025-01-15", "maturity_date": "2026-01-15",
             "coupon_dates": ["2026-01-15"],
             "day_count_definition": "360*dY+30*dM+min(end_day,30)-min(start_day,30)",
             "business_day_adjustment": "NONE", "eom": False, "fees": "0", "fx": False,
             "scaling": False, "optionality": False, "default": False, "rate_reset": False}
    validate_terms(terms)
    for token in ("1,000 GBP", "15 January 2025", "15 January 2026", "5%", "30E/360"):
        require(token in request[start:end], "Retained synthetic baseline differs: " + token)
    cpp = CPP.read_text()
    require("case European:" in cpp and "case EurobondBasis:" in cpp and "new EU_Impl" in cpp,
            "Retained official European mapping absent")
    eu = cpp.split("Thirty360::EU_Impl::dayCount", 1)[1].split("Thirty360::IT_Impl", 1)[0]
    require("if (dd1 == 31) { dd1 = 30; }" in eu and "if (dd2 == 31) { dd2 = 30; }" in eu
            and "February" not in eu, "European endpoint definition changed")
    sources = {str(p.relative_to(ROOT)): file_hash(p) for p in
               (PRIOR / "CORE-REQUEST.md", GUIDE, GUIDE.with_suffix(".json"), CPP,
                ROOT / "src/legalmath/prospectus/successor/fixed_coupon.py")}
    for p in (GUIDE, CPP, PRIOR / "CORE-REQUEST.md", Path(__file__), ROOT / PLAN):
        target = HERE / "retained" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    save("sources.json", sources)
    save("economic-terms.json", terms)
    save("premise-provenance.json", {"source": str((PRIOR / "CORE-REQUEST.md").relative_to(ROOT)),
         "sha256": file_hash(PRIOR / "CORE-REQUEST.md"), "start": start, "end": end,
         "quote": request[start:end], "role": "EXPLICIT_SYNTHETIC_BASELINE_NOT_PROSPECTUS_TERMS",
         "formula": {"source": str(CPP.relative_to(ROOT)), "sha256": file_hash(CPP),
                     "section": "EU_Impl::dayCount and implementation switch",
                     "status": "REFERENCE_DEFINITION; ACTUS_ENUM_NOT_CHECKED"}})
    values = {"contractType": "Principal at maturity (PAM semantics only)", "contractRole": "lender perspective",
              "currency": "GBP", "dayCountConvention": "explicit European formula in economic-terms.json",
              "initialExchangeDate": "2025-01-15", "maturityDate": "2026-01-15",
              "nominalInterestRate": "1/20 per year", "notionalPrincipal": "1000 GBP",
              "statusDate": "strictly before initial exchange; no exact timestamp supplied"}
    rows = [{"attribute": key, "guide_required": True, "semantic_value": values.get(key),
             "encoding_status": "REQUIRES_CORE1.1.0_DICTIONARY_IMPLEMENTATION_AND_TESTS",
             "additional_input_required": key not in values or key == "statusDate"} for key in REQUIRED]
    save("required-terms.json", rows)
    save("mapping-gaps.json", {"official_request_emitted": False,
         "unknown_required_values": [r["attribute"] for r in rows if r["additional_input_required"]],
         "unverified": ["role/sign and core event identifiers", "timestamps/timezone/status initialization",
             "30E/360 enum versus other30/360 variants", "interest cycle and anchor encoding",
             "calendar/business-day/EOM enum values", "explicit no-feature and initial-state mappings",
             "equal-time interest/maturity event order and internal state semantics",
             "output units, event completeness and downstream answer mapping"],
         "guide_scope": "Generic60234c1e required,conditional and optional groups, not a core1.1.0 dictionary",
         "conditional_groups": [1, 2, 5, 6, 7, 8, 9],
         "conditional_features": "One annual coupon is explicit; fee/purchase/termination/scaling/prepayment/reset engines are not exercised"})
    return {"required_attributes": len(rows), "additional_required_values": sum(r["additional_input_required"] for r in rows),
            "official_request_emitted": False, "production_files_unchanged": 441}


def reference():
    terms = read(HERE / "economic-terms.json")
    expected = {"schema": "pam-economic-reference.v1", "origin": "SYNTHETIC_HARNESS_CONTROL",
        "state_scope": "ATOMIC_DATE_GROUPS_NOT_ACTUS_INTERNAL_STATES", "groups": [
            {"date": "2025-01-15", "before": {"principal_receivable": "0", "interest_receivable": "0"},
             "legs": [{"kind": "INITIAL_ADVANCE", "amount": "-1000", "currency": "GBP"}],
             "after": {"principal_receivable": "1000", "interest_receivable": "0"}},
            {"date": "2026-01-15", "before": {"principal_receivable": "1000", "interest_receivable": "50"},
             "legs": [{"kind": "INTEREST", "amount": "50", "currency": "GBP"},
                      {"kind": "PRINCIPAL", "amount": "1000", "currency": "GBP"}],
             "after": {"principal_receivable": "0", "interest_receivable": "0"}}]}
    actual = economic_reference(terms)
    require(actual == expected, "Independent declared economic table disagrees")
    probes = [("annual", "2025-01-15", "2026-01-15", 360),
              ("end31_start29", "2025-01-29", "2025-01-31", 1),
              ("nonleap_feb_end", "2025-02-28", "2025-03-31", 32),
              ("leap_feb_end", "2024-02-29", "2024-03-31", 31),
              ("january_to_feb", "2025-01-31", "2025-02-28", 28),
              ("positive_zero_count", "2025-01-30", "2025-01-31", 0),
              ("year_boundary", "2024-12-31", "2025-01-31", 30)]
    comparisons = []
    for label, start, end, days in probes:
        counted = european_days(start, end)
        require(counted == days, "Declared endpoint reference differs: " + label)
        comparisons.append({"name": label, "start": start, "end": end, "declared_days": days,
                            "actual_days": counted, "year_fraction": fraction_text(Fraction(counted, 360)),
                            "kind": "REFERENCE_FORMULA_PROBE_NOT_ACTUS_STUB_TRIAL"})
    from legalmath.prospectus.successor.fixed_coupon import year_fraction
    try:
        year_fraction("2025-01-15", "2026-01-15", "30E/360", references=[], frequency=1, eom=False)
    except ValueError as error:
        require(str(error) == "Unsupported day-count convention", "Unexpected local probe failure")
        limitation = {"input_convention": "30E/360", "actual_error": str(error),
                      "classification": "EXISTING_LOCAL_SUPPORTED_SCOPE_LIMIT; NOT_ACTUS_PACKAGE_BEHAVIOR",
                      "product_modified": False, "actual_ACTUS_trial": False}
    else:
        raise ValueError("Inspected local unsupported baseline changed")
    save("economic-reference.json", actual)
    save("independent-declared-table.json", expected)
    save("endpoint-probes.json", comparisons)
    save("local-component-limitation.json", limitation)
    return {"economic_groups": 2, "separate_cashflow_legs": 3, "endpoint_probes": len(comparisons),
            "interest": "50 GBP", "principal_repayment": "1000 GBP", "official_core_result": False}


def controls():
    expected = read(HERE / "economic-reference.json")
    positive = compare_economic(expected, read(HERE / "independent-declared-table.json"))
    require(positive["economic_match"] and not positive["package_acceptance"], "Positive reference check failed")
    def set_path(obj, path, value):
        cursor = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
    mutations = [
        ("wrong_initial_date", ["groups", 0, "date"], "2025-01-16"),
        ("wrong_maturity_date", ["groups", 1, "date"], "2026-01-16"),
        ("wrong_initial_sign", ["groups", 0, "legs", 0, "amount"], "1000"),
        ("wrong_interest", ["groups", 1, "legs", 0, "amount"], "49"),
        ("wrong_principal", ["groups", 1, "legs", 1, "amount"], "999"),
        ("wrong_currency", ["groups", 1, "legs", 0, "currency"], "EUR"),
        ("floating_amount", ["groups", 1, "legs", 0, "amount"], 50.0),
        ("wrong_open_principal", ["groups", 0, "after", "principal_receivable"], "0"),
        ("wrong_maturity_accrual", ["groups", 1, "before", "interest_receivable"], "0"),
        ("unrepaid_principal", ["groups", 1, "after", "principal_receivable"], "1000"),
        ("unpaid_accrual", ["groups", 1, "after", "interest_receivable"], "50"),
        ("false_package_origin", ["origin"], "ACTUS_CORE_1.1.0"),
        ("false_internal_state", ["state_scope"], "ACTUS_INTERNAL_STATES"),
        ("missing_principal_leg", ["groups", 1, "legs"], [expected["groups"][1]["legs"][0]]),
        ("dropped_maturity", ["groups"], [expected["groups"][0]]),
        ("extra_fee", ["groups", 1, "legs"], expected["groups"][1]["legs"] +
             [{"kind": "FEE", "amount": "0", "currency": "GBP"}]),
    ]
    results = []
    for name, path, value in mutations:
        candidate = deepcopy(expected)
        set_path(candidate, path, value)
        result = compare_economic(candidate, expected)
        require(not result["economic_match"], "Comparator missed: " + name)
        results.append({"name": name, "candidate": candidate, "actual": result})
    candidate = deepcopy(expected)
    candidate["groups"][1]["legs"][0]["amount"] = "49"
    candidate["groups"][1]["legs"][1]["amount"] = "1001"
    result = compare_economic(candidate, expected)
    require(sum(Fraction(x["amount"]) for x in candidate["groups"][1]["legs"]) == 1050
            and not result["economic_match"], "Conserved-total reallocation slipped through")
    results.append({"name": "same_total_wrong_allocation", "candidate": candidate, "actual": result})
    for field in ("before", "after"):
        candidate = deepcopy(expected)
        del candidate["groups"][1][field]
        result = compare_economic(candidate, expected)
        require(not result["economic_match"], "Missing state slipped through")
        results.append({"name": "missing_" + field + "_state", "candidate": candidate, "actual": result})
    terms = read(HERE / "economic-terms.json")
    input_results = []
    for name, action in (("missing_calendar", lambda t: t.pop("business_day_adjustment")),
                         ("implicit_eom", lambda t: t.pop("eom")),
                         ("bool_as_fee", lambda t: t.update(fees=False)),
                         ("wrong_currency", lambda t: t.update(currency="EUR")),
                         ("unidentified_daycount", lambda t: t.update(day_count_definition="30/360")),
                         ("extra_backend_default", lambda t: t.update(core_default=True))):
        candidate = deepcopy(terms)
        action(candidate)
        try:
            economic_reference(candidate)
        except ValueError as error:
            input_results.append({"name": name, "candidate": candidate, "actual_error": str(error)})
        else:
            raise ValueError("Invalid input accepted: " + name)
    gates = []
    for name, claim in (("positive_fixture", expected), ("claimed_core", {"core_version": "1.1.0", "PASS": True}),
                        ("claimed_terms", {"license_authorized": True, "core_available": True})):
        refusal = execution_gate(claim)
        require(not refusal["execution_allowed"], "Untrusted claim opened the core gate")
        gates.append({"name": name, "claim": claim, "actual": refusal})
    save("controls.json", {"positive_economic_only": positive, "output_mutations": results,
                          "invalid_inputs": input_results, "execution_gate_refusals": gates,
                          "all_observations_synthetic": True})
    return {"output_mutation_refusals": len(results), "invalid_input_refusals": len(input_results),
            "core_gate_refusals": len(gates), "actual_core_executions": 0}


def seal():
    controls = read(HERE / "controls.json")
    require(len(controls["output_mutations"]) == 19 and len(controls["invalid_inputs"]) == 6
            and len(controls["execution_gate_refusals"]) == 3, "Missing required actual controls")
    require(all(not r["actual"]["economic_match"] for r in controls["output_mutations"]),
            "Failed output control")
    for name in ("prepare", "reference", "controls"):
        require(read(HERE / "stages" / name / "result.json")["status"] == "PASS", "Incomplete stage")
    require(economic_reference(read(HERE / "economic-terms.json")) == read(HERE / "economic-reference.json"),
            "Reference drift")
    return {"preparation": "PASS", "actual_core_executions": 0, "task_complete": False,
            "production_files_unchanged": 441}


def finalize(admission):
    stages = {name: read(HERE / "stages" / name / "result.json") for name in STAGES}
    elapsed = sum(r["wall_seconds"] for r in stages.values())
    require(elapsed < SELECTOR["maximum_new_seconds"], "Cumulative bound exceeded")
    result = {"task": "actus-prerequisites", "status": "PASS", "task_complete": False,
              "scope": "ECONOMIC_REFERENCE_AND_REJECTING_COMPARATOR_PREPARATION_ONLY",
              "prerequisites_satisfied": False, "numerical_trial_executed": False,
              "actual_downstream_package_effect_evaluated": False, "package_rejection_established": False,
              "economic_groups": 2, "separate_cashflow_legs": 3, "endpoint_reference_probes": 7,
              "output_mutation_refusals": 19, "invalid_input_refusals": 6, "core_gate_refusals": 3,
              "known_local_limitation": "Existing coupon kernel does not support30E/360; not changed",
              "remaining_required_values": read(HERE / "mapping-gaps.json")["unknown_required_values"],
              "production_files_unchanged": 441, "measured_stage_body_seconds": elapsed,
              "timing_scope": "Stage-body intervals through pre-finalization seal check; final artifact writing excluded. Four invocations each have a30second alarm covering finalization, hence worker body time is bounded by120seconds.",
              "next_action": "Supply authorized core1.1.0/source/official tests/terms and explicit missing synthetic fields; audit mappings and event order before actual comparison"}
    save("result.json", result)
    save("run-manifest.json", {"git_commit": admission["git_commit"], "environment": sys.executable,
         "python": platform.python_version(), "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1; no framework import",
         "random_seeds": "N/A deterministic exact arithmetic", "plan": PLAN, "result": "result.json",
         "data_version": read(HERE / "sources.json"), "worker_commands": [stages[n]["command"] for n in STAGES],
         "measured_stage_body_seconds": elapsed,
         "timing_scope": result["timing_scope"],
         "maximum_worker_body_seconds_from_stage_alarms": 4 * SELECTOR["maximum_stage_seconds"],
         "historical_runtime": read(REVIEW / "history.json")["historical_runtime"],
         "core_network_install_native_model_subprocess_calls": 0,
         "output_artifacts": ["economic-terms.json", "economic-reference.json", "independent-declared-table.json",
             "required-terms.json", "mapping-gaps.json", "controls.json", "local-component-limitation.json", "RESULT.md"]})
    (HERE / "RESULT.md").write_text("""# ACTUS economic preparation result

The retained synthetic plain-PAM case now has an executable economic reference
and a rejecting comparator. Its lender advances GBP1000 on15January2025 and
receives separate GBP50 interest and GBP1000 principal on15January2026. The
reference preserves atomic date-group principal and accrued-interest states;
it makes no claim about ACTUS internal states or equal-time event ordering.

Nineteen altered observations were refused, including a49/1001 reallocation
that preserves the1050 total, dropped legs/states, wrong dates, currency and
signs. Six incomplete/altered term sets were refused. The positive fixture and
two unsupported access/license claims all failed to open the actual-core gate.
These are explicitly synthetic comparator controls. No ACTUS core, wrapper or
downstream package consumer was invoked. Seven exact endpoint probes validate
the declared reference formula, not the uninspected ACTUS implementation.

The thirteen generic-guide required attributes are retained. Contract deal
date, contract/counterparty/creator identifiers and an exact status timestamp
are still missing. Role, date/time, day-count, cycle/calendar/EOM and state
encodings and intraday order require the authorized version-specific code and
tests. None was silently filled. Existing local coupon code explicitly rejects
30E/360; this is a local supported-scope limitation. BASF leaves that option
unselected, so this packet neither changes that bond's convention nor alleges
a package defect. All441 production files and both prior attempts are intact.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain preparation | Exact declared reference and rejecting controls pass | No corrupt source, implicit term or production drift | Official request/event/state mappings uninspected | Supply missing authorized inputs and audit core code/tests | Fixture agreement is not core agreement |
| Keep numerical trial gated | No real core event/payoff/state trace exists | Authorized core/source/tests/terms absent; required values unresolved | Actual package behavior and downstream effects untested | Use this packet after prerequisite acceptance | No integration, package rejection, legal or settlement verdict |

The strongest alternative explanation for a later mismatch is an incorrect
economic-to-core mapping or event-order assumption on our side. Inspection of
the exact implementation, official tests and matched direct/wrapper outputs
would discriminate that explanation. The weakest evidence here is that the
guide is generic, not a core1.1.0 dictionary; therefore this preparation cannot
remove the version/source/license blocker. This is completion of preparation,
not rejection of the package or completion of the original task. Continue
independent authority routes without repeating the access search or this packet.
""")
    (HERE / "NEXT-INPUTS.md").write_text("""# Inputs before the actual ACTUS trial

The exact access specification in retained002/CORE-REQUEST.md still applies:
authorized org.actus:actus-core:1.1.0, source/build/official PAM tests, applicable
version terms/notices and permitted intended use, with service compatibility.
No request has been sent and no license agreement made.

For this synthetic baseline explicitly nominate the missing contract deal date,
contractID, counterpartyID, creatorID and exact status timestamp/timezone. They
are trial parameters rather than client facts. Audit the exact role, event,
day-count, annual-cycle/anchor, calendar, EOM, no-feature and state encodings
against those supplied bytes. Identify official equal-time order and translate
its actual trace into the economic date groups without dropping any event or
state. Preserve additional official events separately. The economic comparator
alone cannot accept the trial; actual event completeness, per-event states and
downstream use still require the original comparison evidence contract.
""")
    require(package() == read(REVIEW / "history.json")["package"], "Final production drift")
    require(size(HERE) < SELECTOR["maximum_new_bytes"] - 64*1024, "Final storage bound")
    save("outputs.json", {str(p.relative_to(HERE)): file_hash(p)
                          for p in sorted(HERE.rglob("*")) if p.is_file()})


def main():
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES, "One reviewed preparation stage required")
    stage = sys.argv[1]
    tick = time.monotonic()
    def expire(_signum, _frame):
        raise TimeoutError("30second preparation-stage bound; no unchanged retry")
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(SELECTOR["maximum_stage_seconds"])
    admission = bound()
    folder = HERE / "stages" / stage
    folder.mkdir(parents=True, exist_ok=False)
    command = [".venv/bin/python", "-m", "scripts.prospectus_actus_preparation", stage]
    save(f"stages/{stage}/started.json", {"command": command, "plan": PLAN,
         "started_at": datetime.now(timezone.utc).isoformat(), "environment": sys.executable,
         "method_sha256": file_hash(Path(__file__)), "git_commit": admission["git_commit"]})
    try:
        details = globals()[stage]()
        bound()
        result = {"status": "PASS", "command": command, "details": details,
                  "wall_seconds": time.monotonic()-tick, "ended_at": datetime.now(timezone.utc).isoformat()}
        save(f"stages/{stage}/result.json", result)
        if stage == "seal":
            finalize(admission)
        print(json.dumps(result))
    except BaseException as error:
        path = folder / "failure.json"
        if not path.exists():
            save(str(path.relative_to(HERE)), {"status": "FAIL", "error": repr(error),
                 "wall_seconds": time.monotonic()-tick})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
