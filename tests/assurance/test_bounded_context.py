"""Discriminating controls for real local context components; no model quality claims."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from copy import deepcopy
from pathlib import Path
import sys
import pytest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
pytest.importorskip("llama_index.core")
from legalmath.errors import LegalMathError
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import (
    ContextRoute, Limits, tokenizer, tree_synthesis, citation_dependencies)
from legalmath.interpretation.search.providers import Completion
from scripts.legal_product_completion import prepare_bounded_context, run_bounded_context

TOKENIZER=ROOT/".localresources/legal-context-methods-2026-10-12/cl100k_base.tiktoken"


@pytest.fixture(scope="module")
def encode():
    return tokenizer(TOKENIZER)


def envelope(texts=None):
    texts = texts or ["A provider must supervise custody. See the exception.",
                      "Unrelated administrative history.",
                      "Exception: the duty does not apply to a different provider."]
    return {"source_packet":{"units":[{"unit_id":f"u{i}","locator":f"paragraph {i}",
                "text":text,"span":{"source_id":"doc"},"normative":True}
            for i,text in enumerate(texts)],"authority":"TEST"},
        "source_qualification":{"limitations":["Synthetic test only."]},
        "original_questions":[{"question_id":"q","text":"What is the custody duty and exception?"}],
        "answer_acceptance":{"acceptance_obligations":[{"id":"o1","statement":"Evaluate the exception"}],
                             "original_readings":[{"id":"r1","statement":"Two rival interpretations"}]}}


def unresolved(packet):
    return {"records":[{"id":r["id"],"status":"UNRESOLVED","findings":[],
                       **({'observations': []} if packet['request']['task'] == 'REVIEW_REQUIREMENTS' else {}),
                       "open_dependencies":["Need source-supported interpretation"]}
                      for r in packet["request"]["records"]]}


class Provider:
    live=False
    def __init__(self,fail_first=False):
        self.calls=0
        self.fail_first=fail_first
    def complete(self,request,schema,settings):
        self.calls+=1
        if self.fail_first and self.calls==1:
            raise ValueError("One isolated invalid response")
        return Completion(unresolved({"request":request}),{"scripted":True})


def test_library_chunks_reconstruct_repeated_unicode_and_whitespace(encode):
    text=("  duty 條文 applies.\n\nException remains. \t"*45)+" END  "
    route=ContextRoute(envelope([text]),encode,limits=Limits(chunk_tokens=40,overlap_tokens=20))
    rows=[route.records[i] for i in route.by_unit["u0"]]
    assert len(rows)>3
    recovered=""
    for row in rows:
        assert row["start"]<=len(recovered)
        assert text[row["start"]:row["end"]]==row["text"]
        recovered+=row["text"][len(recovered)-row["start"]:]
    assert recovered==text


def test_two_readers_and_every_requirement_have_destinations(encode):
    route=ContextRoute(envelope(),encode)
    packets,blocked=route.reading_plan()
    assert not blocked
    for reader in ("reader-1","reader-2"):
        assert {r["unit_id"] for p in packets if p["request"]["reader"]==reader
                for r in p["request"]["records"]}=={"u0","u1","u2"}
    assert {r["id"] for p in packets for r in p["request"]["records"]}==set(route.records)
    assert len([r for r in route.records.values() if r["kind"]=="obligation"])==1


def test_original_fields_reconstruct_even_after_metadata_partition(encode):
    original = envelope(["rule and exception " * 150,"Repeated occurrence.","Repeated occurrence."])
    original["source_packet"]["units"][0]["extraction_warning"] = {"reason":"test","empty":[]}
    original["large_metadata"] = [{"ordinal":i,"terms":["definition "*60,"exception "*60]}
                                  for i in range(4)]
    route = ContextRoute(original,encode,limits=Limits(chunk_tokens=50,overlap_tokens=25))
    assert route.reconstruct() == original
    changed = next(row for row in route.records.values() if row["kind"] == "source")
    changed["start"] += 1
    with pytest.raises(LegalMathError):
        route.reconstruct()


def test_expansion_uses_real_postprocessor_and_keeps_occurrences(encode):
    e=envelope(["custody responsibility","except during suspension","same words","same words"])
    route=ContextRoute(e,encode,limits=Limits(retrieval_hits=1))
    raw=route.retrieve("custody",expand=False)
    expanded=route.retrieve("custody",expand=True)
    assert raw["hit_ids"]==expanded["hit_ids"]
    assert len(expanded["record_ids"])>len(raw["record_ids"])
    assert len(route.by_unit)==4 and route.by_unit["u2"]!=route.by_unit["u3"]


def test_large_parent_expansion_selects_neighbor_chunks_without_restoring_whole_document(encode):
    e = envelope(["administration "*6000 + " custody exception " + "administration "*6000])
    route = ContextRoute(e,encode,limits=Limits(retrieval_hits=1))
    hit = route.retrieve("custody",expand=True)
    assert 1 < len(hit["record_ids"]) <= 3
    assert len(hit["record_ids"]) < len(route.by_unit["u0"])
    packet = route.make_packet("QUESTION_SOURCE_REVIEW",hit["record_ids"])
    assert packet["measurement"]["tokens"] <= route.limits.input_tokens


def test_remote_exception_requires_explicit_bridge(encode):
    texts=["custody must be supervised"]+[f"independent history {i}" for i in range(15)]+["Except where another actor retains custody."]
    route=ContextRoute(envelope(texts),encode,limits=Limits(retrieval_hits=1))
    hits=route.retrieve("custody supervised")
    assert not set(route.by_unit["u16"]) & set(hits["record_ids"])
    packets,blocked=route.dependency_packets([{"id":"remote","unit_ids":["u0","u16"]}])
    assert not blocked
    assert {r["unit_id"] for r in packets[0]["request"]["records"]}=={"u0","u16"}


def test_missing_and_oversized_dependency_preserves_independent_one(encode):
    e=envelope(["x "*1200,"small relevant condition"])
    route=ContextRoute(e,encode,limits=Limits(input_tokens=1600,chunk_tokens=200,overlap_tokens=100))
    packets,blocked=route.dependency_packets([
        {"id":"big","unit_ids":["u0"]},{"id":"missing","unit_ids":["unknown"]},
        {"id":"valid","unit_ids":["u1"]}])
    assert [p["request"]["dependency"]["id"] for p in packets]==["valid"]
    assert {b["id"] for b in blocked}=={"big","missing"}


@pytest.mark.parametrize("fault",["duplicate","omit","fabricate","unsupported","empty_reason","packet_change","source_change"])
def test_bad_readings_cannot_enter_aggregation(encode,fault):
    route=ContextRoute(envelope(),encode)
    packet=route.make_packet("READ_SOURCE",route.by_unit["u0"]+route.by_unit["u1"])
    value=unresolved(packet)
    if fault=="duplicate":value["records"][1]=deepcopy(value["records"][0])
    if fault=="omit":value["records"].pop()
    if fault in ("fabricate","unsupported"):
        value["records"][0].update(status="PROPOSED",findings=[{"statement":"Duty discharged",
            "support":[{"record_id":route.by_unit["u0"][0],"quote":"fabricated words"}] if fault=="fabricate" else [],
            "contrary":[]}])
    if fault=="empty_reason":value["records"][0]["open_dependencies"]=[]
    if fault=="packet_change":packet["request"]["instructions"]="changed"
    if fault=="source_change":route.envelope["source_packet"]["units"][0]["text"]="changed"
    with pytest.raises(Exception):
        route.validate_response(packet,value)


def test_failed_call_does_not_block_independent_requests(encode,tmp_path):
    route=ContextRoute(envelope(),encode,limits=Limits(records_per_request=1))
    packets,_=route.reading_plan()
    provider=Provider(fail_first=True)
    result=route.execute(packets,provider,tmp_path/"run")
    assert result["outcomes"][0]["status"]=="FAILED"
    assert all(x["status"]=="VALIDATED_PROPOSAL" for x in result["outcomes"][1:])
    assert provider.calls==len(packets)


def test_limits_prevent_dispatch_and_live_calls(encode,tmp_path):
    route=ContextRoute(envelope(),encode)
    packets,_=route.reading_plan()
    provider=Provider()
    result=route.execute(packets,provider,tmp_path/"bounded",maximum_calls=1)
    assert provider.calls==1
    assert all(x["status"]=="BLOCKED" for x in result["outcomes"][1:])
    provider.live=True
    with pytest.raises(LegalMathError) as error:
        route.execute(packets,provider,tmp_path/"live")
    assert error.value.code == "E_AUTHORITY"


def test_original_product_entry_delivers_library_prepared_records(tmp_path):
    route,result=run_bounded_context(envelope(),TOKENIZER,Provider(),tmp_path/"product")
    assert all(x["status"]=="VALIDATED_PROPOSAL" for x in result["outcomes"])
    assert not result["complete_reading_established"]
    assert not result["legal_acceptance"]
    import json
    assert json.loads((tmp_path/"product/result.json").read_text()) == result


def test_real_hierarchy_uses_multiple_levels_with_finite_output(encode):
    result=tree_synthesis(["Legal source statement. "*120]*6,"Duty?",encode,
        lambda p:"UNRESOLVED: inspect source.",input_tokens=600,output_tokens=40,maximum_calls=32)
    assert len(result["calls"])>1 and len(result["level_tokens"])>1
    assert result["level_tokens"][-1]<result["level_tokens"][0]
    assert max(x["prompt_tokens"] for x in result["calls"])<=600
    assert not result["legal_acceptance"]


def test_hierarchy_call_and_output_bounds(encode):
    with pytest.raises(LegalMathError):
        tree_synthesis(["text "*800]*4,"Duty",encode,lambda p:"no result",
                       input_tokens=400,output_tokens=30,maximum_calls=1)
    with pytest.raises(LegalMathError):
        tree_synthesis(["text"],"Duty",encode,lambda p:"unbounded "*100,
                       input_tokens=400,output_tokens=30)


def footnote_index(e):
    index = {"packet_hash":digest(e["source_packet"]),"units":{
        "u0":{"locators":["P14"],"status":"LOCATED","unit_hash":digest(e["source_packet"]["units"][0])},
        "u2":{"locators":["FN5"],"status":"LOCATED","unit_hash":digest(e["source_packet"]["units"][2])}},
        "footnote_links":[{"from":"P14","to":"FN5"}]}
    index["index_hash"] = digest(index)
    return index


def test_explicit_footnote_dependency(encode):
    e=envelope()
    e["legal_indexes"]=[footnote_index(e)]
    deps,missing=citation_dependencies(e)
    assert not missing
    assert set(deps[0]["unit_ids"])=={"u0","u2"}


@pytest.mark.parametrize("fault",["missing","ambiguous","stale_unit","stale_index"])
def test_incomplete_footnote_never_looks_like_complete_bridge(fault):
    e = envelope()
    index = footnote_index(e)
    if fault == "missing":
        del index["units"]["u2"]
    if fault == "ambiguous":
        index["units"]["u2"]["status"] = "AMBIGUOUS"
    if fault == "stale_unit":
        index["units"]["u2"]["unit_hash"] = "0"*64
    if fault != "stale_index":
        index["index_hash"] = digest({k:v for k,v in index.items() if k != "index_hash"})
    else:
        index["footnote_links"][0]["to"] = "FN6"
    e["legal_indexes"] = [index]
    dependencies, unresolved = citation_dependencies(e)
    assert not dependencies and unresolved


def test_remote_definition_and_boundary_relation_remain_delivered(encode):
    text = "background "*20 + "Duty applies unless the defined exception holds. " + "details "*20
    e = envelope([text]+["history "*20 for _ in range(10)]+["Defined exception means the entrusted actor has ceased operation."])
    route = ContextRoute(e,encode,limits=Limits(chunk_tokens=20,overlap_tokens=10))
    rows = [route.records[i]["text"] for i in route.by_unit["u0"]]
    assert any("unless the defined exception holds" in text for text in rows)
    packets,blocked = route.dependency_packets([{"id":"remote-definition","unit_ids":["u0","u11"]}])
    assert not blocked
    assert {row["unit_id"] for row in packets[0]["request"]["records"]} == {"u0","u11"}


@pytest.mark.parametrize("fault",[None,"duplicate","source_gap"])
def test_exact_footnote_bridge_across_contiguous_extraction_units(encode,fault):
    rule = "P14 This rule is qualified by a distant footnote."
    footnote = "FN5 This exception concerns the same defined actor."
    text = "background "*100 + rule + " history "*200 + footnote + " end "*100
    if fault == "duplicate":
        text += rule
    cut = text.index(rule)+20
    e = envelope([text[:cut],text[cut:]])
    for i,u in enumerate(e["source_packet"]["units"]):
        start = 0 if i==0 else cut
        u["span"].update(start=start,end=start+len(u["text"]),text_sha256=digest(text))
    if fault == "source_gap":
        e["source_packet"]["units"][1]["span"]["start"] += 1
    index = {"packet_hash":digest(e["source_packet"]),
        "units":{u["unit_id"]:{"unit_hash":digest(u),"locators":[],"status":"UNLOCATED"}
                 for u in e["source_packet"]["units"]},
        "records":[{"locator":"P14","text":rule},{"locator":"FN5","text":footnote}],
        "footnote_links":[{"from":"P14","to":"FN5"}]}
    index["index_hash"] = digest(index)
    e["legal_indexes"] = [index]
    dependencies,unresolved = citation_dependencies(e)
    if fault:
        assert not dependencies and unresolved
        return
    assert not unresolved
    spans = dependencies[0]["source_spans"]
    units = {u["unit_id"]:u for u in e["source_packet"]["units"]}
    for locator,expected in (("P14",rule),("FN5",footnote)):
        assert "".join(units[s["unit_id"]]["text"][s["start"]:s["end"]]
                       for s in spans if s["locator"]==locator) == expected
    route = ContextRoute(e,encode,limits=Limits(chunk_tokens=100,overlap_tokens=50))
    packets,blocked = route.dependency_packets(dependencies)
    assert packets and not blocked
    assert len(packets[0]["request"]["records"]) < len([r for r in route.records.values() if r["kind"]=="source"])

