import pytest
from tests.helpers import prepare_release
from legalmath.errors import LegalMathError


def test_author_separation_and_stale_reviews(db, root, tmp_path, case):
    w = prepare_release(db, root, tmp_path, case, approve=False)
    lc, bh, revision = w["lifecycle"], w["state"]["bundle_hash"], w["state"]["revision"]
    with pytest.raises(LegalMathError) as e:
        lc.transition("author", "self", bh, "approve_meaning", revision, manifest_hash=w["manifest"])
    assert e.value.code == "E_AUTHORITY"
    with db.transaction() as con:
        con.execute("UPDATE identities SET roles=? WHERE id='author'", ('["author","meaning","engineering"]',))
    with pytest.raises(LegalMathError) as e:
        lc.transition("author", "self-with-role", bh, "approve_meaning", revision, manifest_hash=w["manifest"])
    assert e.value.code == "E_RELEASE_BLOCKED"
    result = lc.transition("meaning", "good", bh, "approve_meaning", revision, manifest_hash=w["manifest"])
    assert result["state"] == "IN_REVIEW"
    with pytest.raises(LegalMathError) as e:
        lc.transition("engineer", "stale", bh, "approve_engineering", revision, manifest_hash=w["manifest"])
    assert e.value.code == "E_STALE_REVIEW"
    assert db.verify()


def test_edited_bundle_loses_approval(db, root, tmp_path, case):
    w = prepare_release(db, root, tmp_path, case)
    bundle = w["case"]["bundle"]
    bundle["interpretations"][0]["statement"] += " Changed interpretation."
    changed = w["lifecycle"].create("author", "changed", bundle, parent=w["state"]["bundle_hash"])
    assert changed["state"] == "DRAFT" and changed["bundle_hash"] != w["state"]["bundle_hash"]


def test_unresolved_issue_prevents_approval(db, root, tmp_path, case):
    w = prepare_release(db, root, tmp_path, case, approve=False)
    with db.transaction() as con:
        ih = db.put(con, "issue", {"question": "Meaning of portfolio?"})
        con.execute("INSERT INTO issues VALUES('unresolved',?,?,0)", (w["state"]["bundle_hash"], ih))
    with pytest.raises(LegalMathError) as e:
        w["lifecycle"].transition("meaning", "approve", w["state"]["bundle_hash"], "approve_meaning", w["state"]["revision"], manifest_hash=w["manifest"])
    assert e.value.code == "E_RELEASE_BLOCKED"
