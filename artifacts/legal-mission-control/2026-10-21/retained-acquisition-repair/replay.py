"""Validate one real master entry with the corrected loader and no transport."""
import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts import legal_integration_phased_live as live
from scripts import legal_product_completion as entry
from scripts.legal_mission_execution import read, ref, save
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider

WORK = Path(__file__).resolve().parent


def main(question):
    started = time.monotonic()
    implementation = ref(ROOT, 'src/legalmath/interpretation/assurance/phased/retained_acquisition.py')
    version = implementation['sha256'][:12]
    output = WORK/'replay'/version/question
    ledger_path = ROOT/'artifacts/legal-mission-control/2026-10-13/master/live-calls.json'
    before = ref(ROOT, ledger_path)
    run_product = entry.run_product

    def isolated(root, directory, provider, jdk, at, **kwargs):
        kwargs.update(bounded_phase='acquire', shared_prefix=None)
        return run_product(root, output, provider, jdk, at, **kwargs)

    def never(*args, **kwargs):
        raise AssertionError('Offline production replay attempted dispatch or phase admission')

    service = live.configure().provider()
    result = dict(question=question, started_at_utc=datetime.now(timezone.utc).isoformat(),
        command='.venv-context/bin/python ' + str(Path(__file__).relative_to(ROOT)) + ' ' + question,
        cpu_mode='GPU deliberately hidden', provider_calls=0,
        implementation=implementation)
    try:
        with patch.object(entry, 'run_product', isolated), \
                patch.object(BoundedCodexProvider, 'complete', never), \
                patch.object(live, 'phase_admit', lambda owner: never):
            acquired = live.product_route(question, None, service)
        assert acquired['question_acquisition_complete'][question]
        receipt = read(output/'retained-acquisition-validation.json')
        assert receipt['new_provider_calls'] == 0 and receipt['capacity_rebatching']
        assert all(set(row) == {'planned_packet', 'retained_parent'} for row in receipt['capacity_rebatching'])
        result.update(entry_result='VALIDATED', receipt=ref(ROOT, output/'retained-acquisition-validation.json'),
            planned_requests=receipt['planned_requests'], retained_requests=receipt['retained_requests'],
            rebatched_children=len(receipt['capacity_rebatching']))
    except Exception as exc:
        result['entry_result'] = dict(code=getattr(exc, 'code', type(exc).__name__),
            reason=str(getattr(exc, 'details', None) or exc))
    result.update(ledger_unchanged=before == ref(ROOT, ledger_path), wall_seconds=time.monotonic()-started)
    save(WORK/('replay-'+question+'-'+version+'.json'), result)
    print(result, flush=True)
    return 0 if result['entry_result'] == 'VALIDATED' and result['ledger_unchanged'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question', choices=['p10', 'p14', 'evidence', 'gatecoin'])
    sys.exit(main(parser.parse_args().question))
