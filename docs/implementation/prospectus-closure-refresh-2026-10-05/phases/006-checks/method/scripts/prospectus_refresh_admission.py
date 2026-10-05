"""Reviewed source admission and frozen-reader comparison for two exposed cases."""
import copy, json, re, sys
from pathlib import Path
from scripts import prospectus_refresh as m
from scripts.prospectus_refresh_work import sources, BASF, SUPPLEMENT, ANNUAL, S1, S4, OLD
from scripts.prospectus_refresh_sources import anchor, norm, replay, checked_choice, yes_no, region_extract, verify_region

def source_document(row):
    m.verify_bindings({row["original"]:row["sha256"],row["text"]:row["text_sha256"]})
    doc = m.read(m.ROOT / row["text"])
    m.require(doc["source_sha256"] == row["sha256"], "Wrong extraction/source pair")
    m.require([p["page"] for p in doc["pages"]] == list(range(1,row["pages"]+1)), "Wrong page mapping")
    m.require(all(type(p["page"]) is int for p in doc["pages"]), "Invalid page type")
    return doc

def review():
    path = m.OUT / "source-review.json"
    record = m.read(path)
    m.require(record["schema"] == "prospectus-refresh-source-review.v1" and
              record["review_role"] == "development_source_and_layout_review" and
              record["independent_legal_adjudication"] is False and record["human_acceptance"] is False,
              "Review scope misrepresented")
    prepared = m.latest("prepare") / "prepared.json"
    m.require(record["prepared"] == m.relative(prepared), "Review refers to old preparation")
    m.require(record["source_pages"] == m.read(prepared), "Source image review incomplete or changed")
    docs = sources()
    for row in record["source_pages"]:
        m.require(docs[row["document"]]["sha256"] == row["source_sha256"], "Reviewed wrong source")
        m.verify_bindings({row["image"]:row["image_sha256"]})
        if "bbox" in row:
            m.verify_bindings({row["bbox"]:row["bbox_sha256"]})
    m.require([r["page"] for r in record["regions"]] == [36,37,38], "Reviewed region pages missing/reordered")
    for spec in record["regions"]:
        m.require(spec["document"] == "deutsche-at1-2025" and spec["languages"] == ["de","en"] and
                  spec["status"] == "VISUALLY_REVIEWED" and spec["scope"] == "extraction_only",
                  "Unreviewed/incorrect region scope")
    return record

CHECKBOXES = [
    ("fixed_rate",3,"Fixed Rate Notes (Option I)",True),
    ("temporary_global",3,"Temporary Global Note exchangeable for Permanent Global Note (TEFRA D)",True),
    ("cbl",3,"Clearstream Banking S.A.",True),
    ("euroclear",3,"Euroclear Bank SA/NV",True),
    ("cbf",3,"Clearstream Banking AG",False),
    ("cds",3,"CDS & Co., as nominee for CDS Clearing and Depository Services Inc.",False),
    ("new_global",3,"New Global Note",True),
    ("classical_global",3,"Classical Global Note",False),
    ("icma",5,"Actual/Actual (ICMA Rule 251)",True),
    ("annual_no_stub",5,"annual interest payment (excluding the case of short or long c oupons)",True),
    ("annual_short",5,"annual interest payment (including the case of short coupons)",False),
    ("long_stub",5,"calculation period is longer than one reference period (long c oupon)",False),
    ("actual_365",5,"Actual/365 (Fixed)",False),
    ("actual_360",5,"Actual/360",False),
    ("german_controls",7,"German and English (German contro lling)",True),
    ("english_controls",7,"English and German (English contro lling)",False),
]
YESNO = [
 ("change_of_control","Early Redemption for Reasons of a Change of Control",
  "Vorzeitige Rückzahlung aufgrund eines Kontrollwechsels",True),
 ("dated_call","Early Redemption at the Option of the Issuer at Specified Call Redemption Amount(s)",
  "Vorzeitige Rückzahlung nach Wahl der Emittentin zu festgelegtem(n) Wahlrückzahlungs- betrag/-beträgen (Call)",True),
 ("make_whole_call","Early Redemption at the Option of the Issuer at Early Redemption Amount",
  "Vorzeitige Rückzahlung nach Wahl der Emittentin zum Vorzeitigen Rückzahlungsbetrag",True),
 ("interest_date_call","Early Redemption at the Option of the Issuer at Specified Call Redemption Amount",
  "Vorzeitige Rückzahlung nach Wahl der Emittentin zu festgelegtem(n) Wahlrückzahlungsbetrag/-beträgen (Call)",False),
 ("holder_put","Early Redemption at the Option of a Holder at Specified Put Redemption Amount(s)",
  "Vorzeitige Rückzahlung nach Wahl des Gläubigers zu festgelegtem(n) Wahlrückzahlungs- betrag/-beträgen (Put)",False),
]

def basf_packet():
    docs = sources(); parsed = {k:source_document(v) for k,v in docs.items()}
    ft = parsed["basf-2032-final"]
    def a(key,page,quote):
        return anchor(docs[key], parsed[key], page, quote)
    links = [
        a("basf-2032-final",2,'September 9, 2022 (the "Prospectus") and the supplement dated 27 February 2023.'),
        a("basf-2032-final",2,'der als Option I im Prospekt enthalten ist.'),
        a("basf-2032-final",3,'die weder angekreuzt noch ausgefüllt oder die gestrichen werden, gelten als in den auf die Schuldverschreibungen anwendbaren Anleihebedingungen (die "Bedingungen") gestrichen.'),
        a(BASF,1,"September 9, 2022"),
        a(BASF,108,"OPTION I – Anleihebedingungen für Schuldverschreibungen mit fester Verzinsung"),
        a(SUPPLEMENT,1,"First Supplement dated February 27, 2023 to the Debt Issuance Program Prospectus dated September 9, 2022"),
        a(SUPPLEMENT,2,"To the extent that there is any inconsistency between any statement in this First Supplement and any other statement in or incorporated by reference into the Prospectus, the statements in this First Supplement will prevail."),
        a(BASF,133,"Der deutsche Text ist bindend und maßgeblich."),
        a(BASF,133,"Die Übersetzung in die englische Sprache ist unverbindlich."),
    ]
    selections = []
    for key,page,label,expected in CHECKBOXES:
        text = norm(ft["pages"][page-1]["text"])
        selected = checked_choice(text,label)
        m.require(selected == expected,"Reviewed selection changed: "+key)
        glyph = re.search(r"[\uf078\uf06f☒☐]\s*"+re.escape(label),text).group()
        selections.append({"id":key,"selected":selected,"disposition":"SELECTED" if selected else "DELETED",
                           "basis":a("basf-2032-final",page,glyph)})
    for key,en,de,expected in YESNO:
        text = norm(ft["pages"][5]["text"])
        selected = yes_no(text,en,de)
        m.require(selected == expected,"Reviewed call/put selection changed")
        phrase = en+" "+("Yes" if selected else "No")+" "+de+" "+("Ja" if selected else "Nein")
        selections.append({"id":key,"selected":selected,"disposition":"SELECTED" if selected else "DELETED",
                           "basis":a("basf-2032-final",6,phrase)})
    core = [
        ("senior_unsecured",110,"Die Schuldverschreibungen begründen nicht besicherte und nicht nachrangige Verbindlichkeiten der Emittentin, die untereinander und mit allen anderen nicht besicherten und nicht nachrangigen Verbindlichkeiten der Emittentin gleichrangig sind, soweit diesen Verbindlichkeiten nicht durch zwingende gesetzliche Bestimmungen ein Vorrang eingeräumt wird."),
        ("icma_no_stub",112,"[die tatsächliche Anzahl von Tagen im Zinsberechnungszeitraum, geteilt durch die Actual/Actual tatsächliche Anzahl von Tagen in der jeweiligen Zinsperiode.]"),
        ("payment_delay_no_extra_interest",114,"Der Gläubiger ist nicht berechtigt, weitere Zinsen oder sonstige Zahlungen aufgrund dieser Verspätung zu verlangen."),
        ("german_law",132,"Form und Inhalt der Schuldverschreibungen sowie die Rechte und Pflichten der Gläubiger und der Emittentin bestimmen sich in jeder Hinsicht nach deutschem Recht."),
    ]
    incorporated = [
        {"title":"BASF Group audited financial statements 2020 and 2021",
         "status":"EXACT_ADMISSION_PENDING","basis":a(BASF,189,"(a) the published audited consolidated annual financial statements of BASF Group (English language version) dated December 31, 2020 and December 31, 2021, in each case including the auditor's report thereon;")},
        {"title":"BASF Finance annual 2020/2021 and interim June 2022; BASF Group interim June 2022",
         "status":"SCOPE_AND_EXACT_ADMISSION_PENDING","basis":a(BASF,189,"(c) the published unaudited interim consolidated financial statements of BASF Group as of June 30, 2022;")},
        {"title":"BASF Group 2022 financial report","status":"RETAINED_SELECTED_PAGES_PENDING",
         "retained_document":docs[ANNUAL],
         "basis":a(SUPPLEMENT,12,"the published audited consolidated annual financial statements of BASF Group (English language version) dated December 31, 2022, including the auditors' report thereon.")},
        {"title":"Historical Option I A-I terms","status":"NOT_SELECTED_AS_CURRENT_ISSUE_TERMS",
         "basis":a(BASF,8,"With respect to each type of Notes, the respective Option I A, Option I B, Option I C, Option I D, Option I E, Option I F, Option I G, Option I H and Option I I are incorporated by reference into this Prospectus for the purpose of a potential increase of Notes outstanding and originally issued prior to the date of this Prospectus."),
         "qualification":"Current final terms select Option I, series 51 tranche 1; incorporation alone does not activate the historical alternatives."}
    ]
    packet = {"schema":"basf-source-admission.v1","issue_id":"basf-senior-2032","isin":"XS2595418596",
      "status":"CORE_SOURCES_AND_BOUNDED_SELECTIONS_ADMITTED","full_dossier_status":"UNRESOLVED",
      "source_rows":{k:docs[k] for k in ("basf-2032-final",BASF,SUPPLEMENT)},
      "controlling_language":"de","translation_authority":"en_nonbinding",
      "template_pages":{"de":[108,133],"en":[65,88]},
      "template_pages_automatically_operative":False,"links":links,"selections":selections,
      "core_terms":[{"id":key,"basis":a(BASF,page,quote)} for key,page,quote in core],
      "incorporated_dependencies":incorporated,
      "remaining":["Complete suboption-to-clause mapping and independent German interpretation",
                   "Exact incorporated report admission and applicable agreements/amendment coverage",
                   "Actual event, principal, calendar and settlement facts"],
      "certified_legal_answer":None,"independent_legal_adjudication":False,"production_promotion":False}
    return packet

def load_column_document(meta, root):
    """Verify the entire derivative against its original and reviewed word geometry."""
    root = Path(root).resolve()
    def checked(name,digest):
        path = (root/name).resolve()
        m.require(path.is_relative_to(root),"Column input outside worktree")
        m.require(m.sha(path)==digest,"Column admission hash mismatch")
        return path
    base = meta["base"]
    checked(base["original"],base["sha256"])
    raw = m.read(checked(base["text"],base["text_sha256"]))
    m.require(raw["source_sha256"] == base["sha256"],"Column original mismatch")
    m.require([p["page"] for p in raw["pages"]] == list(range(1,base["pages"]+1)) and
              all(type(p["page"]) is int for p in raw["pages"]), "Original page mapping mismatch")
    spec = m.read(checked(meta["review"],meta["review_sha256"]))
    m.require(spec["independent_legal_adjudication"] is False and
              spec["review_role"] == "development_source_and_layout_review","False review authority")
    regions = m.read(checked(meta["regions"],meta["regions_sha256"]))
    prepared = {(r["document"],r["page"]):r for r in spec["source_pages"]}
    specs = {r["page"]:r for r in spec["regions"] if r["document"]==base["id"]}
    m.require(len(specs)==len(regions)==len(meta["selected_pages"]) and
              [r["page"] for r in regions]==meta["selected_pages"]==sorted(specs), "Reviewed page scope mismatch")
    expected = copy.deepcopy(raw)
    for value in regions:
        page = value["page"]; rs = specs[page]; binding = prepared[(base["id"],page)]
        m.require(type(page) is int and 1<=page<=base["pages"],"Bad derivative page")
        m.require(rs["status"]=="VISUALLY_REVIEWED" and rs["scope"]=="extraction_only" and
                  rs["languages"]==["de","en"] and binding["source_sha256"]==base["sha256"],
                  "Region lacks source review")
        for key in ("split","body_end","line_tolerance"):
            m.require(value[key]==rs[key],"Region geometry differs from review")
        checked(binding["image"],binding["image_sha256"])
        xml = checked(binding["bbox"],binding["bbox_sha256"]).read_text()
        verified = verify_region(value,xml)
        text = verified["columns"]["en"]["text"]
        for phrase in spec["required_english_phrases"][str(page)]:
            m.require(phrase in norm(text),"Reviewed qualifier missing")
        expected["pages"][page-1]["text"] = text
    derivative = m.read(checked(meta["derivative"],meta["derivative_sha256"]))
    m.require(derivative==expected,"Derivative differs from reviewed source reconstruction")
    m.require(meta["analysis_language"]=="en" and meta["complete_legal_reading"] is False,
              "Derivative legal scope overstated")
    return derivative

def frozen_reader():
    candidate = m.ROOT / OLD / "candidate"
    sys.path.insert(0,str(candidate/"src"))
    from legalmath.prospectus import loss_absorption_reader as reader
    m.require(str(candidate) in reader.__file__,"Wrong reader baseline")
    return reader

def walk_anchors(value):
    if isinstance(value,dict):
        if {"original","text_sha256","quote","start","end","page"}<=set(value):
            replay(value,m.ROOT)
        for child in value.values():walk_anchors(child)
    elif isinstance(value,list):
        for child in value:walk_anchors(child)

def run(folder):
    rev = review()
    packet = basf_packet(); walk_anchors(packet)
    m.write(folder/"basf-admission.json",packet)
    docs = sources(); row=docs["deutsche-at1-2025"]
    raw = source_document(row); revised=copy.deepcopy(raw)
    prepared={(r["document"],r["page"]):r for r in rev["source_pages"]}
    regions=[]
    for spec in rev["regions"]:
        item=prepared[(spec["document"],spec["page"])]
        result=region_extract((m.ROOT/item["bbox"]).read_text(),page_number=spec["page"],
                             split=spec["split"],body_end=spec["body_end"],
                             line_tolerance=spec["line_tolerance"])
        for phrase in rev["required_english_phrases"][str(spec["page"])]:
            m.require(phrase in norm(result["columns"]["en"]["text"]),"Missing qualifier: "+phrase)
        revised["pages"][spec["page"]-1]["text"]=result["columns"]["en"]["text"]
        regions.append(result)
    m.write(folder/"regions.json",regions)
    m.write(folder/"english-pages.json",revised)
    meta={"schema":"reviewed-column-document.v1","base":row,"regions":m.relative(folder/"regions.json"),
          "regions_sha256":m.sha(folder/"regions.json"),"derivative":m.relative(folder/"english-pages.json"),
          "derivative_sha256":m.sha(folder/"english-pages.json"),"review":m.relative(m.OUT/"source-review.json"),
          "review_sha256":m.sha(m.OUT/"source-review.json"),"selected_pages":[36,37,38],
          "analysis_language":"en","complete_legal_reading":False}
    admitted=load_column_document(meta,m.ROOT)
    m.write(folder/"column-admission.json",meta)
    reader=frozen_reader()
    selection={"id":row["id"],"operative_pages":[[36,38]],
               "scope_basis":"Fixed page-matched development comparison; incomplete issue scope"}
    issue={"id":"deutsche-at1-2025","security_type":"debt"}
    before=reader.analyze_document(row,raw,selection,issue)
    after=reader.analyze_document(row,admitted,selection,issue)
    before=[e for e in before if 36<=e["page"]<=38]
    after=[e for e in after if 36<=e["page"]<=38]
    m.require(all(reader.quote_valid(e,raw) for e in before),"Original evidence quote invalid")
    m.require(all(reader.quote_valid(e,admitted) for e in after),"Column evidence quote invalid")
    m.write(folder/"reader-before.json",before);m.write(folder/"reader-after.json",after)
    en=norm(regions[1]["columns"]["en"]["text"])
    start=en.index("(7) Note on the possibility")
    end=en.index("§ 3 Interest",start)
    quote=en[start:end].strip()
    m.require("or other instruments of ownership qualifying as Common Equity Tier 1 instruments" in quote,
              "Conversion qualifier lost")
    passage={"page":37,"language":"en","start":start,"end":end,"quote":quote,
             "column_binding":m.relative(folder/"regions.json"),"column_sha256":m.sha(folder/"regions.json"),
             "development_interpretation":"Statutory authority may write down principal to zero and convert to issuer/group/bridge-bank ordinary shares OR other CET1 ownership instruments. This does not establish a common-share-only conversion.",
             "independent_adjudication":False,"certified_legal_answer":None}
    m.write(folder/"reviewed-passage.json",passage)
    inventory=m.read(m.ROOT/S1)
    old_issue=next(i for i in inventory["issues"] if i["id"]=="basf-senior-2032")
    original_result=reader.analyze_issue(old_issue,inventory["documents"],m.ROOT)
    m.write(folder/"basf-frozen-reader.json",original_result)
    revised_issue=copy.deepcopy(old_issue)
    revised_issue["unresolved_operative_dependencies"]=packet["remaining"]
    revised_issue["dependency_boundary"]="Correct 2022 base and February 2023 supplement admitted in bounded source packet; full dossier still unresolved."
    revised_issue["source_admission"]=m.relative(folder/"basf-admission.json")
    m.write(folder/"basf-successor-issue.json",revised_issue)
    gapmap=[
       {"gap":"BASF G12","status":"PARTLY_CLOSED","closed":"Exact required base/supplement identity and bounded German Option I selections",
        "next_action":"Complete clause-level German suboption mapping, financial-report admission and applicable agreement coverage","dependency":"Source/German review","command":"python3 -m scripts.prospectus_refresh status"},
       {"gap":"Deutsche bilingual extraction","status":"THREE_PAGES_REPAIRED","closed":"Lossless language separation on PDF36-38 and validated optional loader",
        "next_action":"Qualify remaining operative bilingual pages individually, then repair unresolved actor/alternative constructions","dependency":"New page reviews and source-bound semantic tests"},
       {"gap":"Original 1467 records / 1307 spans","status":"UNADJUDICATED","next_action":"Independent clause review; retain this development repair separately","dependency":"Qualified adjudicator"},
       {"gap":"Enel/Unilever/Lloyds/SEB/LVMH/BBVA packages","status":"OPEN","next_action":"Execute retained G13-G17 source work orders","dependency":"Executed agreements, amendments and authenticated filings"},
       {"gap":"BES incorporation and precedence","status":"OPEN","next_action":"Work through 29 dependency records and duplicate 1.17 conflict","dependency":"Exact reports/conditions and precedence decisions"},
       {"gap":"Jurisdiction primary sources","status":"OPEN","next_action":"New exact routes for Portuguese Annex2B, HETA, Dana, Lloyds, Ukraine, Popular/Snoras and historical Italian law","dependency":"Primary sources; 24 HTTP requests remain"},
       {"gap":"Regulatory and financial inputs","status":"OPEN","next_action":"Admit applicable dated rules, actual issuer/event/client/bank facts and settlement calendars","dependency":"Actual facts and rule editions"},
       {"gap":"Independent/unseen validation and intended use","status":"OPEN","next_action":"Assign existing 25 forms, independently freeze unexposed cohort, evaluate frozen candidate","dependency":"Qualified external reviewers and cohort curator"}
    ]
    m.write(folder/"remaining-gaps.json",gapmap)
    def counts(evs):
        return {"records":len(evs),"unresolved":sum(e["disposition"].startswith("unresolved") for e in evs)}
    summary={"status":"PASS","basf_selected_options":len(packet["selections"]),
             "basf_full_dossier":"UNRESOLVED","column_pages":[36,37,38],
             "words_preserved":sum(len(r["words"]) for r in regions),
             "reader_before":counts(before),"reader_after":counts(after),
             "count_role":"explanatory only; no accuracy claim",
             "independent_adjudications":0,"production_promotion":False,"new_http_requests":0}
    m.write(folder/"admission-summary.json",summary)
    print(json.dumps(summary,indent=2))
