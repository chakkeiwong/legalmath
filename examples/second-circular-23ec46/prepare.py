"""Manual source-to-RuleIR example. This is not an automatic legal translator."""
import json
from pathlib import Path

from legalmath.canonical import canonical, raw_digest
from legalmath.sources.anchors import make_span
from legalmath.sources.extract import extract
from legalmath.ir.typecheck import validate_bundle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RULE = "fund_promotion.gift_prohibition_applies"
START = "2026-09-01T00:00:00.000000Z"
END = "2026-10-01T00:00:00.000000Z"
AT = "2026-09-22T00:00:00.000000Z"
FIELDS = ("is_distributor", "promotes_sfc_authorised_fund", "specific_product_promotion",
          "particular_product_type_promotion", "gift_offered", "fee_discount_only")


def main():
    oracle = json.loads((HERE / "oracle.json").read_text())
    freeze = json.loads((HERE / "oracle-freeze.json").read_text())
    assert raw_digest((HERE / "oracle.json").read_bytes()) == freeze["oracle_sha256"]
    raw = (ROOT / ".localresources/sfc/23EC46.json").read_bytes()
    assert raw_digest(raw) == freeze["retained_raw_sha256"]
    text, _ = extract(raw, "application/json")
    # The retained HTML contains 18 numbered paragraphs and four footnotes.
    # These locators are source observations, not a claim of automated legal coverage.
    numbered_lines = [2, 9, 14, 19, 28, 33, 38, 43, 50, 55, 60, 67, 72, 77, 84, 89, 94, 99]
    footnote_lines = [115, 117, 119, 121]
    lines = text.splitlines(keepends=True)
    offsets, total = [], 0
    for line in lines:
        offsets.append(total)
        total += len(line)
    dispositions = [
        "Context for the selected distributor/fund profile; actor and legal scope require review.",
        "Background observation; additional product features are not themselves classified by this test.",
        "Background on standing investment mandates; outside this selected control.",
        "Background on marketing practices; not an executable permission or prohibition here.",
        "Guaranteed-return components; not calculated or classified here.",
        "Structured-product classification is qualified and requires separate legal assessment.",
        "Section 103 public-invitation offence, authorisation and exemptions; separate control required.",
        "Non-guaranteed fund disclosure and misleading impressions; separate control required.",
        "Context: incentives may be gifts even if not structured products; do not infer classification automatically.",
        "SELECTED: gift restriction for a specific product or product type, with the fee/charge-discount exception.",
        "Restates Section 103 and Code restrictions; cannot be reduced to this one gift condition.",
        "Background on imposed lock-up periods/dealing frequency; outside selected control.",
        "Fairness and redemption-right restriction; separate control and dealing evidence required.",
        "Administrative cut-offs and best endeavours; qualitative review and separate control required.",
        "Misleading/deceptive service advertisements; separate assessment required.",
        "Advertising Guidelines dependency; separate control and versioned source required.",
        "Risk-free/deposit-like marketing representations; separate control required.",
        "Monitoring/enforcement notice; no executable new numeric rule inferred.",
    ]
    inventory, spans = [], {}
    for i, line_number in enumerate(numbered_lines + footnote_lines):
        ident = f"fund.p{i+1}" if i < 18 else f"fund.footnote{i-17}"
        start, quote = offsets[line_number], lines[line_number].rstrip("\r\n")
        span = make_span(ident, "23EC46", raw, text, start, start + len(quote))
        spans[ident] = span
        disposition = dispositions[i] if i < 18 else "Referenced authority/definition; retain as an unresolved external dependency where used."
        inventory.append({"source_span": span, "disposition": disposition,
            "rule_ids": [RULE] if i in (0, 8, 9, 20) else []})
    assert "other than a discount" in text[spans["fund.p10"]["start"]:spans["fund.p10"]["end"]]
    used = ["fund.p1", "fund.p9", "fund.p10", "fund.footnote3"]
    def fact(name): return {"node_id": "input." + name, "op": "fact", "name": name}
    bundle = {"spec_version": "0.1", "bundle_id": "fund_promotion.gift_test",
        "valid_from": START, "valid_until": END, "source_spans": [spans[k] for k in used],
        "interpretations": [{"id": "meaning.gift_test", "basis": "reviewer_interpretation",
            "statement": "UNREVIEWED agent-authored paragraph-10 prohibition candidate. Assess one incentive component using reviewed gift, fee-discount and promotional-link facts. TRUE is a prohibition trigger; FALSE and OUT_OF_SCOPE grant no permission. Actor/fund scope and validity interval are deliberately narrow synthetic test settings. Additional returns are not automatically classified as gifts. Other circular requirements remain outside this subcondition.",
            "source_span_ids": used, "issue_ids": ["issue.scope_version", "issue.incentive_classification", "issue.promotional_link", "issue.code_faq", "issue.other_controls"]}],
        "facts": [{"name": k, "type": "bool", "description": oracle["fact_definitions"][k]} for k in FIELDS],
        "rules": [{"id": RULE, "type": "bool", "interpretation_id": "meaning.gift_test", "source_span_ids": used,
            "scope": {"node_id": "profile", "op": "all", "args": [fact(k) for k in FIELDS[:2]]},
            "body": {"node_id": "prohibition", "op": "all", "args": [fact("gift_offered"),
                {"node_id": "promotional_link", "op": "any", "args": [fact("specific_product_promotion"), fact("particular_product_type_promotion")]},
                {"node_id": "outside_discount_exception", "op": "not", "arg": fact("fee_discount_only")} ]}}]}
    assert not validate_bundle(bundle), validate_bundle(bundle)
    (HERE / "gift-control.bundle.json").write_bytes(canonical(bundle))
    (HERE / "circular-disposition.json").write_bytes(canonical({"authority": "UNREVIEWED_AGENT_INVENTORY",
        "numbered_paragraphs": 18, "footnotes": 4, "selected_executable_paragraphs": [10], "provisions": inventory}))
    print("Prepared unreviewed paragraph-10 candidate and dispositions for 18 paragraphs plus four footnotes.")


if __name__ == "__main__": main()
