# Executing an admitted future source

The window is created only after final verification by the approved command
`run_assurance_new_grant.py freeze-future`. Its execution configuration names
the exact tested snapshot and fixed pilot allowance. Run Python with that
snapshot's `src` directory first on `PYTHONPATH`; the moving workspace is not
the frozen implementation. A copied or rebuilt installation is a different
method when its bound dependencies or paths differ.

The following API sequence makes no legal answer assumptions. `submission` is
captured source metadata, not a quality label. `roots` and `retained` contain
actual source bytes, official URLs and media types. `selected_question` is the
natural-language investigation scope, and `assessment_at` is the declared
assessment instant for that task. Publication and first-encounter timestamps
must come from retained evidence; do not supply imagined future dates.

```python
from pathlib import Path
from legalmath.canonical import digest, loads
from legalmath.interpretation.assurance import investigation_observations as obs
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance.engine import AssuranceSettings
from legalmath.interpretation.assurance.grants import GrantSlice
from legalmath.interpretation.search.providers import CodexProvider

workspace = Path('/home/chakwong/python/legalmath')
campaign = workspace / 'artifacts/assurance-new-grant/2026-09-29'
window = campaign / 'whole-method-window'
spec = loads((window / 'freeze.json').read_bytes())
configuration = loads((window / 'execution-configuration.json').read_bytes())
method = configuration['method_configuration']
snapshot = Path(configuration['tested_snapshot'])

allowance = GrantSlice(campaign / 'grant.json',
                      Path(configuration['pilot_allowance_path']),
                      configuration['pilot_maximum'])
provider = CodexProvider(allowance=allowance)
catala = {
    'compiler': Path(method['toolchains']['catala']['compiler']['path']),
    'lock': Path(method['toolchains']['catala']['lock']['path']),
    'upstream': snapshot / '.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
}
# Keep proof/runtime evidence and pinned tools under the same evidence root.
# The grant and window remain in the original workspace; changing storage
# location does not change the frozen method's source or tool identities.
runner = CompleteInvestigation(
    snapshot, snapshot / 'artifacts/whole-method-future-investigations', provider,
    Path(method['toolchains']['java']['java']['path']).parent.parent,
    assessment_at,
    settings=AssuranceSettings.model_validate(method['settings']),
    catala=catala,
    maximum_scoped_actions=method['scoped']['maximum_actions'],
    scoped_rounds=method['scoped']['rounds'],
    scoped_batch_size=method['scoped']['batch_size'],
    scoped_pair_order=method['scoped']['pair_order'],
    scoped_schedule=method['scoped']['schedule'],
    reference_protocol=method['transports']['scoped'],
    machine_qualification=True,
)

# Selection uses the raw primary-source SHA-256, not a hash of an enlarged
# context bundle. The complete bundle is separately bound by the investigation.
from legalmath.canonical import raw_digest
item = {
    'task_id': submission['task_id'],
    'family': 'SFC_PUBLIC_CIRCULAR',
    'source_hash': raw_digest(roots[0]['data']),
    'question_hash': digest(selected_question),
    'published_at': submission['published_at'],
    'first_seen_at': submission['first_seen_at'],
}
selected = obs.admit(window, spec['window_hash'], item, runner)
if selected['status'] == 'PENDING':
    dossier = runner.run(roots, selected_question, retained=retained)
    dossier_ref = loads((runner.directory / 'current.json').read_bytes())
    event = obs.observe(window, spec['window_hash'], item['task_id'], dossier_ref, runner)
    report = obs.report(window, spec['window_hash'], expected_head=event['event_hash'])
else:
    report = obs.report(window, spec['window_hash'], expected_head=selected['event_hash'])
```

The example uses the default empty qualification-case list. Its report must
therefore retain zero native target-case coverage unless actual mathematical
cases are supplied. Formal preservation checks, source interpretation proposals
and selected runtime cases are different evidence. Supplying cases must not
supply human expected legal answers.

If `run` fails, preserve its files and the PENDING admission. If `observe` rejects
an identity or missing stage, retain that failure and the original pending task.
Do not catch the exception and manufacture an OBSERVE event. Do not repeat
`admit` under a new task ID: the same source/question is retained as an
ineligible duplicate. Reconstruct the original selection from the window's
immutable event records and investigate its failure within the existing limits.

A source revision changes the retained inputs. A method repair changes the
window's interpretation: call `obs.repair` with the actual revised runner and
cause, retain the old window as development evidence, and freeze a later
confirmation window after verification. An ordinary new source's assessment
instant may differ from the setup instant; it is an input premise recorded in
the dossier, not a change in the frozen interpreter configuration.
