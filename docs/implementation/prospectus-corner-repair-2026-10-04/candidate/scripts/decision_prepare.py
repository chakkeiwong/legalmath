"""Freeze the complete retained inputs before new source checks."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from legalmath.canonical import raw_digest
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.controls import check_controls

DOC=ROOT/'docs/implementation/interpretation-round13'
OLD=ROOT/'artifacts/interpretation/round12/P4/attempt-04/live'

def load_case(cid):
    root=OLD/cid
    report=json.loads((root/'report.json').read_text())
    old=Path(report['interpretation']['directory'])
    directory=root/old.relative_to(old.parents[2])
    return {name:json.loads((directory/(name+'.json')).read_text()) for name in ('packet','claims','candidates')},directory

def quote(packet, phrase):
    found=[{'unit_id':u['unit_id'],'quote':phrase} for u in packet['units'] if u['text'].count(phrase)==1]
    if len(found)!=1: raise ValueError((phrase,len(found)))
    return found

def controls(cid,packet):
    if cid=='26ec2':
        items=[
          ('submission.compliance','Does one submission satisfy the selected channel, method and e-Cert control?','one submission','COMPLIANT',
           'the selected submission satisfies that control','the selected submission fails that control','Licensed firms are required to submit STRs to the JFIU via STREAMS 2'),
          ('ecert.applicability','Is an e-Cert required for this submission method?','one method','REQUIREMENT_APPLIES',
           'the e-Cert condition applies','the e-Cert condition does not apply','Hongkong Post e-Cert (electronic certificate) is required for this submission.'),
          ('resubmission.event','Does the original submission event trigger a duty to resubmit?','one original submission event','DUTY_TRIGGER',
           'the original event triggers resubmission','the original event does not trigger resubmission','licensed firms are required to re-submit the STRs via STREAMS 2.'),
          ('resubmission.history','Does this report have at least one event triggering resubmission?','one report with history','DUTY_TRIGGER',
           'a triggering event exists in the report history','no triggering event exists in a complete report history','For STRs submitted to the JFIU via channels other than STREAMS 2 following its implementation'),
          ('urgent.contact','Is urgent JFIU contact called for during blackout?','one urgent report during blackout','DUTY_TRIGGER',
           'urgent contact is called for','urgent contact is not called for','for any STRs requiring urgent submission during the blackout period of STREAMS'),
          ('xml.transition','Have the XML schema and technical-test transition requirements been fulfilled?','one firm and XML transition','COMPLIANT',
           'the selected transition requirements are fulfilled','the selected transition requirements are not fulfilled','required to follow the XML schema provided separately by the JFIU')]
    else:
        items=[
          ('gift.component','Is this particular benefit component caught by the gift restriction?','one benefit component','PROHIBITED','the component is caught','the component is not caught','other than a discount of fees or charges'),
          ('gift.offer','Does the assessed offer contain a component caught by the gift restriction?','one offer comprising components','PROHIBITED','the offer contains a caught component','the offer contains no caught component','other than a discount of fees or charges'),
          ('gift.compliance','Does this benefit satisfy the selected gift control?','one benefit component','COMPLIANT','the benefit satisfies this control','the benefit fails this control','other than a discount of fees or charges'),
          ('structured.classification','Does the arrangement satisfy the structured-product classification?','one arrangement','CLASSIFICATION','classification satisfied','classification not satisfied','structured products'),
          ('public.invitation','Is this public invitation caught by the stated section 103 offence?','one public invitation','PROHIBITED','caught by the offence','not caught by the offence','section 103 of the SFO'),
          ('advertising.control','Does this advertisement satisfy the separate marketing restrictions?','one advertisement','COMPLIANT','marketing control satisfied','marketing control not satisfied','misleading or deceptive information')]
    result=[]
    for ident,question,unit,kind,yes,no,phrase in items:
        # Repeated short phrases are anchored to the first substantive occurrence
        # with its entire retained unit; no invented quotation is permitted.
        found=[u for u in packet['units'] if phrase.lower() in u['text'].lower()]
        if not found: raise ValueError((cid,phrase))
        u=found[0]
        result.append({'control_id':ident,'question':question,'unit_of_assessment':unit,
            'actor':'licensed firms as defined in circular' if cid=='26ec2' else 'distributors/intermediaries in source scope',
            'temporal_basis':'stated source interval; competing date/time interpretations retained',
            'result_kind':kind,'true_means':yes,'false_means':no,
            'source_evidence':[{'unit_id':u['unit_id'],'quote':u['text']}]})
    return check_controls(result,packet)

def main():
    ledger={}
    for cid in ('26ec2','23ec46','25ec71','24ec50'):
        data,d=load_case(cid)
        if cid in ('26ec2','23ec46'):data['controls']=controls(cid,data['packet'])
        data['origin']={str((d/(name+'.json')).relative_to(ROOT)):raw_digest((d/(name+'.json')).read_bytes())
                        for name in ('packet','claims','candidates')}
        path=DOC/'inputs'/(cid+'.json');save(path,data);ledger[cid]=raw_digest(path.read_bytes())
    save(DOC/'inputs-lock.json',ledger)
    print('Frozen complete source packets, inventories and candidates',ledger.keys())
if __name__=='__main__':main()
