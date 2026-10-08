"""Real Inspect and PIT execution on labelled synthetic challenges."""
from pathlib import Path
import json
import os
import subprocess
import xml.etree.ElementTree as ET

from legalmath.interpretation.assurance.diversity import save
from assurance_tool_preflight import BASE

ROOT=Path(__file__).resolve().parents[1]
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'


def inspect_cases(out):
    from inspect_ai import Task,eval
    from inspect_ai.dataset import Sample
    from inspect_ai.solver import solver
    from inspect_ai.scorer import scorer,Score,accuracy
    cases=[('exception','gift with fee-discount qualification','FALSE','TRUE'),
           ('type','gift linked to product type only','TRUE','FALSE'),
           ('unknown','classification evidence missing','UNKNOWN','FALSE'),
           ('polarity','true means prohibition applies','PROHIBITED','PERMITTED'),
           ('control','ordinary linked gift without exception','TRUE','TRUE'),
           ('missing','no proposer result','UNKNOWN','')]
    exposed=[]
    def public_proposer(public):
        if set(public)!={'id','input','controlled_response'}:raise ValueError('Unexpected proposer field')
        exposed.append({'id':public['id'],'input':public['input'],'metadata_keys':['controlled_response'],
                        'received_keys':sorted(public)})
        return public['controlled_response']
    @solver
    def fixed_proposer():
        async def solve(state,generate):
            # Only public scenario and controlled response are visible here.
            state.output.completion=public_proposer({'id':state.sample_id,'input':state.input_text,
                                                    'controlled_response':state.metadata['controlled_response']})
            return state
        return solve
    @scorer(metrics=[accuracy()])
    def reference_score():
        async def score(state,target):
            answer=state.output.completion
            return Score(value=1.0 if answer and answer==target.text else 0.0,answer=answer,
                         explanation='Synthetic target comparison; peer agreement is irrelevant.',
                         metadata={'missing':not bool(answer),'reference_basis':'declared synthetic fault challenge'})
        return score
    samples=[Sample(id=cid,input=text,target=target,metadata={'controlled_response':answer}) for cid,text,target,answer in cases]
    task=Task(dataset=samples,solver=fixed_proposer(),scorer=reference_score())
    logs=eval(task,model='mockllm/model',log_dir=str(out/'inspect-logs'),display='none',max_tasks=1)
    if len(logs)!=1 or logs[0].status!='success':raise ValueError('Inspect evaluation did not complete')
    actual={str(s.id):next(iter(s.scores.values())).value for s in logs[0].samples}
    expected={cid:float(bool(answer) and target==answer) for cid,text,target,answer in cases}
    if actual!=expected or any(r['metadata_keys']!=['controlled_response'] for r in exposed):
        raise ValueError('Hidden-reference or scoring contract failed')
    result={'status':'PASS','scores':actual,'expected':expected,'proposer_exposure':exposed,'new_model_calls':0,
            'shared_wrong_answers_rewarded':False,'missing_preserved':True,'reference':'synthetic, not legal adjudication',
            'live_model_accuracy_evaluated':False}
    save(out/'inspect-result.json',result);return result


def pit(out):
    work=out/'work';sources=work/'src';classes=work/'classes';sources.mkdir(parents=True);classes.mkdir()
    source='''package assurance;
public final class PilotControl {
  private PilotControl() {}
  public static boolean prohibited(boolean gift, boolean discount, boolean specific, boolean typeLink) {
    return gift && !discount && (specific || typeLink);
  }
  public static boolean syntheticThreshold(int months) { return months >= 6; }
}
'''
    tests='''package assurance;
import org.junit.Test;
import static org.junit.Assert.*;
public class PilotControlTest {
  @Test public void allKnownGiftCases() {
    for(int mask=0; mask<16; mask++) {
      boolean expected = mask==5 || mask==9 || mask==13;
      assertEquals("fixture "+mask,expected,PilotControl.prohibited((mask&1)!=0,(mask&2)!=0,(mask&4)!=0,(mask&8)!=0));
    }
  }
  @Test public void thresholdBoundary() {
    assertFalse(PilotControl.syntheticThreshold(5));
    assertTrue(PilotControl.syntheticThreshold(6));
    assertTrue(PilotControl.syntheticThreshold(7));
  }
}
'''
    (sources/'PilotControl.java').write_text(source);(sources/'PilotControlTest.java').write_text(tests)
    # Keep reviewable source beside the report; work classes are rebuildable.
    (out/'PilotControl.java').write_text(source);(out/'PilotControlTest.java').write_text(tests)
    jars=sorted((BASE/'jars').glob('*.jar'));cp=os.pathsep.join(map(str,[classes,*jars]))
    commands=[
        [str(JDK/'bin/javac'),'--release','17','-g','-cp',cp,'-d',str(classes),str(sources/'PilotControl.java'),str(sources/'PilotControlTest.java')],
        [str(JDK/'bin/java'),'-cp',cp,'org.junit.runner.JUnitCore','assurance.PilotControlTest'],
        [str(JDK/'bin/java'),'-cp',cp,'org.pitest.mutationtest.commandline.MutationCoverageReport',
         '--reportDir',str(out/'pit-report'),'--targetClasses','assurance.PilotControl','--targetTests','assurance.PilotControlTest',
         '--sourceDirs',str(sources),'--classPath',','.join(map(str,[classes,*jars])),
         '--outputFormats','XML','--mutators','CONDITIONALS_BOUNDARY,NEGATE_CONDITIONALS,TRUE_RETURNS,FALSE_RETURNS',
         '--threads','1','--timestampedReports','false']]
    for i,argv in enumerate(commands):
        with (out/f'pit-command-{i}.log').open('w') as log:
            proc=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180,
                                env={**os.environ,'JAVA_HOME':str(JDK),'PATH':str(JDK/'bin')+os.pathsep+os.environ['PATH']})
        if proc.returncode:raise ValueError('Java/PIT command failed; see '+str(out/f'pit-command-{i}.log'))
    paths=list((out/'pit-report').rglob('mutations.xml'))
    if len(paths)!=1:raise ValueError('Missing unique PIT mutation report')
    rows=[]
    for m in ET.parse(paths[0]).getroot().findall('mutation'):
        rows.append({'status':m.attrib['status'],'detected':m.attrib['detected'],
                     'mutator':m.findtext('mutator'),'line':m.findtext('lineNumber'),
                     'method':m.findtext('mutatedMethod'),'description':m.findtext('description')})
    families={r['mutator'].rsplit('.',1)[-1] for r in rows}
    required={'ConditionalsBoundaryMutator','NegateConditionalsMutator'}
    passed=bool(rows) and required<=families and all(r['status']=='KILLED' for r in rows)
    result={'status':'PASS' if passed else 'FAIL','mutants':rows,'commands':commands,
            'scope':'Pilot Boolean prohibition and synthetic threshold; generated Java covered separately in regression',
            'equivalent_mutants_assumed':False,'legal_correctness_established':False}
    save(out/'pit-result.json',result)
    if not passed:raise ValueError('Required material PIT mutants survived or were not generated')
    return result


def run(out):
    out.mkdir(parents=True,exist_ok=False)
    inspected=inspect_cases(out);mutations=pit(out)
    result={'engineering_status':'PASS','inspect':inspected,'pit':mutations,'new_model_calls':0,'release_eligible':False}
    save(out/'result.json',result);return result
