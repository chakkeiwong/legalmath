"""Zero-call, history-preserving source reconciliation for the authorized merge."""
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime, timezone
from copy import deepcopy
import json, hashlib, shutil, sys
ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts.legal_mission_execution import read, save, ref, verify, require, digest
from scripts.legal_baseline_corpus_deployment import acquire_locks, lock_paths, finish_transaction
BASE = Path('artifacts/legal-mission-control/2026-10-13/master')
WORK = Path('artifacts/legal-mission-control/2026-10-27/git-handoff')
DOC = Path('docs/implementation/legal-mission-control/checkpoint-2026-10-27')
LIVE = Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation/live')
HISTORY = DOC/'history'
REVIEW = DOC/'merge-binding-review.md'

def main():
    require(not (ROOT/WORK/'binding-transaction.json').exists(), 'Already reconciled; inspect retained result')
    binding = read(ROOT/BASE/'current-binding.json')
    handover = read(ROOT/WORK/'handover-request.json')
    finished = read(ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure/followthrough/runtime-deployment/finished.json')
    require(finished['refresh_exit'] == 0 and finished['at_utc'] >= handover['at_utc'], 'Handover refresh incomplete')
    journals = sorted(p.relative_to(ROOT) for p in (ROOT/LIVE).rglob('dispatch.json'))
    locks = lock_paths(ROOT, binding, journals)
    with ExitStack() as stack:
        acquire_locks(ROOT, stack, locks)
        require(ref(ROOT,BASE/'current-binding.json') == handover['binding'], 'Binding changed since safe handover')
        ledger = ref(ROOT,BASE/'live-calls.json')
        state = ref(ROOT,BASE/'execution-state.json')
        program = ref(ROOT,'docs/implementation/legal-mission-control/integration-master.json')
        require(len(read(ROOT/BASE/'live-calls.json')['calls']) == handover['calls'] == 7342, 'Changed charges')
        for path in journals:
            require(all(r['status'] != 'RESERVED' for r in read(ROOT/path)['calls'].values()), 'Uncertain provider dispatch')
        for pointer in handover['phases'] + handover['journals']:
            verify(ROOT,pointer)
        (ROOT/HISTORY).mkdir(parents=True,exist_ok=True)
        old_binding = HISTORY/'premerge-binding.json'
        require(not (ROOT/old_binding).exists(), 'Predecessor archive exists')
        shutil.copyfile(ROOT/BASE/'current-binding.json', ROOT/old_binding)
        old_pointer = read(ROOT/BASE/'current-stage.json'); verify(ROOT,old_pointer)
        before_stage = read(ROOT/old_pointer['path'])
        rows = read(ROOT/WORK/'premerge-source-manifest.json')['changes']
        require(len(rows) == 23 and all(r['path']=='pyproject.toml' or r['path'].startswith('src/legalmath/prospectus/') for r in rows), 'Unexpected merge scope')
        expected = {r['path']:r for r in rows}
        changed = []
        updated = deepcopy(binding)
        known = {(r['previous']['path'],r['previous']['sha256']) for r in updated['historical_archives']}
        for index,pointer in enumerate(binding['bindings']):
            current = ref(ROOT,pointer['path'])
            if current == pointer:
                continue
            row = expected[pointer['path']]
            require(pointer['sha256'] == row['before_sha256'] and current['sha256'] == row['main_sha256'], 'Unreviewed merged source')
            verify(ROOT,dict(path=row['archive'],sha256=row['before_sha256']))
            archived = HISTORY/'premerge-source'/pointer['path']
            (ROOT/archived).parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/row['archive'],ROOT/archived)
            replacement = dict(previous=pointer,archive=ref(ROOT,archived),current=current)
            changed.append(replacement)
            if (pointer['path'],pointer['sha256']) not in known:
                updated['historical_archives'].append(dict(previous=pointer,archive=replacement['archive']))
            updated['bindings'][index] = current
        require({r['previous']['path'] for r in changed} == set(expected), 'Wrong changed population')
        manifest = DOC/'merge-bindings.json'
        save(ROOT/manifest,dict(profile='reviewed-git-source-reconciliation.v1',
            at_utc=datetime.now(timezone.utc).isoformat(),review=ref(ROOT,REVIEW),
            prior_binding=ref(ROOT,old_binding),prior_stage=old_pointer,changes=changed,
            calls=7342,calls_added=0,attempts_added=0,limits_changed=False,
            program=program,state=state,ledger=ledger,legal_acceptance=False))
        updated['predecessor'] = ref(ROOT,old_binding)
        updated['phase_service_predecessor'] = updated['predecessor']
        updated['git_merge_reconciliation'] = ref(ROOT,manifest)
        updated['bindings'] += [ref(ROOT,manifest),ref(ROOT,REVIEW)]
        # Preserve the time-extension review, grant, all budgets and phase identity.
        for key in ('review','grant_hash','maximum_calls','deadline_utc','time_extension',
                    'effective_deadline_utc','execution_budget','product_closure','program'):
            require(updated[key] == binding[key], 'Authority or programme changed: '+key)
        save(ROOT/WORK/'merged-binding.json',updated)
        save(ROOT/DOC/'merged-stage.json',dict(before_stage,binding_hash=digest(updated)))
        save(ROOT/WORK/'merged-stage-pointer.json',ref(ROOT,DOC/'merged-stage.json'))
        for p in updated['bindings']:
            verify(ROOT,p)
        for row in updated['historical_archives']:
            require(row['previous']['sha256'] == row['archive']['sha256'],'Historical bytes changed')
            verify(ROOT,row['archive'])
        writes=[dict(path=str(BASE/'current-binding.json'),before=ref(ROOT,BASE/'current-binding.json'),replacement=ref(ROOT,WORK/'merged-binding.json')),
                dict(path=str(BASE/'current-stage.json'),before=ref(ROOT,BASE/'current-stage.json'),replacement=ref(ROOT,WORK/'merged-stage-pointer.json'))]
        save(ROOT/WORK/'binding-transaction.json',dict(profile='baseline-corpus-deployment-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,WORK/'binding-transaction.json')
        for pointer in (ledger,state,program,old_pointer):verify(ROOT,pointer)
        result=dict(status='RECONCILED_LOCAL_ONLY',changed_sources=23,calls_added=0,
            calls=7342,live_authority='EXPIRED; no dispatch',binding=ref(ROOT,BASE/'current-binding.json'),
            stage=ref(ROOT,BASE/'current-stage.json'),manifest=ref(ROOT,manifest))
        save(ROOT/DOC/'merge-binding-result.json',result)
        print(json.dumps(result,indent=2))

if __name__=='__main__':main()
