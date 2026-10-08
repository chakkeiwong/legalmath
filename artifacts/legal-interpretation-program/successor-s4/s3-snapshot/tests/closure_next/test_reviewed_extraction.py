"""Adversarial intake tests: hashes alone must not admit unreviewed text."""
import copy,json
from pathlib import Path
import pytest
from scripts.prospectus_reviewed_extraction import load,sha,text_hash

@pytest.fixture
def package(tmp_path):
    for name,text in (("source.pdf","original"),("image.png","printed page"),("preview.png","preview"),("eng.dat","language")):
        (tmp_path/name).write_text(text)
    digest=sha(tmp_path/"source.pdf")
    row={"page":1,"text":"ISIN ABCO. Not eligible.","image":"image.png","image_sha256":sha(tmp_path/"image.png"),
         "review_image":"preview.png","review_image_sha256":sha(tmp_path/"preview.png")}
    raw={"source":"source.pdf","source_sha256":digest,"pages":[row],"rendered_pages":[1],"ocr_pages":[1],
         "runtime":{"language_sha256":sha(tmp_path/"eng.dat")}}
    review={"source_sha256":digest,"reviewer_type":"agent_visual_review","legal_adjudication":"PENDING","human_acceptance":"PENDING",
        "pages":[{"page":1,"raw_text_sha256":text_hash(row["text"]),"image_sha256":row["image_sha256"],
            "review_image_sha256":row["review_image_sha256"],"status":"VISUALLY_CHECKED","blank":False,
            "corrections":[{"old":"ABCO","new":"ABC0","reason":"Identifier compared with retained image"}]}]}
    doc={"source_sha256":digest,"pages":[{"page":1,"text":"ISIN ABC0. Not eligible."}],"reviewed_blank_pages":[],
         "blank_page_reviews":{},"automatic_ocr_performed":True,"review_scope":"agent_visual_review"}
    meta={"id":"example","original":"source.pdf","sha256":digest,"pages":1,"raw":"raw.json","review":"review.json",
          "text":"text.json","language_model":"eng.dat"}
    def save():
        (tmp_path/"raw.json").write_text(json.dumps(raw));meta["raw_sha256"]=sha(tmp_path/"raw.json")
        review["raw_sha256"]=meta["raw_sha256"]
        for key,obj in (("review",review),("text",doc)):
            (tmp_path/meta[key]).write_text(json.dumps(obj));meta[key+"_sha256"]=sha(tmp_path/meta[key])
    save()
    return tmp_path,meta,raw,review,doc,save

def test_reviewed_identifier_preserves_negation(package):
    root,meta,*_=package
    assert load(meta,root)["pages"][0]["text"]=="ISIN ABC0. Not eligible."

@pytest.mark.parametrize("filename",["source.pdf","raw.json","review.json","text.json","image.png","preview.png","eng.dat"])
def test_changed_bound_bytes_rejected(package,filename):
    root,meta,*_=package
    (root/filename).write_text("different")
    with pytest.raises(ValueError):load(meta,root)

@pytest.mark.parametrize("mutation",[
    "extra_edit","missing_page","duplicate_page","wrong_source","stale_review","unreviewed",
    "missing_review","out_of_range_render","ocr_not_rendered","wrong_blank","hide_text",
    "empty_reason","ambiguous_correction","wrong_image","false_ocr","string_ocr","fake_human","extra_blank",
    "string_blank","boolean_page"
])
def test_rehashed_structural_corruption_rejected(package,mutation):
    root,meta,raw,review,doc,save=package
    if mutation=="extra_edit":doc["pages"][0]["text"]="ISIN ABC0. Eligible."
    elif mutation=="missing_page":doc["pages"]=[]
    elif mutation=="duplicate_page":doc["pages"]*=2
    elif mutation=="wrong_source":raw["source"]="another.pdf"
    elif mutation=="stale_review":review["source_sha256"]="bad"
    elif mutation=="unreviewed":review["pages"][0]["status"]="PENDING"
    elif mutation=="missing_review":review["pages"]=[]
    elif mutation=="out_of_range_render":raw["rendered_pages"]=[2]
    elif mutation=="ocr_not_rendered":raw["rendered_pages"]=[];review["pages"]=[]
    elif mutation=="wrong_blank":doc["reviewed_blank_pages"]=[1]
    elif mutation=="hide_text":review["pages"][0]["blank"]=True;doc["pages"][0]["text"]=""
    elif mutation=="empty_reason":review["pages"][0]["corrections"][0]["reason"]=" "
    elif mutation=="ambiguous_correction":review["pages"][0]["corrections"][0]["old"]=""
    elif mutation=="wrong_image":review["pages"][0]["image_sha256"]="bad"
    elif mutation=="false_ocr":doc["automatic_ocr_performed"]=False
    elif mutation=="string_ocr":doc["automatic_ocr_performed"]="false"
    elif mutation=="fake_human":review["human_acceptance"]="ACCEPTED"
    elif mutation=="extra_blank":doc["blank_page_reviews"]={"2":{}}
    elif mutation=="string_blank":review["pages"][0]["blank"]="false"
    elif mutation=="boolean_page":doc["pages"][0]["page"]=True
    save()
    with pytest.raises(ValueError):load(meta,root)

def test_reviewed_blank_page_requires_matching_image(package):
    root,meta,raw,review,doc,save=package
    raw["pages"][0]["text"]="";review["pages"][0].update(blank=True,corrections=[],raw_text_sha256=text_hash(""))
    doc["pages"][0]["text"]="";doc["reviewed_blank_pages"]=[1]
    doc["blank_page_reviews"]={"1":{"reviewed_image_sha256":raw["pages"][0]["image_sha256"]}}
    save();assert load(meta,root)["reviewed_blank_pages"]==[1]
    doc["reviewed_blank_pages"]=[True];save()
    with pytest.raises(ValueError):load(meta,root)
    doc["reviewed_blank_pages"]=[1]
    doc["blank_page_reviews"]["1"]["reviewed_image_sha256"]="different"
    save()
    with pytest.raises(ValueError):load(meta,root)

def test_source_symlink_cannot_escape_worktree(package,tmp_path_factory):
    root,meta,*_=package
    outside=tmp_path_factory.mktemp("outside")/"source.pdf";outside.write_text("original")
    (root/"source.pdf").unlink();(root/"source.pdf").symlink_to(outside)
    with pytest.raises(ValueError):load(meta,root)

def test_admission_precedes_reader_execution(package):
    from scripts.prospectus_closure_intake import analyze
    root,meta,raw,review,doc,save=package
    doc["pages"][0]["text"]="Eligible.";save()
    class Reader:
        def analyze_issue(self,*args):pytest.fail("Reader ran before rejected derivative")
    with pytest.raises(ValueError):analyze(Reader(),{"documents":[{"id":"example"}]},{"example":meta},root)

def test_wrapper_corrects_only_verified_ocr_status(package):
    from scripts.prospectus_closure_intake import analyze
    root,meta,*_=package
    class Reader:
        def analyze_issue(self,*args):return {"answer":None,"extraction":[{"document":"example","automatic_ocr_performed":False}]}
    value,raw=analyze(Reader(),{"documents":[{"id":"example"}]},{"example":meta},root)
    assert value["extraction"][0]["automatic_ocr_performed"] is True
    assert raw["extraction"][0]["automatic_ocr_performed"] is False
    assert value["answer"] is None

def test_real_reviewed_corpus_replays():
    from scripts import run_prospectus_closure_next as m
    for meta in m.read(m.DATA/"reviewed-extractions.json").values():
        assert load(meta,m.ROOT)["source_sha256"]==meta["sha256"]
