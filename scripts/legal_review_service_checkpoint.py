"""Retain a running owner's checkpoint when its provider prerequisite disappears."""
import os
from scripts.legal_mission_execution import read, save, ref, verify, require, process_identity
from legalmath.canonical import digest
from legalmath.interpretation.assurance.phased.service_prerequisite import PROFILE, record


def checked(root, tid, row):
    pointer = row.get('service_checkpoint')
    require(pointer and row.get('master_live') and row['status'] == 'RUNNING',
        'Missing paused provider owner checkpoint')
    verify(root, pointer)
    value = read(root / pointer['path'])
    require(value['profile'] == PROFILE and value['task_id'] == tid and
        value['attempt'] == len(row['attempts']) and
        value['supervisor'] == row.get('live_supervisor') and
        value['prerequisite']['status'] == 'DEFERRED_SERVICE' and
        value['prerequisite']['dispatched'] is False and
        'result' not in row['attempts'][-1], 'Changed paused owner checkpoint')
    return value


def pause(execution, tid, directory, exc):
    with execution.locked() as state:
        row = state['tasks'][tid]
        require(row['status'] == 'RUNNING' and row.get('master_live') and
            row.get('live_supervisor') == process_identity(os.getpid()),
            'Provider pause has a different owner')
        value = dict(profile=PROFILE, task_id=tid, attempt=len(row['attempts']),
            supervisor=row['live_supervisor'], prerequisite=record(exc))
        path = directory/('service-checkpoint-'+digest(value)[:24]+'.json')
        if path.exists():
            require(read(path) == value, 'Changed provider pause evidence')
        else:
            save(path, value)
        row['service_checkpoint'] = ref(execution.root, path)
        row.pop('service_resume', None)
        execution.event(state, tid, 'SERVICE_CHECKPOINT', evidence=[row['service_checkpoint']],
            attempt=len(row['attempts']), new_attempt=False)
    return dict(service_deferred=True, evidence=ref(execution.root, path), legal_acceptance=False)
