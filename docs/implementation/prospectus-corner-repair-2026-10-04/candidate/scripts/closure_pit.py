"""PIT challenges the real Java temporal selector used by generated policies."""
from pathlib import Path
import json
import os
import subprocess
import xml.etree.ElementTree as ET

from legalmath.ir.evaluate import evaluate
from legalmath.java.emit import emit, runtime_sources
from legalmath.interpretation.assurance.diversity import save

ROOT = Path(__file__).resolve().parents[1]
JDK = ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'


def run(out, cases, selected_bundle):
    src = out/'src'; classes = out/'classes'
    src.mkdir(parents=True); classes.mkdir()
    name, generated = emit(selected_bundle)
    for filename, text in {**runtime_sources(), name+'.java': generated}.items():
        (src/filename).write_text(text)
    rows = []
    for case in cases:
        expected = evaluate(**{k: case[k] for k in ('bundle', 'snapshot', 'rule_id', 'valid_at', 'known_at')})
        expected = {k: v for k, v in expected.items() if k not in ('engine_version', 'result_hash')}
        rows.append({**case, 'expected_result': expected,
                     'use_generated': case['bundle'] == selected_bundle})
    data = out/'cases.ndjson'
    data.write_text('\n'.join(json.dumps(c, sort_keys=True) for c in rows)+'\n')
    test = '''package hk.legalmath;
import org.junit.Test;
import static org.junit.Assert.*;
import java.nio.file.*;
import java.util.*;
public class RuntimeAssuranceTest {
 @Test public void intervalBoundaries() {
   String a="2026-01-01T00:00:00.000000Z", b="2026-01-02T00:00:00.000000Z";
   assertTrue(Policy.eligible(a,b,a));
   assertFalse(Policy.eligible(a,b,b));
   assertFalse(Policy.eligible(b,null,a));
   assertTrue(Policy.eligible(a,null,b));
 }
 @Test public void compiledAndDynamicConformance() throws Exception {
   for(String line:Files.readAllLines(Path.of(DATA))) {
     Map<String,Object> c=Json.map(Json.parse(line));
     String snapshot=Json.write(c.get("snapshot")), rule=Json.str(c.get("rule_id"));
     String at=Json.str(c.get("valid_at")), cutoff=Json.str(c.get("known_at"));
     String answer=Boolean.TRUE.equals(c.get("use_generated")) ? GENERATED.evaluate(snapshot,rule,at,cutoff,"draft")
       : new Policy(Json.write(c.get("bundle"))).evaluate(snapshot,rule,at,cutoff,"draft");
     Map<String,Object> actual=Json.map(Json.parse(answer));
     actual.remove("engine_version"); actual.remove("result_hash");
     assertEquals(Json.str(c.get("id")),Json.write(c.get("expected_result")),Json.write(actual));
   }
 }
}'''.replace('DATA', json.dumps(str(data.resolve()))).replace('GENERATED', name)
    (src/'RuntimeAssuranceTest.java').write_text(test)
    jars = sorted((ROOT/'.localresources/assurance-tools/jars').glob('*.jar'))
    cp = os.pathsep.join(map(str, [classes, *jars]))
    env = {**os.environ, 'JAVA_HOME': str(JDK), 'PATH': str(JDK/'bin')+os.pathsep+os.environ['PATH']}
    commands = []

    def execute(argv):
        index = len(commands); commands.append(argv)
        with (out/f'command-{index}.log').open('w') as log:
            result = subprocess.run(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        if result.returncode:
            raise ValueError('Actual-runtime PIT execution failed; see '+str(out/f'command-{index}.log'))

    execute([str(JDK/'bin/javac'), '--release', '17', '-g', '-cp', cp, '-d', str(classes),
             *map(str, sorted(src.glob('*.java')))])
    execute([str(JDK/'bin/java'), '-cp', cp, 'org.junit.runner.JUnitCore', 'hk.legalmath.RuntimeAssuranceTest'])
    # Enumerate the compiled class, so the bounded target cannot drift when a
    # new method is added. The rest of the runtime has separate targeted faults.
    signature = subprocess.check_output([str(JDK/'bin/javap'), '-p', '-classpath', str(classes),
                                         'hk.legalmath.Policy'], text=True)
    excluded = sorted({line.split('(')[0].split()[-1].rsplit('.', 1)[-1]
                       for line in signature.splitlines() if '(' in line} - {'eligible'})
    excluded = ['<init>' if n == 'Policy' else n for n in excluded]
    execute([str(JDK/'bin/java'), '-cp', cp, 'org.pitest.mutationtest.commandline.MutationCoverageReport',
             '--reportDir', str(out/'pit-report'), '--targetClasses', 'hk.legalmath.Policy',
             '--targetTests', 'hk.legalmath.RuntimeAssuranceTest', '--sourceDirs', str(src),
             '--classPath', ','.join(map(str, [classes, *jars])), '--excludedMethods', ','.join(excluded),
             '--outputFormats', 'XML', '--mutators', 'CONDITIONALS_BOUNDARY,NEGATE_CONDITIONALS,TRUE_RETURNS,FALSE_RETURNS',
             '--threads', '1', '--timestampedReports', 'false'])
    paths = list((out/'pit-report').rglob('mutations.xml'))
    if len(paths) != 1:
        raise ValueError('Unique mutation report missing')
    mutants = [{'status': m.attrib['status'], 'method': m.findtext('mutatedMethod'),
                'mutator': m.findtext('mutator'), 'description': m.findtext('description'),
                'killing_test': m.findtext('killingTest')} for m in ET.parse(paths[0]).getroot().findall('mutation')]
    passed = bool(mutants) and all(m['method'] == 'eligible' and m['status'] == 'KILLED' for m in mutants)
    result = {'status': 'PASS' if passed else 'FAIL', 'mutants': mutants, 'commands': commands,
              'reference_cases': len(cases), 'scope': 'Actual Policy.eligible temporal selector; all other methods excluded explicitly',
              'generated_policy': name, 'whole_runtime_mutation_coverage': False, 'release_eligible': False}
    save(out/'result.json', result)
    if not passed:
        raise ValueError('Material temporal runtime mutant survived or target drifted')
    return result
