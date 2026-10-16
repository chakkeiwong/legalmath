"""Immutable predecessor binding for explicitly admitted full source restarts."""
from pathlib import Path
import fcntl

from ...canonical import digest, loads, raw_digest
from ...errors import LegalMathError
from .diversity import save
from .source_context import input_identity


def check(ok, reason):
    if not ok:
        raise LegalMathError('E_STALE_REVIEW', details=reason)


def snapshot(directory):
    return {str(p.relative_to(directory)):raw_digest(p.read_bytes()) for p in sorted(directory.rglob('*')) if p.is_file()}


def validate(runner, restart, roots, retained, question, originals, context):
    check(restart.get('profile')=='full-source-restart.v1','Unknown restart profile')
    record=runner.directory/'source-restarts'/('restart-'+str(restart['number'])+'.json')
    check(record.is_file() and loads(record.read_bytes())==restart,'Unregistered or changed restart')
    prior=runner.directory/'revisions'/restart['predecessor_revision']
    check(prior.is_dir() and snapshot(prior)==restart['predecessor_files'],'Predecessor changed')
    history=loads((runner.directory/'revisions.json').read_bytes())
    previous=next((r for r in history if r['revision']==restart['predecessor_revision']),None)
    check(previous is not None and digest(previous['binding'])==restart['predecessor_revision'],'Unknown predecessor revision')
    bound=previous['binding']
    check(bound['question']==question and bound.get('original_questions')==originals,'Restart changed original target')
    check(bound['source_input_context']==input_identity(roots,retained),'Restart changed source identity')
    check(bound.get('qualified_source_context')==context,'Restart changed source qualification')
    stop=loads((prior/'prerequisite-failure.json').read_bytes())
    check(stop['stage']=='SOURCE_REVIEW_RESTART' and digest(stop['repair_stop'])==restart['repair_stop_hash'],'Changed or absent repair concern')
    concern={k:v for k,v in stop['repair_stop']['concern'].items() if k not in ('candidate_id','representation_quotes')}
    check(restart['source_concern']==concern and restart['invalidated_stages']==stop['repair_stop']['invalidated_stages'],'Restart changed the retained concern or invalidation scope')
    check(1<=restart['number']<=restart['maximum_restarts']<=2,'Restart bound exceeded')


def prepare(runner, predecessor, roots, question, maximum, kwargs):
    check(type(maximum) is int and 1<=maximum<=2,'One or two explicitly reserved restarts required')
    check(isinstance(predecessor,str) and len(predecessor)==64 and all(c in '0123456789abcdef' for c in predecessor),'Invalid predecessor ID')
    check('source_restart' not in kwargs,'Caller cannot replace registered restart')
    directory=runner.directory/'source-restarts'
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'restart.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        existing=[loads(p.read_bytes()) for p in sorted(directory.glob('restart-*.json'))]
        check(all(x['maximum_restarts']==maximum for x in existing),'Cannot increase restart ceiling on resume')
        matched=[x for x in existing if x['predecessor_revision']==predecessor]
        if matched:
            restart=matched[0]
            validate(runner,restart,roots,kwargs.get('retained',()),question,kwargs.get('original_questions'),kwargs.get('source_context'))
            return restart
        check(len(existing)<maximum,'Full source restart allowance exhausted')
        history=loads((runner.directory/'revisions.json').read_bytes())
        prior=next((x for x in history if x['revision']==predecessor),None)
        check(prior is not None,'Unknown predecessor revision')
        binding=prior['binding']
        check(binding['question']==question and binding.get('original_questions')==kwargs.get('original_questions'),'Restart changed original target')
        check(binding['source_input_context']==input_identity(roots,kwargs.get('retained',())),'Restart changed source identity')
        check(binding.get('qualified_source_context')==kwargs.get('source_context'),'Restart changed source qualification')
        folder=runner.directory/'revisions'/predecessor
        failure=loads((folder/'prerequisite-failure.json').read_bytes())
        check(failure['stage']=='SOURCE_REVIEW_RESTART','Predecessor did not require source restart')
        stop=failure['repair_stop']
        concern={k:v for k,v in stop['concern'].items() if k not in ('candidate_id','representation_quotes')}
        restart={'profile':'full-source-restart.v1','number':len(existing)+1,'maximum_restarts':maximum,
                 'predecessor_revision':predecessor,'predecessor_files':snapshot(folder),
                 'repair_stop_hash':digest(stop),'source_concern':concern,
                 'invalidated_stages':stop['invalidated_stages'],
                 'new_source_readers_required':['atomic-reader','qualification-reader'],
                 'resource_policy':'Same provider authority and remaining aggregate route budget; this receipt grants no calls.'}
        save(directory/('restart-'+str(restart['number'])+'.json'),restart)
        validate(runner,restart,roots,kwargs.get('retained',()),question,kwargs.get('original_questions'),kwargs.get('source_context'))
        return restart
