"""Public-source assurance and schedulable monitoring entry points."""
from pathlib import Path
import time
from ...canonical import loads, digest, raw_digest
from ...errors import LegalMathError
from ...sources.fetch import fetch
from ..search.providers import CodexProvider, Allowance, Completion
from .sources import official_url, transport_url
from .engine import Assurance, AssuranceSettings
from .monitor import Monitor


class ReplayProvider:
    """Explicit fixture mode; never represented as live model evidence."""
    provider_id = 'assurance.explicit-replay.v1'
    live = False

    def __init__(self, path): self.responses = iter(loads(Path(path).read_bytes()))

    def complete(self, request, schema, settings):
        try: value = next(self.responses)
        except StopIteration: raise LegalMathError('E_RESOURCE_LIMIT', details='Fixture responses exhausted')
        return Completion(value, {'provider':self.provider_id,'evidence_class':'SCRIPTED_ENGINEERING_FIXTURE'})


def read_documents(records, base):
    documents = []; findings = []
    for record in records:
        url = official_url(record['url'])
        try:
            if 'path' in record:
                data = (base / record['path']).read_bytes()
                if record.get('sha256') and raw_digest(data) != record['sha256']:
                    raise LegalMathError('E_HASH_MISMATCH')
                document = {'url':url,'data':data,'media_type':record['media_type']}
            else:
                document = {**fetch(transport_url(url)), 'url':url}
            if record.get('aliases'): document['aliases'] = record['aliases']
            documents.append(document)
        except (LegalMathError,OSError) as exc:
            findings.append({'kind':'SOURCE_UNAVAILABLE','url':url,'error':getattr(exc,'code',type(exc).__name__)})
    return documents, findings


def configured(args):
    settings = AssuranceSettings.model_validate(loads(Path(args.settings).read_bytes())) if args.settings else AssuranceSettings()
    if getattr(args,'replay_responses',None): provider = ReplayProvider(args.replay_responses)
    else:
        if not args.allowance: raise LegalMathError('E_AUTHORITY',details='Live assurance requires the authorized persistent allowance')
        provider = CodexProvider(allowance=Allowance(args.allowance,args.total_calls))
    return settings, provider


def execute(args):
    config_path = Path(args.manifest).resolve(); config = loads(config_path.read_bytes()); base=config_path.parent
    roots, errors = read_documents(config['roots'],base)
    retained, retained_errors = read_documents(config.get('retained',[]),base)
    catalog, catalog_errors = read_documents(config.get('authority_catalog',[]),base)
    if errors or retained_errors or catalog_errors:
        raise LegalMathError('E_DEPENDENCY',details=errors+retained_errors+catalog_errors)
    settings,provider = configured(args)
    return Assurance(args.out,provider,args.jdk,args.at,settings).drive(roots,config['selected_slice'],
        retained=retained,authority_catalog=catalog,expected_versions=config.get('expected_versions'))


def monitor(args):
    config_path=Path(args.config).resolve();config=loads(config_path.read_bytes())
    documents, errors=read_documents(config['documents'],config_path.parent)
    index={d['url']:d for d in documents};versions={url:raw_digest(d['data']) for url,d in index.items()}
    settings,provider=configured(args);root=Path(args.out)
    scheduler=Monitor(root/'monitor',cadence_seconds=config.get('cadence_seconds',86400),
                      max_attempts=config.get('max_attempts',2))
    # Derive the method fingerprint from the actual code, provider route and settings.
    method=Assurance(root/'configuration',provider,args.jdk,args.at,settings).method_hash
    def investigate(control,scope):
        prefix='run.'+digest({'control':control,'scope':scope})[:24]
        existing=list((root/'investigations').glob(prefix+'.*'))
        directory=root/'investigations'/(prefix+'.'+str(len(existing)))
        seeds=[index[url] for url in [control['source'],*control['dependencies']]]
        return Assurance(directory,provider,args.jdk,args.at,settings).drive(seeds,control['selected_slice'],retained=documents)
    return scheduler.tick(config['controls'],versions,method,config['fact_schema_hash'],
                          int(time.time()) if args.now is None else args.now,investigate,acquisition_findings=errors,
                          evaluation_at=args.at)
