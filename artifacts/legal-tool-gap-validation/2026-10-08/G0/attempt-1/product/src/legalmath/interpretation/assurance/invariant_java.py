"""Emit a Java API that evaluates every retained policy before aggregating."""
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from ...canonical import canonical, digest, raw_digest
from ...java.emit import emit, runtime_sources
from ...java.manifest import toolchain
from .invariant import validate_prepared


def build(prepared, output, jdk):
    validate_prepared(prepared)
    jdk, version = toolchain(jdk)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    name = 'Assured_' + prepared['set_hash'][:20]
    sources = runtime_sources(); lines = []
    for ident, row in prepared['alternatives'].items():
        if row['bundle'] is None:
            lines.append('outcomes.put('+json.dumps(ident)+', null);')
        else:
            policy, source = emit(row['bundle']); sources[policy+'.java'] = source
            lines.append('outcomes.put('+json.dumps(ident)+', project('+policy+
                         '.evaluate(snapshot, "selected.control", at, knownAt, "draft")));')
    source = '''package hk.legalmath;
import java.util.Map;
import java.util.LinkedHashMap;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
/** Conditional on every retained hypothesis; this API grants no release authority. */
public final class NAME {
    private NAME() {}
    public static final String SET_HASH = "SETHASH";
    public static final String SOURCE_HASH = "SOURCEHASH";
    private static Map<String,Object> project(Map<String,Object> result) {
        Map<String,Object> p = new LinkedHashMap<>();
        for (String key : new String[]{"status","type","value"})
            if (result.containsKey(key)) p.put(key,result.get(key));
        return p;
    }
    public static String evaluate(String snapshot, String sourceHash, String at, String knownAt) {
        return Json.write(evaluate(Json.map(Json.parse(snapshot)),sourceHash,at,knownAt));
    }
    public static Map<String,Object> evaluate(Map<String,Object> snapshot, String sourceHash, String at, String knownAt) {
        Map<String,Object> outcomes = new LinkedHashMap<>();
        String status = "SOURCE_CHANGED"; Object value = null;
        if (SOURCE_HASH.equals(sourceHash)) {
            EVALUATIONS
            boolean unencoded=false, unknown=false, allNA=true, same=true;
            Map<String,Object> first=null;
            for (Object item : outcomes.values()) {
                if (item==null) { unencoded=true; continue; }
                Map<String,Object> row=Json.map(item);
                String s=Json.str(row.get("status"));
                allNA=allNA && s.equals("OUT_OF_SCOPE");
                unknown=unknown || !(s.equals("TRUE") || s.equals("FALSE") || s.equals("OUT_OF_SCOPE"));
                if (first==null) first=row; else same=same && first.equals(row);
            }
            if (unencoded) status="UNENCODED_ALTERNATIVE";
            else if (allNA) status="INVARIANT_NOT_APPLICABLE";
            else if (unknown) status="UNKNOWN_OR_CONFLICT";
            else if (!same) status="INTERPRETATION_DISAGREEMENT";
            else if (first!=null && first.get("value") instanceof Boolean) {
                status="INVARIANT_KNOWN"; value=first.get("value");
            } else status="UNKNOWN_OR_CONFLICT";
        }
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("status",status); result.put("value",value); result.put("outcomes",outcomes);
        result.put("question_hash","QUESTIONHASH"); result.put("set_hash",SET_HASH);
        result.put("source_packet_hash",sourceHash); result.put("snapshot_hash",Json.hash(snapshot));
        result.put("conditional_on_retained_hypotheses",true); result.put("release_eligible",false);
        return result;
    }
    public static void main(String[] args) throws Exception {
        BufferedReader in=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));
        String line;
        while ((line=in.readLine())!=null) {
            Map<String,Object> r=Json.map(Json.parse(line));
            System.out.println(Json.write(evaluate(Json.map(r.get("snapshot")),Json.str(r.get("source_packet_hash")),
                Json.str(r.get("valid_at")),Json.str(r.get("known_at")))));
        }
    }
}
'''
    for key, value in {'NAME': name, 'SETHASH': prepared['set_hash'],
                       'SOURCEHASH': prepared['source_packet_hash'], 'QUESTIONHASH': digest(prepared['question']),
                       'EVALUATIONS': '\n            '.join(lines)}.items():
        source = source.replace(key, value)
    sources[name+'.java'] = source
    flags = ['--release','17','-encoding','UTF-8','-g:none','-Xlint:all','-Werror']
    with tempfile.TemporaryDirectory(prefix='legalmath-assured-') as td:
        stage = Path(td); classes = stage/'classes'; classes.mkdir()
        for filename, text in sources.items():
            (stage/filename).write_text(text)
        subprocess.run([str(jdk/'bin/javac'),*flags,'-d',str(classes),
                        *map(str, sorted(stage.glob('*.java')))],check=True,capture_output=True,timeout=60)
        jar = output/(name+'.jar')
        with zipfile.ZipFile(jar,'w',compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(classes.rglob('*.class')):
                info = zipfile.ZipInfo(path.relative_to(classes).as_posix(),(1980,1,1,0,0,0))
                info.external_attr=0o100644 << 16; archive.writestr(info,path.read_bytes())
    for filename, text in sources.items():
        (output/filename).write_text(text)
    manifest = {'set_hash': prepared['set_hash'], 'source_packet_hash': prepared['source_packet_hash'],
                'compiler': version, 'jar_sha256': raw_digest(jar.read_bytes()),
                'sources': {k: raw_digest(v.encode()) for k,v in sources.items()},
                'class_name': 'hk.legalmath.'+name, 'jar': str(jar), 'release_eligible': False}
    (output/'assured-build.json').write_bytes(canonical(manifest))
    return manifest


def run(build_manifest, requests, jdk):
    from ...errors import LegalMathError
    if raw_digest(Path(build_manifest['jar']).read_bytes()) != build_manifest['jar_sha256']:
        raise LegalMathError('E_INTEGRITY')
    result = subprocess.run([str(Path(jdk)/'bin/java'),'-cp',build_manifest['jar'],build_manifest['class_name']],
                            input=b'\n'.join(canonical(r) for r in requests)+b'\n',
                            capture_output=True,check=True,timeout=60)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    if len(rows) != len(requests):
        raise LegalMathError('E_INTEGRITY')
    return rows
