"""Freeze identical, explicitly selected source bytes for both study arms."""
from pathlib import Path
from legalmath.canonical import digest,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.sources import acquire_context,packet_from_context,audit_packet
from legalmath.interpretation.assurance.engine import coalesce_dependency_records
from run_assurance_successor import read,save


def read_source(root,ref):
    path=(Path(root)/ref['path']).resolve()
    if not path.is_relative_to(Path(root).resolve()):raise LegalMathError('E_REFERENCE')
    data=path.read_bytes()
    if raw_digest(data)!=ref['sha256']:raise LegalMathError('E_INTEGRITY',details='Selected source bytes changed')
    return {'url':ref['url'],'media_type':ref['media_type'],'data':data}


def appendix_reference(root,out,task,original,url):
    """Reuse an already frozen source when an old receipt names another checkout."""
    root=Path(root).resolve();old=Path(original['path'])
    local=(old if old.is_absolute() else root/old).resolve()
    if local.is_relative_to(root):
        return {'path':str(local.relative_to(root)),'sha256':original['sha256'],
                'url':url,'media_type':'application/pdf'}
    frozen=Path(out)/'study-source-freeze.json'
    if not old.is_absolute() or not frozen.is_file():
        raise LegalMathError('E_REFERENCE',details='Outside-checkout appendix needs its existing frozen source binding')
    records=[r for r in read(frozen)['tasks'] if r['task_id']==task['task_id']]
    if len(records)!=1 or records[0]['original_task_hash']!=digest(task):
        raise LegalMathError('E_INTEGRITY',details='Frozen appendix belongs to a different or ambiguous task')
    choices=[r for r in records[0]['sources'] if r['url']==url]
    if (len(choices)!=1 or choices[0]['sha256']!=original['sha256'] or
            choices[0]['media_type']!='application/pdf'):
        raise LegalMathError('E_INTEGRITY',details='Frozen appendix differs from its original producer receipt')
    ref=choices[0];name=Path(ref['path'])
    if name.is_absolute() or '..' in name.parts:
        raise LegalMathError('E_REFERENCE',details='Frozen appendix must use a repository-relative path')
    # This checks both the resolved path boundary and the original byte hash.
    # The caller still compares the complete reconstructed source freeze.
    read_source(root,ref)
    return {k:ref[k] for k in ('path','sha256','url','media_type')}


def prepare(root,out,tasks):
    root,out=Path(root),Path(out);prepared={};records=[]
    for task in tasks:
        refs=[task['source']]
        if task['task_id']=='26ec35':
            original=read(out/'S1/attempt-01/appendix/input.json')
            choices=[r for r in task['unresolved_references'] if r['relation']=='incorporates']
            if len(choices)!=1:raise LegalMathError('E_REFERENCE',details='Expected exact frozen authentication appendix')
            refs.append(appendix_reference(root,out,task,original,choices[0]['url']))
        sources=[read_source(root,r) for r in refs]
        # Retained catalogue documents are not automatically roots. Explicitly
        # select the incorporated appendix for BOTH arms at depth zero.
        context=acquire_context(sources,max_documents=8,max_depth=0)
        if len(context['documents'])!=len(sources):raise LegalMathError('E_INTEGRITY',details='A selected source did not enter the context')
        packet=packet_from_context(context,task['selected_slice'])
        if audit_packet(packet,context):raise LegalMathError('E_INTEGRITY',details='Selected source characters lost')
        packet,_=coalesce_dependency_records(packet)
        original_units={u['unit_id']:u['text'] for u in task['packet'].get('units',[])}
        shared_units={u['unit_id']:u['text'] for u in packet['units']}
        if any(shared_units.get(k)!=v for k,v in original_units.items()):
            raise LegalMathError('E_INTEGRITY',details='Original frozen root passage changed')
        records.append({'task_id':task['task_id'],'original_task_hash':digest(task),'sources':refs,
            'packet':packet,'packet_hash':digest(packet),'selected_documents':len(sources),
            'root_passages_unchanged':True,'both_arms_receive_same_packet':True})
        prepared[task['task_id']]={'task':{**task,'packet':packet},'sources':sources}
    value={'profile':'shared-study-sources.v1','tasks':records,
        'changes_to_conditional_reference_answers':False,'source_access_comparison':'Identical explicitly selected sources; different investigation mechanisms'}
    target=out/'study-source-freeze.json'
    if target.exists():
        if read(target)!=value:raise LegalMathError('E_STALE_REVIEW',details='Shared study source freeze changed')
    else:
        if any((out/'unfamiliar-study').glob('*/single-summary.json')):
            raise LegalMathError('E_STALE_REVIEW',details='Shared source freeze must precede study answers')
        save(target,value)
    return prepared
