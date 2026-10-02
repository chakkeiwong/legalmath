#!/usr/bin/env python3
"""Run source classification and optional formal/native checks with receipts."""
import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from legalmath.prospectus.common import ROOT, now, read, sha, write
from legalmath.prospectus.loss_absorption import POLICY
from legalmath.prospectus.loss_absorption_reader import analyze_issue


def source_versions():
    paths = sorted((ROOT / 'src/legalmath/prospectus').glob('loss_absorption*.py'))
    paths += [ROOT/'src/legalmath/prospectus/money_witness.py', ROOT/'src/legalmath/prospectus/source_obligations.py', ROOT/'src/legalmath/prospectus/feature_investigation.py']
    paths += [Path(__file__), ROOT / 'scripts/build_bond_feature_inventory.py']
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}


def run(inventory, output, checks=False, plan='docs/plans/bond-reader-repair-program.md'):
    start = time.monotonic(); output.mkdir(parents=True, exist_ok=False)
    metadata = read(inventory); versions = source_versions()
    manifest = {'started_at': now(), 'command': sys.argv, 'python': sys.version,
        'environment': str(Path(sys.executable)), 'platform': platform.platform(),
        'git_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        'dirty_source_hashes': versions, 'inventory': str(inventory), 'inventory_sha256': sha(inventory.read_bytes()),
        'cpu_gpu': 'CPU only; no GPU framework imported', 'seeds': 'N/A: deterministic',
        'plan': str(plan), 'policy': POLICY,
        'data_versions': {k: {'original':v['sha256'], 'text':v['text_sha256']} for k,v in metadata['documents'].items()},
        'human_quality_labels': False, 'status': 'RUNNING'}
    write(output/'run-manifest.json', manifest)
    phases = []
    def checkpoint(name, result, next_step):
        phases.append({'phase': name, 'time': now(), 'result': result, 'next_step': next_step})
        write(output/'checkpoints.json', phases)
        (output/'next-phase.md').write_text('# Refreshed continuation\n\n'+next_step+'\n')
    try:
        checkpoint('L0', {'issues':len(metadata['issues']), 'documents':len(metadata['documents'])},
                   'L1: validate original/extraction identity and analyze all declared pages. A damaged source must remain unresolved.')
        results = [analyze_issue(issue, metadata['documents'], ROOT) for issue in metadata['issues']]
        write(output/'classification.json', {'policy':POLICY, 'scope':metadata['scope'], 'results':results})
        summary = {'bonds':len(results), 'yes':sum(r['answer'] is True for r in results),
            'no':sum(r['answer'] is False for r in results), 'unresolved':sum(r['answer'] is None for r in results),
            'source_pages':sum(v['pages'] for v in metadata['documents'].values()),
            'legal_entailment':'NOT_PROVED', 'human_quality_labels':False}
        checkpoint('L1', summary, 'L2: publish each issue, result, generated reason, qualification and supporting evidence. Preserve unresolved rows.')
        columns = ['id','title','issuer','jurisdiction','rank','identifiers','answer','classification','status','summary_reason','qualification']
        with (output/'classification.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=columns); writer.writeheader()
            for row in results:
                writer.writerow({k: ('; '.join(row[k]) if isinstance(row.get(k),list) else row.get(k)) for k in columns})
        lines = ['# Bond-by-bond loss-absorption feature results', '',
            'Yes means an applicable principal write-down or compulsory common-share conversion was identified. '
            'No means neither was identified in the declared offering documents, with affirmative debt and principal-repayment terms. '
            'Ordinary creditor-approved restructuring, optional conversion and coupon deferral are recorded separately. '
            'All source conclusions are qualified; formal checks do not prove English meaning or current legal eligibility.', '',
            '| Bond | ISIN / issue identifier | Answer | Reason |', '| --- | --- | --- | --- |']
        for row in results:
            answer = 'Yes — loss absorption' if row['answer'] is True else 'No — non loss absorption' if row['answer'] is False else 'Unresolved'
            identifier = ', '.join(row['identifiers']) or row['id']
            lines.append('| '+ ' | '.join(str(s).replace('|','/') for s in (row['title'], identifier, answer, row['summary_reason']))+' |')
        lines += ['', '## Source qualifications', '', metadata['scope'], '']
        for row in results:
            qualifications = [row[k] for k in ('identity_qualification','source_language_qualification','dependency_boundary') if row.get(k)]
            if qualifications: lines.append('- '+row['id']+': '+' '.join(qualifications))
        lines += ['', 'Document/section scope is an explicitly recorded source interpretation, not a quality label. '
            'The JSON preserves quotations, candidate dispositions, original/extraction hashes, all open issues and per-document page coverage.', '']
        (output/'classification.md').write_text('\n'.join(lines))
        checkpoint('L2', summary, 'L3: run controlled integrity/parser tests, independent formal obligations and identical native RuleIR/Catala cases. Repair failures before freezing.')
        if checks:
            from legalmath.prospectus.loss_absorption_checks import native, prove
            completed = subprocess.run([sys.executable,'-m','pytest','tests/prospectus/test_loss_absorption.py',
                'tests/prospectus/test_loss_absorption_repair.py','tests/prospectus/test_loss_absorption_two_case.py',
                'tests/prospectus/test_bond_report_presentation.py','tests/prospectus/test_gap_closure.py','tests/prospectus/test_feature_investigation.py','-q',
                '--junitxml='+str(output/'tests.xml')],cwd=ROOT,capture_output=True,text=True,timeout=120)
            (output/'tests.log').write_text(completed.stdout+completed.stderr)
            if completed.returncode: raise ValueError('Controlled tests failed; see tests.log')
            summary['formal'] = prove(output/'formal')
            summary['native'] = native(output/'native',results)
            checkpoint('L3', summary, 'L4: freeze the source hashes, acquire an uninspected issuer-family challenge and execute without modifying the method. Exposed cases become development if a repair is needed.')
        if source_versions() != versions or sha(inventory.read_bytes()) != manifest['inventory_sha256']:
            raise ValueError('Implementation or inventory changed during the run')
        if not summary['yes'] or not summary['no']:
            summary['coverage_status'] = 'INCOMPLETE: no demonstrated positive/negative contrast'
        else:
            summary['coverage_status'] = 'PARTIAL' if summary['unresolved'] else 'QUALIFIED_SOURCE_RESULTS_COMPLETE'
        write(output/'summary.json',summary)
        manifest.update(status='COMPLETE', finished_at=now(), wall_seconds=time.monotonic()-start,
            result=str(output/'classification.json'), artifacts={str(p.relative_to(output)):sha(p.read_bytes())
            for p in output.rglob('*') if p.is_file() and p.name!='run-manifest.json'})
        write(output/'run-manifest.json',manifest)
        print(json.dumps({k:v for k,v in summary.items() if k not in ('formal','native')},indent=2))
        return summary
    except Exception as exc:
        manifest.update(status='FAILED',error=str(exc),finished_at=now(),wall_seconds=time.monotonic()-start)
        write(output/'run-manifest.json',manifest)
        checkpoint('REPAIR_REQUIRED', {'error':str(exc)}, 'Preserve this failed attempt. Diagnose the source, implementation or harness failure; record a causal repair and execute a new output directory. No promotion from this attempt.')
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--checks',action='store_true')
    parser.add_argument('--plan',type=Path,default=Path('docs/plans/bond-reader-repair-program.md'))
    args=parser.parse_args(); run(args.inventory,args.output,args.checks,args.plan)
