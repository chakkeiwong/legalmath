"""Retain the actual preparation055 failure without changing frozen methods."""
import json
from scripts import prospectus_fresh_preparation as r

a=r.read(r.HERE/'fresh/P1/P1.json')
manifest=r.read(r.prior.prior.prior.PREP/'products.json')
b=r.read(r.ROOT/manifest['products']['P1']['path'])
assert a==b
r.save(r.HERE/'source-failure-diagnosis.json',{
    'cause':'Indented serialization exceeds cap measured on compact baseline',
    'pretty_bytes':(r.HERE/'fresh/P1/P1.json').stat().st_size,
    'compact_bytes':len(json.dumps(a,ensure_ascii=False,separators=(',',':')).encode()),
    'complete_P1_equal':True,
    'repair':'Write compact lossless JSON;retain 128MiB cap and original failed bytes'})
r.save(r.HERE/'result.json',{'status':'FAIL','task':'basf-references',
    'original_task_complete':False,'result_kind':'FRESH_PREPARATION_SERIALIZATION_FAILURE',
    'complete_P1_equal':True,'package_failure':False,
    'failure':'Prepared product exceeds size cap due to indentation','resources':r.costs(),
    'next_action':'Reviewed changed compact-serialization repair;no unchanged retry'})
(r.HERE/'RESULT.md').write_text('''# Fresh preparation rejected at serialization

The installed command reextracted all four original PDFs and its complete P1
equals the retained baseline. Indented JSON occupies139068110bytes,versus
65765520bytes losslessly compact. This exceeds the128MiBcap measured on compact
products. The failure is our serializer choice,not extraction,package capability
or evidence against staged preparation. Failed bytes remain unchanged.

All816tests and small installed phase controls passed,but did not expose this
realistic size mismatch. Downstream stages were not run. Add a compact-size
regression and change only serialization under a reviewed new attempt.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Reject current serializer|P1semantic equality passes;output cap fails|Candidate promotion veto|Downstream and full installed chain untested|Compact lossless serialization with regression|Package or research-direction failure|
''')
r.save(r.HERE/'outputs.json',{str(p.relative_to(r.HERE)):r.sha(p)
    for p in r.HERE.rglob('*') if p.is_file()})
print('Retained FAIL and complete P1 equality; failed evidence unchanged')
