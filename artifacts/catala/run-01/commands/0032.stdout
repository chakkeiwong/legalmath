"""Portable draft Java-host package; release authorization is deliberately external."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
from ..canonical import canonical,digest,loads,raw_digest
from ..errors import LegalMathError
from ..ir.trace import verify_result
from .manifest import build_candidate,verify_candidate,toolchain


def prepare(bundle,cases,sources,out,jdk):
    out=Path(out)
    if out.exists():raise LegalMathError('E_IDEMPOTENCY')
    # Raw source commitments must actually be present in the package.
    hashes={raw_digest(data) for data in sources.values()}
    if not {s['raw_sha256'] for s in bundle['source_spans']}<=hashes:raise LegalMathError('E_REFERENCE')
    out.mkdir(parents=True)
    build=build_candidate(bundle,out/'policy',jdk);verify=verify_candidate(build,cases,jdk)
    for h,data in ((raw_digest(data),data) for data in sources.values()):
        (out/'sources').mkdir(exist_ok=True);(out/'sources'/(h+'.bin')).write_bytes(data)
    clazz=build['class_name']
    if not re.fullmatch(r'hk\.legalmath\.Policy_[0-9a-f]{20}',clazz):raise LegalMathError('E_INTEGRITY')
    host='''import java.nio.file.Files;
import java.nio.file.Path;
public final class LegalMathHost {
  private LegalMathHost() {}
  public static void main(String[] args) throws Exception {
    if(args.length!=3) throw new IllegalArgumentException("snapshot, rule, UTC assessment time required");
    String snapshot=Files.readString(Path.of(args[0]));
    System.out.println(POLICY.evaluate(snapshot,args[1],args[2],args[2],"draft"));
  }
}
'''.replace('POLICY',clazz)
    (out/'LegalMathHost.java').write_text(host);(out/'host-classes').mkdir()
    jdk,_=toolchain(jdk)
    subprocess.run([str(jdk/'bin/javac'),'--release','17','-Xlint:all','-Werror','-cp',build['jar'],
        '-d',str(out/'host-classes'),str(out/'LegalMathHost.java')],check=True,capture_output=True,timeout=60)
    (out/'bundle.json').write_bytes(canonical(bundle));(out/'cases.json').write_bytes(canonical(cases))
    metadata={'version':'host-package.v1','bundle_hash':digest(bundle),'class_name':clazz,
              'jar':str(Path(build['jar']).relative_to(out)),'source_urls':{url:raw_digest(data) for url,data in sources.items()},
              'host_sha256':raw_digest((out/'host-classes/LegalMathHost.class').read_bytes()),
              'verification':verify,'mode':'draft','release_eligible':False,'institution_accepted':False}
    (out/'package.json').write_bytes(canonical(metadata))
    (out/'README.txt').write_text('Draft Java 17 integration package. Verify manifest bytes before loading.\n'
        'LegalMathHost accepts snapshot JSON file, exact rule ID, and UTC assessment time.\n'
        'Returns typed status/value/trace. UNKNOWN, CONFLICT and ERROR cannot authorize a transaction.\n'
        'Institution staging, fact mappings, service identity and release configuration remain required.\n')
    manifest={'files':{str(p.relative_to(out)):raw_digest(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}}
    (out/'manifest.json').write_bytes(canonical(manifest));return metadata


def verify_package(directory):
    directory=Path(directory).resolve();manifest=loads((directory/'manifest.json').read_bytes())
    if set(manifest['files'])!={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name!='manifest.json'}:
        raise LegalMathError('E_INTEGRITY')
    for name,sha in manifest['files'].items():
        p=(directory/name).resolve()
        if not p.is_relative_to(directory) or raw_digest(p.read_bytes())!=sha:raise LegalMathError('E_INTEGRITY')
    metadata=loads((directory/'package.json').read_bytes());bundle=loads((directory/'bundle.json').read_bytes())
    if digest(bundle)!=metadata['bundle_hash'] or metadata['release_eligible'] is not False:raise LegalMathError('E_INTEGRITY')
    if 'output_descriptor' in metadata:
        from ..interpretation.outputs import validate_descriptor
        from ..interpretation.search.formal import bundle as compile_reading
        interpretation=loads((directory/'interpretation.json').read_bytes())
        reading,packet=interpretation['reading'],interpretation['source_packet']
        validate_descriptor(metadata['output_descriptor'],reading,packet['selected_slice'])
        if compile_reading(reading,packet,bundle['valid_from'])!=bundle:
            raise LegalMathError('E_INTEGRITY',details='Output meaning belongs to a different generated program')
    return metadata,bundle


def prepare_interpretation(reading,packet,cases,sources,out,jdk,at):
    """Carry a proposed question and output meaning with its exact draft program."""
    from ..interpretation.outputs import descriptor
    from ..interpretation.search.formal import bundle as compile_reading
    meaning=descriptor(reading,packet['selected_slice'])
    compiled=compile_reading(reading,packet,at)
    metadata=prepare(compiled,cases,sources,out,jdk);out=Path(out)
    metadata['output_descriptor']=meaning
    (out/'interpretation.json').write_bytes(canonical({'reading':reading,'source_packet':packet}))
    (out/'package.json').write_bytes(canonical(metadata))
    with (out/'README.txt').open('a') as stream:
        stream.write('The package output_descriptor names the proposed legal question and meaning.\n'
                     'TRUE_IS_SATISFIED identifies a predicate; it is not compliance, prohibition or licence possession.\n'
                     'The executable result retains status/type/value; consumers must retain this associated descriptor.\n')
    manifest={'files':{str(p.relative_to(out)):raw_digest(p.read_bytes()) for p in sorted(out.rglob('*'))
                      if p.is_file() and p.name!='manifest.json'}}
    (out/'manifest.json').write_bytes(canonical(manifest))
    verify_package(out)
    return metadata


def run(directory,snapshot,rule_id,at,jdk):
    directory=Path(directory);metadata,bundle=verify_package(directory);jdk,_=toolchain(jdk)
    with tempfile.TemporaryDirectory(prefix='legalmath-host-') as td:
        td=Path(td);(td/'snapshot.json').write_bytes(canonical(snapshot))
        # The executed bytes are copied from the checked package; the caller does
        # not depend on a mutable active-release symlink during Java evaluation.
        jar=directory/metadata['jar'];jar_bytes=jar.read_bytes()
        expected=metadata['verification']['jar_sha256']
        if raw_digest(jar_bytes)!=expected:raise LegalMathError('E_INTEGRITY')
        (td/'policy.jar').write_bytes(jar_bytes)
        host=(directory/'host-classes/LegalMathHost.class').read_bytes()
        if raw_digest(host)!=metadata['host_sha256']:raise LegalMathError('E_INTEGRITY')
        (td/'LegalMathHost.class').write_bytes(host)
        result=subprocess.run([str(jdk/'bin/java'),'-cp',str(td)+os.pathsep+str(td/'policy.jar'),
            'LegalMathHost',str(td/'snapshot.json'),rule_id,at],check=True,capture_output=True,timeout=60)
        value=loads(result.stdout);verify_result(bundle,snapshot,rule_id,value)
        return value
