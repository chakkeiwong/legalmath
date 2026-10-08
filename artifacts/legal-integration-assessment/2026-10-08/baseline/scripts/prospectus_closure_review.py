"""Apply explicit image-checked corrections; raw OCR is retained unchanged."""
import json
from pathlib import Path
from scripts import run_prospectus_closure_next as m
from scripts.prospectus_reviewed_extraction import norm,text_hash,load
def run():
    corrections={
        "jur-more-bes-1315263":{
            1:[("www.bourse.!u","www.bourse.lu"),("Banco Espirito Santo, $.A.","Banco Espirito Santo, S.A."),
               ("Banco Espirito Santo, 8.A.","Banco Espirito Santo, S.A.")],
            2:[("Calculation Ameunt","Calculation Amount")],
            3:[("Banco Espfrito Santo","Banco Espírito Santo"),("USS. Selling","U.S. Selling")],
            4:[("responsibilityaforthe information contained inthese FinalC)","responsibility for the information contained in these Final Terms.")],
            5:[("Espaiia","España"),("Espafia","España")],
            6:[("PTBEQBOMO0010","PTBEQBOM0010"),
               ("EuroclearAny clearing system(s) other than Interbolsa-Sociedade Gestora de Sistemas de Liquidacdoe Bank S.A/ N.V. and de Sistemas Centralizados de Valores Mobilidrios, S.A. Clearstream Banking, societe anonyme (\"Interbolsa\") and the relevant identification | number(s):",
                "Any clearing system(s) other than Euroclear Bank S.A./ N.V. and Clearstream Banking, societe anonyme and the relevant identification number(s): Interbolsa-Sociedade Gestora de Sistemas de Liquidação e de Sistemas Centralizados de Valores Mobiliários, S.A. (\"Interbolsa\")"),
               ("oruponall satisfactiontimes duringoftheirthe Eurosystemlife. Such recognitioneligibility criteria.will depend",
                "or all times during their life. Such recognition will depend upon satisfaction of the Eurosystem eligibility criteria.")]},
        "jur-more-bes-1922255":{
            1:[("ESPiRITO","ESPÍRITO")],
            2:[("2\\st January","21st January"),("Actual/Actual CMA)","Actual/Actual (ICMA)")],
            3:[("USS. Selling","U.S. Selling")],
            4:[("Espafia","España")],
            5:[("BancaIMIS.p.A.","Banca IMI S.p.A."),("J.P. Morgan Securities ple","J.P. Morgan Securities plc")]},
        "jur-bes-2014-ptbeqkom0019":{
            1:[("ESPiIRITO","ESPÍRITO")],
            4:[("Espajfia","España")],
            5:[("HSBC Bank ple","HSBC Bank plc"),("J.P. Morgan Securities ple","J.P. Morgan Securities plc")]},
        "jur-more-bes-1217215":{}}
    blank={"jur-more-bes-1922255":[6],"jur-more-bes-1217215":[287]}
    fields={
        "jur-more-bes-1315263":{"issuer":"Banco Espirito Santo, S.A.","series":"23","isin":"PTBEQBOM0010","terms_date":"2011-07-14","issue_date":"2011-07-15","maturity":"2016-07-15","coupon_percent":"6.875","currency":"EUR","denomination":"100000","governing_law":"Portuguese Law"},
        "jur-more-bes-1922255":{"issuer":"Banco Espírito Santo, S.A.","series":"35","isin":"PTBENKOM0012","terms_date":"2014-01-20","issue_date":"2014-01-21","maturity":"2019-01-21","coupon_percent":"4.00","currency":"EUR","denomination":"100000"},
        "jur-bes-2014-ptbeqkom0019":{"issuer":"Banco Espírito Santo, S.A.","series":"36","isin":"PTBEQKOM0019","terms_date":"2014-05-06","issue_date":"2014-05-08","maturity":"2017-05-08","coupon_percent":"2.625","currency":"EUR","denomination":"100000"}}
    allmeta={};total=0
    for key,changes in corrections.items():
        folder=m.DATA/"derivatives"/key;raw_path=folder/"pages.json";raw=m.read(raw_path)
        reviewed=[];rows=[];blanks=blank.get(key,[])
        for page in raw["pages"]:
            n=page["page"];text=page["text"]
            if n in raw["rendered_pages"]:
                edits=[{"old":a,"new":b,"reason":"Compared against the original page image; character or row-order repair."} for a,b in changes.get(n,[])]
                text=norm(text)
                for edit in edits:
                    assert text.count(edit["old"])==1,(key,n,edit["old"])
                    text=text.replace(edit["old"],edit["new"],1)
                total+=len(edits)
                reviewed.append({"page":n,"status":"VISUALLY_CHECKED","blank":n in blanks,
                    "raw_text_sha256":text_hash(page["text"]),
                    "image_sha256":page["image_sha256"],"review_image_sha256":page["review_image_sha256"],
                    "corrections":edits,
                    "scope":"Material printed terms, identifiers, dates, repayment, applicable/Not Applicable entries, cross-references and eligibility qualifications. Handwritten signatures are not authenticated or transcribed as proof of authority."})
            rows.append({"page":n,"text":text})
        review={"source_sha256":raw["source_sha256"],"raw_sha256":m.sha(raw_path),
            "reviewer_type":"agent_visual_review","legal_adjudication":"PENDING","human_acceptance":"PENDING",
            "pages":reviewed,"checked_fields":fields.get(key,{}),
            "limitations":"Visual checks support the recorded printed terms and corrections; this is not independently adjudicated legal completeness."}
        review_path=folder/"review.json";m.write(review_path,review)
        doc={"source_sha256":raw["source_sha256"],"pages":rows,"reviewed_blank_pages":blanks,
            "blank_page_reviews":{str(n):{"reviewed_image_sha256":raw["pages"][n-1]["image_sha256"],
                                         "basis":"Original page visually inspected and blank"} for n in blanks},
            "automatic_ocr_performed":bool(raw["ocr_pages"]),"review_scope":"agent_visual_review"}
        text_path=folder/"reviewed-pages.json";m.write(text_path,doc)
        meta={"id":key,"original":raw["source"],"sha256":raw["source_sha256"],"pages":len(rows),
              "raw":str(raw_path.relative_to(m.ROOT)),"raw_sha256":m.sha(raw_path),
              "review":str(review_path.relative_to(m.ROOT)),"review_sha256":m.sha(review_path),
              "text":str(text_path.relative_to(m.ROOT)),"text_sha256":m.sha(text_path),
              "language_model":str((m.DATA/"tools/eng.traineddata").relative_to(m.ROOT))}
        assert load(meta,m.ROOT)==doc
        allmeta[key]=meta
    m.write(m.DATA/"reviewed-extractions.json",allmeta)
    result={"status":"PASS","documents":len(allmeta),"visually_inspected_pages":18,
            "ocr_pages":17,"blank_pages":blank,"corrections":total,"independent_adjudication":False}
    m.write(m.OUT/"ocr-review-result.json",result);print(json.dumps(result,indent=2))
