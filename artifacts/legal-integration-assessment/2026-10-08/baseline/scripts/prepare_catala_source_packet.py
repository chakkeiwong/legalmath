#!/usr/bin/env python3
"""Freeze dated retained-source tasks, references and concrete disputed readings."""
from itertools import product
from pathlib import Path
from legalmath.canonical import raw_digest, canonical, digest, loads
from legalmath.sources.anchors import make_span
from tests.catala.native.reference import task, f
from legalmath.catala.native.boundary import make_snapshot
from legalmath.catala.native.source_review import validate_packet

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/catala/gap-closure/source-review'


def corpus():
    specs=[
      ('netassets','23EC35-annex1','pdf','3.3 “Net assets”','\n3.4',
       [f('assets','money','Correctly classified total assets in HKD','HKD cents'),f('liabilities','money','Correctly classified total liabilities in HKD','HKD cents'),f('residence','money','Value of primary residence already included in assets','HKD cents')], 'money',
       'Compute only net assets excluding primary residence from paragraph 3.3. Input classification, account ownership and conversion to HKD are supplied; do not infer SPI eligibility. Signed input amounts are admitted for arithmetic stress tests.',
       'Deduct total liabilities and the primary residence from total assets.',
       'Deduct the primary residence twice when interpreting net assets excluding residence.',
       {'assets':'10000','liabilities':'3000','residence':'2000'},'5000','3000','REJECT_AS_SOURCE_UNSUPPORTED_MUTATION'),
      ('gifts','23EC46','json','Paragraph 3.11 of the Code of Conduct provides','\nIn light of the concerns',
       [f('gift','boolean','The offered item is classified as a gift, without deciding the exception'),f('discount','boolean','The offered item is a discount of fees or charges'),f('specific','boolean','The promotion is linked to a specific investment product'),f('producttype','boolean','The promotion is linked to a particular type of investment product')], 'boolean',
       'For a distributor promoting products to a client, compute whether the quoted paragraph 3.11 gift prohibition applies. The four supplied classifications are evidence inputs. This is only the quoted gift control; section 103 and the rest of the Code are outside the selected question.',
       'The discount exception applies on both the specific-product and product-type routes.',
       'The parenthetical discount exception attaches only to the specific-product route.',
       {'gift':True,'discount':True,'specific':False,'producttype':True},False,True,'PROVISIONAL_REJECT_RIVAL_PENDING_REVIEW'),
      ('network','26EC22','json','Product Providers should not use public-permissionless','\nProduct Providers should confirm',
       [f('publicnetwork','boolean','The proposed network is public-permissionless'),f('controls','boolean','Additional controls have been applied'),f('proper','boolean','The additional controls are professionally assessed as proper')], 'boolean',
       'For a Product Provider within the circular scope, compute whether the selected sentence prohibits the proposed network use. The controls and proper-input classifications are supplied by reviewers. Do not turn this one control into overall product approval or resolve other referenced requirements.',
       'Public-permissionless use fails the selected control unless controls are both additional and proper.',
       'Any additional control suffices irrespective of whether it is proper.',
       {'publicnetwork':True,'controls':True,'proper':False},True,False,'REJECT_AS_OMITTED_QUALIFIER'),
      ('consultation','26EC22','json','For new investment products that have tokenisation','\nGiven the rapidly evolving',
       [f('newproduct','boolean','The product is new and has tokenisation features'),f('seeksauthorisation','boolean','SFC authorisation is planned'),f('existingtokenisation','boolean','This proposal tokenises an existing SFC-authorised investment product'),f('materialchange','boolean','The proposal makes a material change to an existing tokenised product arrangement')], 'boolean',
       'Compute whether prior consultation is required under the two selected sentences. Classification of a material change is supplied. Do not equate consultation with prior approval: the source separately says such changes may require approval.',
       'Consultation applies to a new tokenised product seeking authorisation, tokenisation of an existing authorised product, or a material arrangement change.',
       'For existing authorised products, tokenisation and material change must both occur before consultation is required.',
       {'newproduct':False,'seeksauthorisation':False,'existingtokenisation':False,'materialchange':True},True,False,'PROVISIONAL_REJECT_CONJUNCTION_PENDING_REVIEW')]
    frozen=[];blobs={}
    for name,source,ext,start_text,end_text,inputs,typ,question,reading,rival,witness,value,alternative,disposition in specs:
        raw=(ROOT/'.localresources/sfc'/f'{source}.{ext}').read_bytes()
        text=(ROOT/'.localresources/sfc'/f'{source}.txt').read_text()
        start=text.index(start_text);end=text.index(end_text,start);quote=text[start:end]
        span=make_span('span.'+name,source,raw,text,start,end)
        t=task('closure.'+name,'Control',quote,inputs,[f('result',typ,question,'HKD cents' if typ=='money' else 'truth value')])
        t.update(native_profile='legalmath.catala.native.v2',question=question+' Dated retained edition; assessment timestamps are a synthetic test setting.')
        t['packet'].update(source_key='sfc.'+source.lower()+'.'+name,authority='RETAINED_SOURCE',family_ids=['sfc.'+source.split('-')[0].lower()])
        t['packet']['units'][0].update(locator=source+' selected control',span=span)
        if name=='netassets': rows=[{'assets':str(a),'liabilities':str(b),'residence':str(c)} for a,b,c in [(0,0,0),(10000,3000,2000),(100,200,10),(10**25,1,2)]]
        else: rows=[dict(zip([f['name'] for f in inputs],v)) for v in product((False,True),repeat=len(inputs))]
        def reference(v):
            if name=='netassets':return str(int(v['assets'])-int(v['liabilities'])-int(v['residence']))
            if name=='gifts':return v['gift'] and not v['discount'] and (v['specific'] or v['producttype'])
            if name=='network':return v['publicnetwork'] and not (v['controls'] and v['proper'])
            return (v['newproduct'] and v['seeksauthorisation']) or v['existingtokenisation'] or v['materialchange']
        cases=[{'id':name+'.'+str(i),'snapshot':make_snapshot(t,v),'expected':{'status':'VALUE','value':{'result':reference(v)}}} for i,v in enumerate(rows)]
        assert reference(witness)==value
        frozen.append({'task':t,'cases':cases,'reference_author':'Executing Codex; separate reference code, not independent legal adjudication',
             'source_family':raw_digest(raw),'lineage_family':t['packet']['family_ids'][0],
             'selected_reading':reading,'rival':rival,'rival_disposition':disposition,
             'witness':{'inputs':witness,'selected':value,'rival':alternative},
             'scope_qualifications':question,'adjudication':{'status':'PENDING_HUMAN','reviewer':None}})
        blobs[raw_digest(raw)]=raw;blobs[raw_digest(text.encode())]=text.encode()
    return frozen,blobs


def main():
    rows,blobs=corpus()
    packet={'record_type':'CatalaSourceReviewPacket','corpus':rows,'source_hashes':sorted(blobs),
            'sampling':'Development convenience sample: 4 tasks, 3 circular families; 26EC22 supersedes 23EC53; all retained editions have prior project exposure.',
            'heldout_eligible':False}
    report=validate_packet(packet,list(blobs.values()))
    OUT.mkdir(parents=True,exist_ok=False)
    (OUT/'packet.json').write_bytes(canonical(packet));(OUT/'validation.json').write_bytes(canonical(report))
    sources=OUT/'sources';sources.mkdir()
    for h,data in blobs.items():(sources/(h+'.bin')).write_bytes(data)
    lines=['# Independent legal review packet','',packet['sampling'],'',
           'Review each quoted provision against the retained edition, assess the supplied factual classifications, and accept, revise or reject the selected reading and rival. All decisions below are provisional. Record your identity, source review, reasons and concrete distinguishing values in an adjudication record.','']
    for row in rows:
        t=row['task'];lines+=['## '+t['task_id'],'',t['question'],'',t['packet']['selected_slice'],'',
          '**Proposed reading:** '+row['selected_reading'],'','**Rival to assess:** '+row['rival'],
          '','**Current provisional disposition:** '+row['rival_disposition'],'',
          'Distinguishing input and outcomes: `'+canonical(row['witness']).decode()+'`','',
          'Every supplied source unit is used in this selected control; cross-referenced controls and whole-product approval require separate review.','']
    (OUT/'review.md').write_text('\n'.join(lines))
    print(canonical(report).decode())

if __name__=='__main__':main()
