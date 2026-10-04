"""Packaged Java boundary for actor-attributed, historical contact evidence."""
from pathlib import Path
import subprocess
import tempfile
import zipfile
from ..canonical import canonical,digest,raw_digest,loads
from ..errors import LegalMathError
from .emit import emit,runtime_sources
from .manifest import toolchain

PROFILE='attributed-contact-history-v1'


def build(trigger,performance,policy,output,jdk):
    from ..ir.typecheck import validate_bundle
    if validate_bundle(trigger) or validate_bundle(performance):raise LegalMathError('E_SCHEMA')
    if ({f['name']:f['type'] for f in trigger['facts']}!={'licensed':'bool','urgent':'bool','in_window':'bool'} or
        {f['name']:f['type'] for f in performance['facts']}!={'contact_observed':'bool'}):
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    jdk,version=toolchain(jdk);tn,ts=emit(trigger);pn,ps=emit(performance)
    entry='Contact_'+digest({'trigger':trigger,'performance':performance,'policy':policy})[:20]
    template=(Path(__file__).parent/'contact'/'ContactHistory.java').read_text()
    template=template.replace('CONTACT_ENTRY',entry).replace('TRIGGER_POLICY',tn).replace('PERFORMANCE_POLICY',pn)
    template=template.replace('POLICY_STRING',canonical(canonical(policy).decode()).decode())
    sources={**runtime_sources(),tn+'.java':ts,pn+'.java':ps,entry+'.java':template}
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='legalmath-contact-') as temp:
        d=Path(temp);classes=d/'classes';classes.mkdir()
        for n,s in sources.items():(d/n).write_text(s)
        command=[str(jdk/'bin/javac'),'--release','17','-encoding','UTF-8','-g:none','-Xlint:all','-Werror',
            '-d',str(classes),*[str(p) for p in sorted(d.glob('*.java'))]]
        subprocess.run(command,check=True,capture_output=True,timeout=60)
        jar=d/'contact.jar'
        with zipfile.ZipFile(jar,'w',compression=zipfile.ZIP_STORED) as z:
            entries={'META-INF/MANIFEST.MF':f'Manifest-Version: 1.0\r\nMain-Class: hk.legalmath.{entry}\r\n\r\n'.encode(),
                    **{str(p.relative_to(classes)):p.read_bytes() for p in classes.rglob('*.class')}}
            for n,data in sorted(entries.items()):
                info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));info.external_attr=0o100644<<16;z.writestr(info,data)
        data=jar.read_bytes()
    target=output/(raw_digest(data)+'.jar');target.write_bytes(data)
    result={'profile':PROFILE,'jar':str(target),'jar_sha256':raw_digest(data),'entry_class':'hk.legalmath.'+entry,
            'policy_hash':digest(policy),'bundle_hashes':[digest(trigger),digest(performance)],'compiler':version,
            'source_hashes':{n:raw_digest(s.encode()) for n,s in sources.items()},'release_eligible':False}
    (output/'build.json').write_bytes(canonical(result));(output/(entry+'.java')).write_text(template)
    return result


def run(build,requests,jdk):
    jar=Path(build['jar']);jdk,_=toolchain(jdk)
    if raw_digest(jar.read_bytes())!=build['jar_sha256']:raise LegalMathError('E_INTEGRITY')
    p=subprocess.run([str(jdk/'bin/java'),'-jar',str(jar)],input=b'\n'.join(canonical(r) for r in requests)+b'\n',
                     capture_output=True,check=True,timeout=60)
    values=[loads(line) for line in p.stdout.splitlines()]
    if len(values)!=len(requests):raise LegalMathError('E_INTEGRITY')
    return values
