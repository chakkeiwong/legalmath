from copy import deepcopy
from legalmath.review.lifecycle import Lifecycle
from legalmath.review.releases import Releases
from legalmath.sources.intake import import_spi

IDENTITIES = {
    "author": {"token": "synthetic-author-token", "roles": ["author"]},
    "meaning": {"token": "synthetic-meaning-token", "roles": ["meaning"]},
    "engineer": {"token": "synthetic-engineer-token", "roles": ["engineering"]},
}


def prepare_release(db, root, tmp_path, case, *, approve=True):
    case = deepcopy(case)
    case["bundle"]["bundle_id"] = "synthetic.release"
    for item in case["bundle"]["interpretations"]:
        item["basis"] = "synthetic_test"
        item["statement"] = "Engineering workflow test; the bank interpretation remains unapproved."
        item["issue_ids"] = []
    lc, rel = Lifecycle(db), Releases(db)
    lc.register(IDENTITIES)
    import_spi(db, root)
    state = lc.create("author", "create", case["bundle"])
    bh = state["bundle_hash"]
    inventory = [{"source_span": span, "disposition": "Synthetic financial-subcondition profile; scope and meaning explicitly limited to the test.", "rule_ids": [case["rule_id"]]} for span in case["bundle"]["source_spans"]]
    state = lc.record_coverage("meaning", "coverage", bh, inventory, state["revision"])
    a = {"assessment_id": "test.scope", "bundle_hash": bh, "legal_entity": "synthetic.bank", "regulated_role": "synthetic.distributor",
        "activity": "synthetic.solicited", "product_class": "synthetic.funds", "client_class": "synthetic.individual", "jurisdiction": "HK",
        "valid_from": case["bundle"]["valid_from"], "valid_until": case["bundle"]["valid_until"], "conclusion": "in_scope",
        "reason": "Public synthetic engineering scenario only", "source_span_ids": [case["bundle"]["source_spans"][0]["id"]], "reviewer_id": "meaning"}
    app = lc.assess("meaning", "scope", a)
    build = rel.build("engineer", "build", bh, tmp_path / "build", root / ".localresources/java-toolchain/jdk-17.0.20.1+1", [case])
    manifest = rel.prepare("engineer", "prepare", build["build_manifest_hash"], build["verification_report_hash"], app["applicability_hash"], a["valid_from"], a["valid_until"])["java_release_manifest_hash"]
    state = lc.transition("author", "submit", bh, "submit", state["revision"])
    if approve:
        state = lc.transition("meaning", "review-meaning", bh, "approve_meaning", state["revision"], manifest_hash=manifest)
        state = lc.transition("engineer", "review-engineering", bh, "approve_engineering", state["revision"], manifest_hash=manifest)
    return {"case": case, "state": state, "manifest": manifest, "build": build, "app": app, "releases": rel, "lifecycle": lc}
