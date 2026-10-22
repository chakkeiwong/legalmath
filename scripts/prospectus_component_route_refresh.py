"""Update an unadmitted proposal's route projection without changing task scope."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,REL,read,write,file_hash,digest
from scripts.prospectus_component_evidence import COMPONENTS
revision=int(sys.argv[1]);auth=Authority(ROOT);old,_,_=auth.spec()
assert old['revision']==revision-1
proposal=ROOT/REL/'proposals'/f'component-{revision}.json'
review=ROOT/REL/'proposals'/f'component-{revision}-review.json'
new=read(proposal);audit=read(review);assert new['revision']==revision
mapping=read(ROOT/new['continuation_review']['routes']);mapping['baseline_revision']=revision
events=auth.events();tasks={t['id']:t for t in new['tasks']}
for kind,(key,_,criterion,_) in COMPONENTS.items():
    task=tasks[key];row=next(r for r in mapping['tasks'] if r['task']==key)
    selection=task.get('current_component_validation',{})
    active=selection.get('review','').endswith('-'+str(revision))
    if active:
        row.update(phase=0,task_sha256=digest(task),dossier=task['dossier'],
            next_action='Execute admitted current and isolated installed '+kind+' validation; preserve complete original outputs and all controls, then record and refresh.')
    else:
        last=next((e for e in reversed(events) if e.get('task')==key and e['kind'] in {'RECORD','ACCEPT','REJECT'}),None)
        if last and criterion in last.get('build_acceptances',[]):
            row.update(phase=5,remaining='Finite '+kind+' criterion recorded in '+last['attempt']+'; original wider requirements remain.',
                next_action='Preserve the complete finite installed proof; continue distinct original source/financial requirements. Revalidation is needed after any further bound production change.')
route=REL+f'/closure-routes-2026-10-17-components-{revision}.json'
write(ROOT/route,mapping,exclusive=True)
new['continuation_review']['routes']=route
for name in [route,str(Path(__file__).relative_to(ROOT))]:new['continuation_review']['bindings'][name]=file_hash(ROOT/name)
audit['changes'].append('Refresh completed component dispositions and next admitted work without altering scope')
write(proposal,new);write(review,audit)
print({'updated_unadmitted_revision':revision})
