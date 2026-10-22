"""Retain085's lexical false-heading failure; do not modify its frozen methods."""
from scripts import prospectus_reference_address_projection as run
import xml.etree.ElementTree as ET

here=run.HERE;assert not (here/'outputs.json').exists()
suites=list(ET.parse(here/'pytest.xml').getroot().iter('testsuite'))
counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
assert counts=={'tests':117,'failures':9,'errors':0,'skipped':0}
diagnostic=run.read(here/'stages/diagnostic/result.json')
assert len(diagnostic['index_issues'])==1 and diagnostic['index_issues'][0]['label']=='etwaiger'
result={'status':'FAIL','task':'basf-references','original_task_complete':False,
    'result_kind':'PARENTHETICAL_PROSE_FALSE_HEADING','tests':counts,'resources':run.costs(),
    'next_action':'Narrow label recognition to numeric,single-letter or Roman candidates; retain all source expectations'}
run.save(here/'result.json',result)
run.save(here/'run-manifest.json',{'git_commit':run.read(here/'admission.json')['git_commit'],
    'commands':[run.read(here/'stages'/s/'started.json')['command'] for s in ('install','tests')]+[diagnostic['command']],
    'environment':str(run.ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
    'seeds':'N/A deterministic','data_version':run.sha(run.previous.PRODUCTS),'wall_time':run.costs(),
    'plan':run.PLAN,'result':run.rel(here/'result.json')})
(here/'RESULT.md').write_text('''# A prose parenthesis is not a structural heading

108 tests passed and nine failed. The transformation repair passes its adverse
controls and no longer rejects substituted final terms. The source index then
mistook the ordinary parenthetical word (etwaiger) for a paragraph label, reset
the section9 parent and truncated its first paragraph. The retained diagnostic
shows three later address differences, all in that affected section.

| Decision | Primary criterion | Veto | Uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Reject085 | Original source destinations not yet equal | False heading from overly broad lexical pattern | Full consumers not run | Narrow candidate label grammar and preserve expectations | PDF-package or reference-method failure |

Keep the original tests, oracle, expected intervals and failed result unchanged.
The repair must continue refusing unsupported label-like tokens while ignoring
ordinary multi-letter parenthetical prose.
''')
run.save(here/'outputs.json',{str(p.relative_to(here)):run.sha(p) for p in here.rglob('*') if p.is_file()})
print('Sealed FAIL085; 108passed/9failed; no full consumers or package')
