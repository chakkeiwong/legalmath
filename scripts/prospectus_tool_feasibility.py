"""Bounded official-source access checks; no package installation or credentials."""
from datetime import datetime, timezone
import json
import subprocess
from scripts.prospectus_integration_repair import OUT, save, sha

SOURCES = {
    'actus-core-repository': 'https://api.github.com/repos/actusfrf/actus-core',
    'actus-distributions-tree': 'https://api.github.com/repos/actusfrf/actus-distributions/git/trees/main?recursive=1',
    'actus-service-readme': 'https://raw.githubusercontent.com/actusfrf/actus-service/7293157a7f272925dbce68b5a037d2e23c585c9e/README.md',
    'actus-service-readme-case-corrected': 'https://raw.githubusercontent.com/actusfrf/actus-service/7293157a7f272925dbce68b5a037d2e23c585c9e/ReadMe.md',
    'actus-userguides-tree': 'https://api.github.com/repos/actusfrf/actus-userguides/git/trees/main?recursive=1',
    'actus-installation-guide': 'https://raw.githubusercontent.com/actusfrf/actus-userguides/60234c1ea538115386421aec94ede4bcae0a94d4/docs/getting-started/installation.md',
    'actus-pam-guide': 'https://raw.githubusercontent.com/actusfrf/actus-userguides/60234c1ea538115386421aec94ede4bcae0a94d4/docs/contract-types/PAM.md',
    'actus-python-architecture': 'https://raw.githubusercontent.com/actusfrf/actus-userguides/60234c1ea538115386421aec94ede4bcae0a94d4/docs/awesome-actus-lib/architecture.md',
    "cdm-python-readme": "https://raw.githubusercontent.com/finos/common-domain-model/65996cfa8defcd1f15eb457f9d2c50295b3e9691/python/README.md",
    "cdm-pom": "https://raw.githubusercontent.com/finos/common-domain-model/65996cfa8defcd1f15eb457f9d2c50295b3e9691/pom.xml",
}


def refresh():
    folder = OUT/'official-sources'
    folder.mkdir(exist_ok=True)
    ledger_path = folder/'requests.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    receipts = {}
    for key, url in SOURCES.items():
        target, receipt = folder/(key+'.txt'), folder/(key+'.json')
        if receipt.exists():
            row = json.loads(receipt.read_text())
            if row['url'] != url or sha(target) != row['sha256']:
                raise ValueError('Changed retained official source')
            receipts[key] = row
            continue
        if len(ledger) >= 10 or sum(r['reserved_bytes'] for r in ledger)+2_000_000 > 20_000_000:
            raise ValueError('Official-source refresh budget exhausted')
        ledger.append({'url': url, 'reserved_bytes': 2_000_000})
        save(ledger_path, ledger)
        # No redirects/retries: each reserved request is one actual request.
        argv = ['curl','--silent','--show-error','--proto','=https','--connect-timeout','12',
                '--max-time','40','--max-filesize','2000000','--output',str(target),
                '--write-out','%{http_code}',url]
        run = subprocess.run(argv, capture_output=True, text=True, timeout=45)
        row = {'url': url, 'command': argv, 'http_status': run.stdout,
               'returncode': run.returncode, 'error': run.stderr,
               'retrieved_utc': datetime.now(timezone.utc).isoformat()}
        if run.returncode or run.stdout not in ('200','404'):
            save(folder/(key+'-failed-request.json'), row)
            raise RuntimeError('Official-source request failed; inspect retained transport receipt')
        row['sha256'] = sha(target)
        row['bytes'] = target.stat().st_size
        save(receipt, row)
        receipts[key] = row
    return receipts
