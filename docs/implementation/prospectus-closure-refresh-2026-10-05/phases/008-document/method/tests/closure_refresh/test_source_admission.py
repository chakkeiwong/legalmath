"""Adverse tests for source-bound choices and language geometry."""
import copy, json
from pathlib import Path
import pytest
from scripts import prospectus_refresh as m
from scripts.prospectus_refresh_sources import anchor, replay, checked_choice, yes_no, region_extract, verify_region
from scripts.prospectus_refresh_admission import basf_packet, load_column_document, review
from scripts.prospectus_refresh_work import sources

XML = """<doc><page width="600" height="850">
<word xMin="50" yMin="50" xMax="90" yMax="60">Keine</word>
<word xMin="100" yMin="50" xMax="160" yMax="60">Zahlung.</word>
<word xMin="340" yMin="50" xMax="355" yMax="60">No</word>
<word xMin="365" yMin="50" xMax="410" yMax="60">payment.</word>
<word xMin="550" yMin="800" xMax="558" yMax="810">1</word>
</page></doc>"""

def extract(xml=XML, **kwargs):
    return region_extract(xml, page_number=1, split=304, body_end=775, **kwargs)

def test_geometry_retains_negation_and_both_languages():
    value=extract()
    assert value["columns"]["en"]["text"]=="No payment."
    assert value["columns"]["de"]["text"]=="Keine Zahlung."
    assert len(value["words"])==5 and value["footer_word_ids"]==[4]
    assert verify_region(value,XML)==value

@pytest.mark.parametrize("xml",[
    XML.replace('xMin="340"','xMin="300"'),
    XML.replace('yMin="50"','yMin="770"',1).replace('yMax="60"','yMax="780"',1),
    XML.replace('>1<','>confidential<'),
    XML.replace('xMax="410"','xMax="NaN"'),
    XML.replace('xMax="410"','xMax="610"'),
    XML.replace('xMin="365"','xMin="350"'),
    XML.replace('<word xMin="340" yMin="50" xMax="355" yMax="60">No</word>',''),
])
def test_invalid_or_lost_geometry_rejected(xml):
    if ">No<" not in xml:
        altered=extract(xml)
        assert altered["columns"]["en"]["text"]=="payment."
        # Raw token extraction does not invent absent words; reviewed reconstruction
        # detects a missing original token.
        with pytest.raises(ValueError):
            verify_region(extract(),xml)
    else:
        with pytest.raises(ValueError):extract(xml)

@pytest.mark.parametrize("field,value",[("split",500),("body_end",45),("page",True)])
def test_changed_region_metadata_rejected(field,value):
    result=extract();result[field]=value
    with pytest.raises(ValueError):verify_region(result,XML)

@pytest.mark.parametrize("change",["negation","drop_german","duplicate_id","wrong_line","footer"])
def test_derivative_mutation_rejected(change):
    result=extract()
    if change=="negation":result["columns"]["en"]["text"]="payment."
    if change=="drop_german":result["columns"]["de"]["text"]=""
    if change=="duplicate_id":result["columns"]["en"]["word_ids"]=[2,2]
    if change=="wrong_line":result["columns"]["en"]["lines"][0]["start"]=1
    if change=="footer":result["footer_word_ids"]=[]
    with pytest.raises(ValueError):verify_region(result,XML)

@pytest.mark.parametrize("label",["Option I","Option I A"])
def test_full_option_label_not_prefix(label):
    text="☒ Option I\n☐ Option I A"
    assert checked_choice(text,"Option I A") is False
    if label=="Option I":
        # Duplicate prefix selections must not be guessed.
        with pytest.raises(ValueError):checked_choice(text,label)

@pytest.mark.parametrize("text",["German controlling","☒ German controlling ☐ German controlling",
                                "☑ German controlling"])
def test_missing_ambiguous_unknown_checkbox_rejected(text):
    with pytest.raises(ValueError):checked_choice(text,"German controlling")

def test_explicit_unselected_option_stays_deleted():
    assert checked_choice("☐ Long coupon","Long coupon") is False

@pytest.mark.parametrize("text",["Call Yes Kündigung Nein","Call No Kündigung Ja",
                                "Call Maybe Kündigung Ja","Call Yes Kündigung Ja Call No Kündigung Nein"])
def test_conflicting_bilingual_call_rejected(text):
    with pytest.raises(ValueError):yes_no(text,"Call","Kündigung")

def test_bilingual_no_and_yes():
    assert yes_no("Call No Kündigung Nein","Call","Kündigung") is False
    assert yes_no("Call Yes Kündigung Ja","Call","Kündigung") is True

def test_actual_basf_source_scope():
    packet=basf_packet()
    choices={s["id"]:s["selected"] for s in packet["selections"]}
    assert packet["controlling_language"]=="de" and packet["translation_authority"]=="en_nonbinding"
    assert choices["dated_call"] is True and choices["interest_date_call"] is False
    assert choices["icma"] is True and choices["annual_no_stub"] is True
    assert choices["long_stub"] is False and choices["actual_365"] is False
    assert packet["template_pages_automatically_operative"] is False
    assert packet["full_dossier_status"]=="UNRESOLVED" and packet["certified_legal_answer"] is None

def test_actual_reviewed_columns_keep_full_resolution_qualifier():
    record=review()
    rows={(r["document"],r["page"]):r for r in record["source_pages"]}
    for spec in record["regions"]:
        xml=(m.ROOT/rows[(spec["document"],spec["page"])]["bbox"]).read_text()
        result=region_extract(xml,page_number=spec["page"],split=spec["split"],body_end=spec["body_end"])
        text=" ".join(result["columns"]["en"]["text"].split())
        assert all(q in text for q in record["required_english_phrases"][str(spec["page"])])
        assert "Emittentin" not in text
        assert len(result["words"])==sum(len(c["word_ids"]) for c in result["columns"].values())+len(result["footer_word_ids"])

@pytest.fixture
def bound_document(tmp_path):
    def save(name,value,binary=False):
        path=tmp_path/name
        if binary:path.write_bytes(value)
        else:path.write_text(value if isinstance(value,str) else json.dumps(value))
        return m.sha(path)
    orig=save("original.pdf",b"synthetic original fixture",True)
    base={"source_sha256":orig,"pages":[{"page":1,"text":"Keine No Zahlung. payment. 1"}]}
    base_sha=save("original.json",base)
    row={"id":"synthetic","original":"original.pdf","sha256":orig,"text":"original.json","text_sha256":base_sha,"pages":1}
    image_sha=save("page.png",b"synthetic image fixture",True)
    xml_sha=save("page.xhtml",XML)
    regions=[extract()]
    reg_sha=save("regions.json",regions)
    record={"review_role":"development_source_and_layout_review","independent_legal_adjudication":False,
            "source_pages":[{"document":"synthetic","page":1,"source_sha256":orig,
                             "image":"page.png","image_sha256":image_sha,"bbox":"page.xhtml","bbox_sha256":xml_sha}],
            "regions":[{"document":"synthetic","page":1,"split":304,"body_end":775,"line_tolerance":0.75,
                        "status":"VISUALLY_REVIEWED","scope":"extraction_only","languages":["de","en"]}],
            "required_english_phrases":{"1":["No payment."]}}
    review_sha=save("review.json",record)
    derived=copy.deepcopy(base);derived["pages"][0]["text"]="No payment."
    out_sha=save("derivative.json",derived)
    meta={"base":row,"regions":"regions.json","regions_sha256":reg_sha,
          "derivative":"derivative.json","derivative_sha256":out_sha,"review":"review.json",
          "review_sha256":review_sha,"selected_pages":[1],"analysis_language":"en","complete_legal_reading":False}
    return tmp_path,meta

def test_valid_optional_loader(bound_document):
    root,meta=bound_document
    assert load_column_document(meta,root)["pages"][0]["text"]=="No payment."

@pytest.mark.parametrize("mutation",["source","unbound_review","lost_negation_rehashed","wrong_language",
                                   "false_legal_scope","wrong_page","changed_geometry_rehashed",
                                   "wrong_review_language_rehashed","changed_image","changed_bbox"])
def test_loader_rejects_invalid_provenance_and_scope(bound_document,mutation):
    root,meta=bound_document
    if mutation=="source":(root/"original.pdf").write_bytes(b"changed")
    elif mutation=="unbound_review":(root/"review.json").write_text("{}")
    elif mutation=="lost_negation_rehashed":
        data=m.read(root/"derivative.json");data["pages"][0]["text"]="payment."
        m.write(root/"derivative.json",data);meta["derivative_sha256"]=m.sha(root/"derivative.json")
    elif mutation=="wrong_language":meta["analysis_language"]="de"
    elif mutation=="false_legal_scope":meta["complete_legal_reading"]=True
    elif mutation=="wrong_page":meta["selected_pages"]=[2]
    elif mutation=="changed_geometry_rehashed":
        data=m.read(root/"regions.json");data[0]["split"]=300
        m.write(root/"regions.json",data);meta["regions_sha256"]=m.sha(root/"regions.json")
    elif mutation=="wrong_review_language_rehashed":
        data=m.read(root/"review.json");data["regions"][0]["languages"]=["en","de"]
        m.write(root/"review.json",data);meta["review_sha256"]=m.sha(root/"review.json")
    elif mutation=="changed_image":(root/"page.png").write_bytes(b"changed")
    elif mutation=="changed_bbox":(root/"page.xhtml").write_text(XML.replace("No","Yes"))
    with pytest.raises(ValueError):load_column_document(meta,root)

def test_anchor_replays_and_rejects_boolean_page(bound_document):
    root,meta=bound_document;row=meta["base"];doc=m.read(root/row["text"])
    item=anchor(row,doc,1,"Keine No Zahlung.")
    replay(item,root)
    with pytest.raises(ValueError):anchor(row,doc,True,"Keine")
    item["page"]=True
    with pytest.raises(ValueError):replay(item,root)
