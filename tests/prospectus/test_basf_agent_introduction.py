import gzip, json
from pathlib import Path
import pytest
from legalmath.prospectus.basf_agent_introduction import associations, source_groups


@pytest.fixture
def products():
    root = Path(__file__).resolve().parents[2]
    path = root / "docs/implementation/prospectus-execution-authority/attempts/basf-meanings/attempt-013/products.json.gz"
    return json.loads(gzip.decompress(path.read_bytes()))


def test_role_links_keep_placeholder_and_excluded_branch(products):
    groups = source_groups(products); rows = associations(groups)
    assert [r["id"] for r in rows] == ["initial-fiscal-agent", "initial-paying-agent", "initial-calculation-agent"]
    assert rows[0]["office_status"] == "SOURCE_REPORTED_SELECTED_BLOCK"
    assert rows[2]["office_status"] == "UNRESOLVED"
    assert rows[2]["named_entity"] == "NatWest Markets N.V."
    assert all(r["assembly_role"] == "EXCLUDED" for r in groups["excluded_cds_branch"])
    assert [r["source"]["quote"] for r in rows[0]["final_term_label"]] == [
        "Fiscal and Paying Agent", "Fiscal Agent und Zahlstelle",
        "Deutsche Bank Aktiengesellschaft", "Deutsche Bank Aktiengesellschaft"]
    assert [r["source"]["quote"] for r in rows[2]["final_term_label"]] == [
        "Calculation Agent", "Berechnungsstelle", "NatWest Markets N.V.", "NatWest Markets N.V."]


def test_mixed_caption_does_not_enter_introduction(products):
    groups = source_groups(products)
    first = groups["introduction"][0]
    assert first["selected_start"] == 45
    assert first["selected_text"].startswith("Der anfänglich bestellte Fiscal Agent")
    assert not first["selected_text"].startswith("(1) Bestellung")
    assert first["selected_sources"]


@pytest.mark.parametrize("change", ["intro-role", "cds-role", "placeholder-text", "final-name"])
def test_changed_source_or_selection_is_refused(products, change):
    import copy
    altered = copy.deepcopy(products)
    selected = {u["unit"]: u for u in altered["P2"]["payload"]["assembly"]["units"]}
    base = "basf-base-september-2022-exchange"
    final = "basf-2032-final"
    if change == "intro-role": selected[base + ":p123:l82"]["role"] = "OPERATIVE"
    elif change == "cds-role": selected[base + ":p124:l22"]["role"] = "OPERATIVE"
    elif change == "placeholder-text": selected[base + ":p124:l44"]["text"] = "NatWest London"
    else: selected[final + ":p7:l28"]["text"] = "Deutsche Bank Aktiengesellschaft"
    with pytest.raises(ValueError): source_groups(altered)
