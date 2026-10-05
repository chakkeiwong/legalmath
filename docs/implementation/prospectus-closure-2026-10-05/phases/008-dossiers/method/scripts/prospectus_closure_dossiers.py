"""Source-bound BES incorporation and precedence review, without legal promotion."""
import json,re
from collections import Counter
from scripts import run_prospectus_closure_next as m
from scripts.prospectus_reviewed_extraction import norm,load

def source_rows():
    old=m.read(m.ROOT/"docs/implementation/prospectus-corner-repair-2026-10-04/phases/016-intake/bes-bundles.json")
    return old
def anchor(key,fragment):
    meta=source_rows()["documents"][key]
    path=m.ROOT/meta["original"]
    if m.sha(path)!=meta["sha256"]:raise ValueError("Original changed: "+key)
    pagepath=path.with_name("pages.json")
    doc=m.read(pagepath)
    matches=[]
    for page in doc["pages"]:
        text=norm(page["text"]);needle=norm(fragment)
        if needle in text:
            start=text.index(needle)
            matches.append({"document":key,"original":meta["original"],"source_sha256":meta["sha256"],
                "text":str(pagepath.relative_to(m.ROOT)),"text_sha256":m.sha(pagepath),
                "page":page["page"],"start":start,"end":start+len(needle),"quote":needle})
    if len(matches)!=1:raise ValueError(f"Anchor must match exactly once: {key}: {fragment}: {len(matches)}")
    return matches[0]

def run():
    old=source_rows();dependencies=[]
    def add(code,title,scope,fragment,local=None):
        key="jur-more-bes-"+code
        row={"id":f"BES-DEP-{len(dependencies)+1:02d}","introduced_by":key,"title":title,
             "incorporated_scope":scope,"anchor":anchor(key,fragment),
             "status":"RETAINED_SCOPE_REVIEW_PENDING" if local else "NOT_LOCATED_IN_RETAINED_CORPUS",
             "local_source":local,"independent_adjudication":None}
        dependencies.append(row)
    # 2010 base, printed pages 37–38.
    for title,scope,fragment in [
        ("BES 9M 2010 results, release 2010-11-02","Balance sheet p37; income statement p38","The press release of the Bank dated 2nd November, 2010"),
        ("BES Finance H1 2010 statements","Income p2; balance p4; equity p5; cash flow p6; notes pp7–35","The unaudited interim financial statements of BES Finance for the six months ended 30th June, 2010"),
        ("BES Finance 2009 audited statements","Income p2; balance p4; cash flow p6; policies/notes pp7–54; auditor pp55–56","The auditors’ report and audited annual financial statements of BES Finance for the financial year ended 31st December, 2009"),
        ("BES Finance 2008 audited statements","Income p3; balance p2; cash flow p5; policies/notes pp6–40; auditor p1","The auditors’ report and audited annual financial statements of BES Finance for the financial year ended 31st December, 2008"),
        ("BES H1 2010 consolidated/nonconsolidated statements","Selected statements pp51–60; policies/notes pp61–171; auditor pp172–173","The unaudited consolidated and non-consolidated interim financial statements of the Bank for the six months ended 30th June, 2010"),
        ("BES 2009 consolidated/nonconsolidated statements","Selected statements pp66–78; policies/notes pp74–170; auditor pp173–174","The auditors’ report and audited consolidated and non-consolidated annual financial statements of the Bank for the financial year ended 31st December, 2009"),
        ("BES 2008 consolidated/nonconsolidated statements","Selected statements pp69–74,165–170; policies/notes pp75–163,171–241; auditor pp245–248","Bank for the financial year ended 31st December, 2008")]:
        add("1217215",title,scope,fragment)
    for code,title,scope,fragment in [
        ("1272291","BES unaudited 2010 release, 2011-01-31","Balance p41; income p42","On 31 January 2011 the Bank issued a press release"),
        ("1286398","BES audited 2010 accounts","Balance p94; income p92; cash flow p96; policies/notes pp97–187; auditor pp190–191","the Bank's auditors' report and audited consolidated annual financial statements"),
        ("1286398","BES Finance audited 2010 accounts","Balance p4; income p2; cash flow p6; policies/notes pp7–50; auditor pp51–52","2.2 Auditor’s report and audited annual financial statements of BES Finance"),
        ("1286398","BES Q1 2011 release, 2011-05-02","Balance p36; income p37","On 2 May, 2011 the Bank issued a press release")]:
        add(code,title,scope,fragment)
    # 2013 base imports only the named historical conditions, not every old prospectus page.
    dates=["7th December 2005","23rd February 2007","18th January 2008","18th February 2009",
           "18th December 2009","3rd November 2010","4th November 2011","29th May 2012"]
    common="the section entitled “Terms and Conditions of the Notes (other than Undated Deeply Subordinated Notes)”"
    for date in dates:
        add("1774077","BES prior base "+date,common,common,
            "jur-more-bes-1217215" if date=="3rd November 2010" else None)
    for title,scope,fragment in [
        ("BES Q1 2013 release, 2013-05-07","Balance p39; income p40","The press release of the Bank dated 7th May, 2013"),
        ("BES audited 2012 accounts","Income pp100–101; balance p102; equity p103; cash p104; notes pp110–212; auditor pp213–215","Bank for the financial year ended 31st December, 2012"),
        ("BES audited 2011 accounts","Income pp100–101,127–128; balance pp102,129–130; equity p103; cash p104; notes pp105–199; auditor pp200–202","Bank for the financial year ended 31st December, 2011"),
        ("BES Finance audited 2012 accounts","Income pp2–3; balance p4; equity p5; cash p6; notes pp7–44; auditor pp45–46","The auditors’ report and audited annual financial statements of BES Finance for the financial year ended 31st December, 2012"),
        ("BES Finance audited 2011 accounts","Income pp2–3; balance p4; equity p5; cash p6; notes pp7–44; auditor pp45–46","The auditors’ report and audited annual financial statements of BES Finance for the financial year ended 31st December, 2011")]:
        add("1774077",title,scope,fragment)
    for code,title,scope,fragment in [
        ("1774113","BES H1 2013 release, 2013-07-26","Balance p38; income p39","On 26 July 2013 the Bank issued a press release"),
        ("1843910","BES 9M 2013 release, 2013-10-25","Balance p41; income p42","On 25 October 2013, the Bank issued a press release"),
        ("1949460","BES unaudited 2013 release, 2014-02-13","Balance p46; income p47","The press release of the Bank dated 13th February, 2014"),
        ("2001058","BES 2013 I. Management Report","Income pp180,182; balance pp179,181; meeting approval still pending as at supplement date","The management report, the auditors’ report and audited consolidated and non-"),
        ("2001058","BES 2013 II. Financial Statements and Notes","Income p3; balance p5; equity p6; cash p7; policies/notes pp8–179; auditor pp180–182; meeting approval pending","The management report, the auditors’ report and audited consolidated and non-")]:
        add(code,title,scope,fragment)
    precedence=[]
    for code in ("1217215","1774077"):
        precedence.append({"source":code,"rule":"Modification or supersession only to the extent applicable; no blanket replacement",
            "anchor":anchor("jur-more-bes-"+code,"Any statement so modified or superseded shall not, except as so modified or superseded, constitute a part of this Prospectus.")})
    for code in ("1221003","1272291","1260978","1286398","1297141","1347380","1774113","1843910"):
        precedence.append({"source":code,"rule":"Supplement prevails only to the extent of an inconsistency",
            "anchor":anchor("jur-more-bes-"+code,"the statements in (a) above will prevail.")})
    replacements=[
        {"source":"1949460","target":"Taxation in Portugal","action":"Entire section replacement",
         "anchor":anchor("jur-more-bes-1949460","the wording under the heading “Taxation in Portugal” will be entirely replaced")},
        {"source":"1949460","target":"Tax forms beginning printed p212","action":"Delete obsolete forms",
         "anchor":anchor("jur-more-bes-1949460","are therefore deleted in their entirety.")},
        {"source":"2001058","target":"Summary B12","action":"Express replacement",
         "anchor":anchor("jur-more-bes-2001058","item B12 will be deleted and replaced by the following wording:")},
        {"source":"2001058","target":"General Information: Significant or Material Change","action":"Express replacement",
         "anchor":anchor("jur-more-bes-2001058","the paragraphs under the heading “Significant or Material Change” shall be deleted and replaced")}]
    conflict={"status":"UNRESOLVED_SECTION_NUMBER_COLLISION",
        "description":"November 2013 renumbers the FTT risk to 1.17; April 2014 inserts KPMG risk as 1.17 after 1.16. Do not overwrite by numeric key.",
        "anchors":[anchor("jur-more-bes-1843910","shall be renumbered sections 1.16"),
                   anchor("jur-more-bes-2001058","1.17 2013 KPMG AUDIT REPORT")]}
    local=[]
    for path in sorted((m.ROOT/"docs/prospectus").rglob("pages.json")):
        try:
            value=m.read(path);pages=value.get("pages",[]) if isinstance(value,dict) else []
            first=" ".join(norm(p.get("text","")) for p in pages[:3])
        except (ValueError,TypeError,AttributeError):continue
        if re.search(r"Banco Esp.r[ií]to Santo|BES Finance",first,re.I):
            local.append({"path":str(path.relative_to(m.ROOT)),"sha256":m.sha(path),"opening_text":first[:280]})
    issues=[]
    for row in old["issues"]:
        issue=row["issue"];ids={x["id"] for x in issue["documents"]}
        deps=[d["id"] for d in dependencies if d["introduced_by"] in ids]
        issues.append({"id":issue["id"],"issue_date":issue["issue_date"],"terms_date":issue["terms_date"],
            "required_retained_documents":sorted(ids),"incorporated_dependencies":deps,
            "binding_status":"UNRESOLVED","precedence_rule_review":"SOURCE_REVIEWED",
            "full_conflict_resolution":"PENDING","independent_adjudication":None})
    result={"retained_bes_documents":len(old["documents"]),"dependencies":dependencies,"precedence_rules":precedence,
        "express_amendments":replacements,"conflicts":[conflict],"issues":issues,
        "local_match_candidates":local,"local_match_limit":"Opening-page identity search; source mentions do not admit a report. Missing status means no exact admitted match.",
        "historical_conditions_scope":"Incorporation does not make every historical edition operative for Series 35 or 36. Issue-specific application remains to be reviewed.",
        "network":{"prior":187,"new_ocr_model_requests":1,"total":188,"limit":212,"remaining":24,
            "further_acquisitions":"No specific new document route found in retained links; previous failed search/decree endpoints not retried."},
        "original_cohort_remaining":m.read(m.ROOT/"docs/implementation/prospectus-evidence-closure/phases/S2/attempt-017/result.json")["remaining"]}
    m.write(m.OUT/"dossier-review.json",result)
    lines=["# BES dependency and precedence review","","All 15 listed bases, supplements and final terms are retained. The table records further incorporated reports and historical conditions; it does not infer that every programme document governs every issue.","",
        "| Dependency | Introduced by | Required scope | Current evidence |","| --- | --- | --- | --- |"]
    for d in dependencies:
        lines.append("| "+d["title"]+" | "+d["introduced_by"]+" p"+str(d["anchor"]["page"])+" | "+d["incorporated_scope"]+" | "+d["status"]+" |")
    lines += ["","The source states that later statements modify earlier ones only to the extent applicable or inconsistent. The February 2014 tax section and forms have express replacement/deletion instructions. The April 2014 accounts remained subject to the scheduled shareholder approval as at that supplement; later approval must be evidenced separately.","",
        conflict["description"],"","All three issue dossiers remain unresolved. Exact missing reports, selected historical conditions, operative agreements and conflict resolution must be admitted before a complete-dossier claim.","",
        "Original-cohort packages still require:"]+["- "+x for x in result["original_cohort_remaining"]]
    (m.OUT/"DOSSIER-REVIEW.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"status":"PASS","retained_documents":15,"incorporated_dependencies":len(dependencies),
        "local_candidates":len(local),"precedence_rules":len(precedence),"express_amendments":len(replacements),
        "conflicts":1,"complete_dossiers":0,"requests_remaining":24},indent=2))
