"""Connect an issue-specific source proposal to the existing bank investigation."""
from copy import deepcopy
from pathlib import Path

from ..canonical import digest
from ..transaction.evidence import fields
from ..transaction import engine
from . import eligibility, instrument_sources, instrument_terms, instrument_prices, instrument_extensions, instrument_evidence

PROFILE = "instrument-investigation.v1"


def method_identity():
    files = {p.name: p.read_text() for p in Path(__file__).parent.glob("instrument_*.py")}
    return digest({"instrument": files, "bank": engine.method_identity()})


def investigate(request, store, root):
    expected={"profile", "joined_request", "dossier_sha256", "scenario_sha256"}
    if "extensions_sha256" in request: expected.add("extensions_sha256")
    fields(request, expected)
    if request["profile"] != PROFILE:
        raise ValueError("Unsupported instrument investigation profile")
    packet = instrument_sources.verify(store.json(request["dossier_sha256"]), root)
    joined_request = deepcopy(request["joined_request"])
    extensions = instrument_extensions.read(store,request.get("extensions_sha256"))
    private = instrument_evidence.attach_private(joined_request["bank_request"],store,extensions["private_records"])
    joined_request["bank_request"] = private["request"]
    context = joined_request["bank_request"]["context"]
    if (joined_request["bank_request"]["context"]["instrument_id"] != instrument_sources.KEY
            or joined_request["prospectus_source_ids"] != [instrument_sources.KEY]):
        raise ValueError("Issue-specific profile cannot be transferred to another instrument")
    joined = eligibility.investigate(joined_request, store)
    observations = deepcopy(joined["observations"])
    for name, value in packet["product_interpretation"]["values"].items():
        row = observations[name]
        if row["status"] == "CONFLICT" or (row["status"] == "KNOWN" and row["value"] != value):
            row.update(status="CONFLICT", value=None)
        else:
            row.update(status="KNOWN", value=value)
        row["truth_of_assertion"] = "SOURCE_DEPENDENT_PROPOSAL"
        row["sources"] = sorted(set(row["sources"] + [request["dossier_sha256"]]))
    event = {"status": "UNKNOWN", "reason": "Actual publication, notice, calendar and holding evidence not supplied"}
    scenario = None
    if request["scenario_sha256"] is not None:
        scenario = store.json(request["scenario_sha256"])
        fields(scenario, {"premise_kind", "product_facts", "calendar_sha256", "event", "price_history", "holdings",
                          "share_creation_date", "depository_received_date"})
        if scenario["premise_kind"] not in {"HYPOTHETICAL", "SOURCE_DEPENDENT_PROPOSAL"}:
            raise ValueError("Explicit scenario provenance required")
        if not isinstance(scenario["product_facts"], dict):
            raise ValueError("Explicit partial product premises required")
        # A scenario may fill factual gaps; it cannot overwrite derived values or
        # contradict the source proposal silently.
        forbidden = {key for _, key in eligibility.LINKS}
        for name, value in scenario["product_facts"].items():
            if name not in observations or name in forbidden or type(value) is not bool:
                raise ValueError("Unsupported/derived scenario premise")
            row = observations[name]
            if row["status"] == "CONFLICT" or (row["status"] == "KNOWN" and row["value"] != value):
                row.update(status="CONFLICT", value=None)
            else:
                row.update(status="KNOWN", value=value)
            row["truth_of_assertion"] = scenario["premise_kind"]
            row["sources"] = sorted(set(row["sources"] + [request["scenario_sha256"]]))
        if scenario["event"] is not None and scenario["calendar_sha256"] is None:
            event = {"status": "UNKNOWN", "reason": "Covered business-calendar evidence not supplied",
                "settlement": {"status": "UNKNOWN", "reason": "Event schedule requires a covered calendar"},
                "legal_event_truth": "NOT_ESTABLISHED"}
        elif scenario["event"] is not None:
            calendar = instrument_terms.Calendar(store, scenario["calendar_sha256"])
            data = scenario["event"]
            notice_evidence = None
            effective_notice = None
            if extensions["alternative_notice"] is not None:
                notice_evidence = instrument_extensions.notice(store,extensions["alternative_notice"],scenario,context)
                effective_notice = notice_evidence["notice_date"]
            if data.get("kind") == "trigger":
                fields(data, {"kind", "publication", "notice", "higher", "restoration"})
                snapshot = store.json(data["publication"]["snapshot_sha256"])
                if snapshot != {k: v for k, v in data["publication"].items() if k != "snapshot_sha256"}:
                    raise ValueError("Publication changed relative to its snapshot")
                event = instrument_terms.trigger(packet["terms"], data["publication"], calendar,
                    notice=data["notice"], higher=data["higher"], restoration=data["restoration"], notice_effective_date=effective_notice)
            elif data.get("kind") == "viability":
                fields(data, {"kind", "event", "notice", "alternative"})
                event = instrument_terms.viability(calendar, data["event"], notice=data["notice"], alternative=data["alternative"], notice_effective_date=effective_notice)
            else:
                raise ValueError("Unsupported instrument event")
            if notice_evidence is not None:
                event["notice_evidence"] = notice_evidence
                if notice_evidence["status"] != "CONDITIONAL":
                    event["status"] = "QUALIFIED"
                    event["issues"].extend(notice_evidence["issues"])
            actual = event.get("actual_notice_date")
            if actual and scenario["price_history"] is not None:
                price = instrument_prices.price_at_notice(packet["terms"], actual, scenario["price_history"])
                if extensions["price_determination"] is not None:
                    reconstructed = price
                    price = instrument_extensions.price(store,extensions["price_determination"],scenario,context,actual)
                    price["reconstructed_price"] = reconstructed
                event["price"] = price
                if price["status"] == "CONDITIONAL" and scenario["holdings"] is not None:
                    given = data["notice"]["price"]
                    if given is None or instrument_terms.amount(given) != instrument_terms.amount(price["price"]):
                        event["status"] = "QUALIFIED"
                        event["issues"].append("Notice price conflicts with reconstructed notice-date price")
                    entitlement = instrument_terms.share_entitlement(scenario["holdings"], price["price"], packet["terms"]["denomination"])
                    event["settlement"] = instrument_terms.settlement(event, entitlement,
                        share_creation_date=scenario["share_creation_date"], depository_received_date=scenario["depository_received_date"])
                else:
                    event["settlement"] = {"status": "UNKNOWN", "reason": "Price or holding premises unresolved"}
            else:
                event["settlement"] = {"status": "UNKNOWN", "reason": "Notice or complete price history missing"}
            if extensions["holder_delivery"] is not None:
                event["holder_delivery"] = instrument_extensions.delivery(store,extensions["holder_delivery"],scenario,context,event["settlement"])
    calculations, observations = eligibility.calculate(observations)
    restricted = calculations["restriction"]["pi_restriction_satisfied"]
    result = {"profile": PROFILE, "request_hash": digest(request), "method_hash": method_identity(),
        "dossier_hash": packet["dossier_hash"], "instrument": packet["instrument"],
        "joined": joined, "observations": observations, "calculations": calculations,
        "instrument_event": event, "scenario_kind": scenario["premise_kind"] if scenario else None,
        "private_evidence": {"accepted":private["accepted"],"unresolved":private["unresolved"]},
        "inventory": joined["inventory"], "dependencies": packet["dependencies"],
        "source_dependent_product_premises": len(packet["product_interpretation"]["values"]),
        "restriction_signal": "CONDITIONAL_RESTRICTION" if restricted["status"] == "KNOWN" and restricted["value"] is False else "NO_CLEARANCE",
        "decision": "QUALIFIED", "may_execute_transaction": False,
        "current_applicability": "NOT_ESTABLISHED", "legal_entailment": "NOT_ESTABLISHED",
        "human_quality_evidence": False}
    return {**result, "receipt_hash": digest(result)}


def revalidate(receipt, request, store, root):
    current = investigate(request, store, root)
    if current != receipt:
        raise ValueError("Instrument evidence, scenario or method changed; reassessment required")
    return current
