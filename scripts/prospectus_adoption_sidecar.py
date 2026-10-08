"""Offline CPU-only workers for bounded layout, UIMA and coupon trials."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path("/tmp/prospectus-adoption-tools/bin/python")


def layout(data, folder):
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, LayoutOptions
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
    from docling.datamodel.layout_model_specs import DOCLING_LAYOUT_V2
    if not 1 <= len(data["pages"]) <= 2:
        raise ValueError("First layout trial is capped at two pages")
    revision = json.loads((ROOT / "docs/implementation/prospectus-adoption/tool-setup/layout-model/receipt.json").read_text())["revision"]
    model_spec = DOCLING_LAYOUT_V2.model_copy(update={"revision": revision})
    options = PdfPipelineOptions(do_ocr=False, do_table_structure=False, document_timeout=180,
        artifacts_path=Path("/tmp/prospectus-adoption-models"),
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=4),
        layout_options=LayoutOptions(model_spec=model_spec))
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    rows = []
    for i, row in enumerate(data["pages"]):
        source = ROOT / row["path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Layout PDF changed")
        started = time.monotonic()
        converted = converter.convert(source, page_range=(row["page"], row["page"]))
        output = converted.document.export_to_dict()
        (folder / f"layout-{i}.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
        rows.append({**row, "output": f"layout-{i}.json", "status": str(converted.status),
                     "wall_seconds": time.monotonic()-started})
    return {"pages": rows, "options": options.model_dump(mode="json"), "engine_executed": True,
            "candidate": "Docling 2.60.1 layout-v2, OCR and table structure disabled for born-digital slice"}


def coupon(data, folder):
    import QuantLib as ql
    if ql.__version__ != "1.38":
        raise ValueError("QuantLib comparator version changed")
    def day(s):
        y,m,d = map(int, s.split("-"))
        return ql.Date(d,m,y)
    rows = []
    for row in data["cases"]:
        convention = row["convention"]
        if convention == "ACT_ACT_ICMA":
            refs = row["references"]
            if not refs:
                raise ValueError("Missing reference schedule; fallback forbidden")
            dates = [day(refs[0]["start"])] + [day(r["end"]) for r in refs]
            schedule = ql.Schedule(dates, ql.NullCalendar(), ql.Unadjusted, ql.Unadjusted,
                                   ql.Period(12//row["frequency"], ql.Months), ql.DateGeneration.Forward,
                                   row["eom"], [True] * (len(dates)-1))
            counter = ql.ActualActual(ql.ActualActual.ISMA, schedule)
        else:
            counter = {"ACT_ACT_ISDA": lambda: ql.ActualActual(ql.ActualActual.ISDA),
                       "ACT_365_FIXED": ql.Actual365Fixed, "ACT_360": ql.Actual360}[convention]()
        value = counter.yearFraction(day(row["start"]), day(row["end"]))
        rows.append({"id": row["id"], "year_fraction": value})
    # Independent TARGET comparator with named edition and explicit dates.
    calendar = ql.TARGET()
    dates = [{"input": d, "following": calendar.adjust(day(d), ql.Following).ISO(),
              "modified_following": calendar.adjust(day(d), ql.ModifiedFollowing).ISO()}
             for d in data["calendar_dates"]]
    return {"version": ql.__version__, "fractions": rows, "calendar": dates,
            "evaluation_date_used": False, "missing_reference_fallback_used": False}


def annotation(data, folder):
    import cassis
    sys.path.insert(0, str(ROOT / "src"))
    from legalmath.prospectus.successor.annotation_bridge import from_utf16, to_utf16
    ts = cassis.TypeSystem()
    span = ts.create_type(name="webanno.custom.LegalEvidence", supertypeName="uima.tcas.Annotation")
    for name in ("groupId", "label", "sourceSHA", "textSHA", "quote"):
        ts.create_feature(span, name=name, rangeType="uima.cas.String")
    ts.create_feature(span, name="piece", rangeType="uima.cas.Integer")
    relation = ts.create_type(name="webanno.custom.LegalRelation", supertypeName="uima.tcas.Annotation")
    for name in ("relationId", "kind"):
        ts.create_feature(relation, name=name, rangeType="uima.cas.String")
    for name in ("Governor", "Dependent"):
        ts.create_feature(relation, name=name, rangeType=span.name)
    cas = cassis.Cas(typesystem=ts)
    cas.sofa_string = data["text"]
    heads = {}
    for group in data["groups"]:
        members = []
        for i, piece in enumerate(group["spans"]):
            ann = span(begin=from_utf16(data["text"], piece["begin"]), end=from_utf16(data["text"], piece["end"]),
                       groupId=group["id"], label=group["label"], piece=i, quote=piece["quote"],
                       sourceSHA=data["source"]["source_sha256"], textSHA=data["source"]["text_sha256"])
            cas.add(ann); members.append(ann)
        heads[group["id"]] = members[0]
        for i, member in enumerate(members[1:], 1):
            cas.add(relation(begin=members[0].begin, end=members[0].end, Governor=members[0], Dependent=member,
                             relationId=group["id"]+":piece:"+str(i), kind="same_evidence_group"))
    for edge in data["relations"]:
        head = heads[edge["from"]]
        cas.add(relation(begin=head.begin, end=head.end, Governor=head, Dependent=heads[edge["to"]],
                         relationId=edge["id"], kind=edge["kind"]))
    ts.to_xml(folder / "typesystem.xml")
    cas.to_xmi(folder / "annotations.xmi")
    with (folder / "annotations.xmi").open("rb") as stream:
        restored = cassis.load_cas_from_xmi(stream, typesystem=ts)
    if restored.sofa_string != data["text"]:
        raise ValueError("CAS text changed on reimport")
    groups = {}
    for ann in restored.select(span.name):
        if ann.sourceSHA != data["source"]["source_sha256"] or ann.textSHA != data["source"]["text_sha256"]:
            raise ValueError("CAS source edition changed")
        groups.setdefault(ann.groupId, []).append(ann)
    packet = {**data, "groups": [{"id": key, "label": values[0].label, "spans": [
        {"begin": to_utf16(data["text"], v.begin), "end": to_utf16(data["text"], v.end), "quote": v.quote}
        for v in sorted(values, key=lambda v: v.piece)]} for key, values in groups.items()],
        "relations": [{"id": e.relationId, "kind": e.kind, "from": e.Governor.groupId, "to": e.Dependent.groupId}
                      for e in restored.select(relation.name) if e.kind != "same_evidence_group"]}
    (folder / "reimport.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
    return {"engine": "dkpro-cassis 0.10.1 UIMA XMI", "target": "INCEpTION 38.0",
            "round_trip": "PASS", "groups": len(groups), "relations": len(packet["relations"]),
            "inception_server_executed": False, "independent_reader": False}


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="-1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      HF_HOME="/tmp/prospectus-adoption-hf", OMP_NUM_THREADS="4")
    if Path(sys.executable).absolute() != PYTHON.absolute():
        os.execv(str(PYTHON), [str(PYTHON), "-m", "scripts.prospectus_adoption_sidecar", *sys.argv[1:]])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["layout", "coupon", "annotation"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "result.json").exists():
        raise ValueError("Immutable sidecar result exists")
    start = time.monotonic()
    try:
        data = json.loads(Path(args.input).read_text())
        result = globals()[args.kind](data, folder)
        result["execution"] = "EXECUTED"
    except Exception as exc:
        import traceback
        result = {"execution": "FAILED", "error": str(exc), "traceback": traceback.format_exc()}
    result.update(cpu_gpu="CPU; CUDA_VISIBLE_DEVICES=-1", wall_seconds=time.monotonic()-start,
                  command=sys.argv, packages={name: importlib.metadata.version(name) for name in
                  ("docling", "docling-core", "docling-ibm-models", "torch", "transformers", "QuantLib", "dkpro-cassis")})
    (folder / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"execution": result["execution"], "result": str(folder / "result.json")}, indent=2))
    if result["execution"] == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
