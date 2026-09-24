"""Source-bound retention of proposals changed or rejected during output repair."""
from pathlib import Path
from ...canonical import loads,raw_digest,digest
from ...errors import LegalMathError
from .checkpoints import check_manifest


def invalid_generation_proposals(directory,issue,packet):
    """Recover evidence for reconsideration, without editing invalid readings.

    An invalid scope, label, fact or quote is never silently filled in. A fresh
    task must propose any replacement; the exact original remains visible.
    """
    directory=Path(directory).resolve();records=[]
    for path in sorted(directory.rglob('outcome.json')):
        attempt=path.parent;outcome=loads(path.read_bytes())
        if outcome['status']=='VALIDATED' or not (attempt/'response.json').exists():continue
        manifest=check_manifest(attempt)
        if not {'response.json','request.json','outcome.json'}<=set(manifest['files']):
            raise LegalMathError('E_INTEGRITY')
        request=loads((attempt/'request.json').read_bytes())
        if request.get('original_task',request.get('task'))!='ISSUE_HYPOTHESES':continue
        if request['source_packet']!=packet or request['issue']!=issue:raise LegalMathError('E_STALE_REVIEW')
        raw=loads((attempt/'response.json').read_bytes())['value']
        values=raw.get('readings',[]) if isinstance(raw,dict) else []
        if not isinstance(values,list) or len(values)>4:raise LegalMathError('E_RESOURCE_LIMIT')
        for index,reading in enumerate(values):
            records.append({'attempt':str(attempt),'response_sha256':raw_digest((attempt/'response.json').read_bytes()),
                'reading_index':index,'original_reading':reading,'validation_failure':outcome,
                'provisional_only':True,'independent_opinion':False})
    return {'issue_hash':digest(issue),'records':records,'unvalidated_proposals':len(records),
            'semantic_edits_performed':False,'release_eligible':False}
