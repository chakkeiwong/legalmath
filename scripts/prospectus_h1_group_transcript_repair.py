"""Correct two manual group-directory labels; retain failed 040 evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prospectus_h1_related_validator_repair as prior
from scripts import prospectus_h1_group_structure as failed
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-group-transcript-repair-404'
HERE = BASE / 'attempt-041'
SELF = 'scripts/prospectus_h1_group_transcript_repair.py'
PLAN = 'docs/plans/prospectus-h1-group-transcript-repair-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-group-structure.v18'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (61,62,63,64,65,66)
TESTS = prior.TESTS
DEPENDENCIES = {'render': [], 'source': ['render'], 'implement': ['source'],
    'tests': ['implement'], 'ordinary': ['tests'], 'controls': ['ordinary'],
    'package': ['controls'], 'installed': ['package'], 'coverage': []}


def authority():
    sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def costs(reserve=0):
    start = read(PREP/'accounting-start.json')
    paths = {p for d in (PREP, HERE) if d.exists() for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN, SELF, PRODUCTION))
    paths.add(AUTH/'revisions/0404.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 126*1024**2 and seconds < 1200}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==403 and not PREP.exists() and not HERE.exists(),'Fresh403 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==40,'Retain40attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','039 must pass')
    require(read(failed.HERE/'result.json')['status']=='FAIL' and
            not (failed.HERE/'stages/implement').exists(),'Retain failed 040 without implementation')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40):
        folder=BASE/f'attempt-{n:03d}'; manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items(): require(sha(folder/name)==h,'Changed original '+name)
    previous=failed.costs()
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    preflight=read(Path('/tmp/prospectus-group-repair-preflight.json'))
    require(preflight['status']=='PASS' and preflight['manual_image_review'],'Complete corrected source preflight required')
    save(PREP/'mapping-preflight.json',preflight)
    save(PREP/'commands/mapping-preflight.json',{'wall_seconds':preflight['seconds'],
        'command':'Full corrected manual source check, original graph and deliberate corruption refusals'})
    (PREP/'baseline').mkdir(); shutil.copyfile(ROOT/PRODUCTION,PREP/'baseline/statement_cells.py')
    production=common.production();save(PREP/'baseline/production.json',production)
    protected.update({n:h for n,h in read(failed.PREP/'freeze.json')['bindings'].items() if n!=PRODUCTION})
    names=[PLAN,SELF,prior.SELF,failed.SELF,rel(failed.HERE/'image-transcript.json'),rel(failed.HERE/'SOURCE-REVIEW.md'),rel(failed.HERE/'images.json'),rel(failed.HERE/'FAILURE-REVIEW.md'),'pyproject.toml',*TESTS,rel(PREP/'mapping-preflight.json'),rel(PREP/'baseline/statement_cells.py'),
        rel(PREP/'baseline/production.json'),rel(prior.HERE/'ordinary.json.gz'),
        rel(prior.HERE/'source-units.json'),rel(prior.HERE/'reading.json'),
        rel(prior.HERE/'image-transcript.json'),rel(BASE/'attempt-028/COVERAGE-CORRECTION.md'),
        rel(prior.HERE/'images.json'),rel(prior.HERE/'registry-entry.json'),rel(BASE/'attempt-028/retained-risk-coverage-correction.json')]
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in production.items() if n!=PRODUCTION})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale inherited binding')
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'Once after reviewed source and candidate freeze'})
    config=read(prior.PREP/'config.json'); require(sha(config['package_python'])==config['python_sha256'],'Build interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=404
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Correct two manual Note 1 labels and deliver group disclosures; preserve complete 039 and failed 040')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':1200,'control_seconds':60,'new_bytes':128*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['group_structure_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=41
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=404
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='039 related-party disclosures retained; Note 1 and wider source/authority remain.',
                next_action='Correct 040 manual labels and execute 041 source/normal/installed delivery; retain 039 and all failure evidence.',
                stop_condition='Retain 40 admissions and permit attempt 41; 1200+60 seconds and 128 MiB new; no unchanged retry; retain cumulative costs/failures.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in
        (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast=costs()['new_bytes']+2*len(raw)+3*source_bytes+10*1024**2
    require(forecast<126*1024**2,'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Deliver Note 1; preserve complete 039','Preserve verified original composition including OCR risk tables','Retain 40 admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original date/column geometry,conditional clauses and actual consumers;hashes and arithmetic do not prove legal or financial truth'},
        'evidence_contract':{'question':'Do group structure, economic interests, consolidation methods and movement amounts reach the answer with source limits intact?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':40,'new_maximum':41,
            'retained_attempts':attempts,'reason':'Changed correction of two manual accents; preserve exact matching and all prior failures and costs',
            'next_discriminating_check':'Control and significant influence distinguished from economic-interest thresholds; complete original entity and movement tables',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_group_transcript_repair','prepare']})
    return {'status':'PREPARED','revision':404,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=360):
    require(costs(1024**2)['execution_allowed'], 'Resource reservation exhausted')
    target = HERE/'commands'; target.mkdir(exist_ok=True); tick = time.monotonic(); result = None; error = None
    try:
        with (target/(name+'.log')).open('x') as stream:
            result = subprocess.run(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout,
                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
                     'PYTHONNOUSERSITE': '1', 'PYTHONPATH': str(ROOT/'src')+os.pathsep+str(ROOT),
                     'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'})
        require(result.returncode==0, 'Inspect retained '+name+'.log')
    except Exception as exc: error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(target/(name+'.json'), {'command': argv, 'wall_seconds': time.monotonic()-tick,
        'exit_code': None if result is None else result.returncode, 'error': error})
    require(error is None, 'Command failed: '+name+': '+str(error))
    require(costs()['execution_allowed'], 'Post-command resource limit')


DIRECTORY_MAP = {62: [[3, [12, 13, 14, 7], []], [15, [16, 17, 18, 19, 20, 21], []], [22, [23, 24, 25, 26, 27, 28], []], [29, [30, 31, 32, 33, 34, 56], [55]], [35, [36, 37, 38, 39, 40, 57], []], [41, [42, 43, 44, 45, 46, 47], []], [48, [49, 50, 51, 52, 53, 54], []], [58, [59, 60, 61, 62, 63, 64], []], [65, [66, 67, 68, 69, 70, 71], []], [72, [73, 74, 75, 76, 77, 78], []], [79, [80, 81, 82, 83, 84, 85], []], [86, [87, 88, 89, 90, 91, 92], []], [93, [94, 95, 96, 97, 98, 99], []], [100, [101, 102, 103, 104, 105, 106], []], [107, [108, 109, 110, 111, 112, 113], []], [114, [115, 116, 117, 118, 119, 120], []], [121, [122, 123, 124, 125, 126, 127], []], [128, [129, 130, 131, 132, 133, 134], []], [135, [136, 137, 138, 139, 140, 141], []], [142, [143, 144, 145, 146, 147, 148], []], [149, [150, 151, 152, 153, 154, 155], []], [156, [157, 158, 159, 160, 161, 162], []], [163, [164, 165, 166, 167, 168, 169], []], [170, [171, 172, 173, 174, 175, 176], []], [177, [178, 179, 180, 181, 182, 183], []], [185, [186, 187, 188, 189, 190, 184], []], [191, [192, 193, 194, 195, 196, 197], []], [198, [199, 200, 201, 202, 203, 204], []], [205, [206, 207, 208, 209, 210, 211], []], [212, [213, 214, 215, 216, 217, 218], []], [219, [220, 221, 222, 223, 224, 225], []], [226, [227, 228, 229, 230, 231, 232], []], [233, [234, 235, 236, 237, 238, 239], []], [240, [241, 242, 243, 244, 245, 246], []], [247, [248, 249, 250, 251, 252, 253], []], [254, [255, 256, 257, 258, 259, 260], []], [261, [262, 263, 264, 265, 266, 267], []], [268, [269, 270, 271, 272, 273, 274], []], [275, [276, 277, 278, 279, 280, 281], []], [282, [283, 284, 285, 286, 287, 288], []], [289, [290, 291, 292, 293, 294, 295], []], [296, [297, 298, 299, 300, 301, 302], []], [303, [304, 305, 306, 307, 308, 309], []], [310, [311, 312, 313, 314, 315, 316], []], [317, [318, 319, 320, 321, 322, 323], []], [324, [325, 326, 327, 328, 329, 330], []], [331, [332, 333, 334, 335, 336, 337], []], [338, [339, 340, 341, 342, 344, 345], [343]], [346, [347, 348, 349, 350, 352, 353], [351]], [354, [355, 356, 357, 358, 360, 361], [359]]], 63: [[3, [11, 12, 13, 14, 15, 16], []], [51, [17, 18, 19, 20, 21, 22], []], [23, [24, 25, 26, 27, 28, 29], []], [30, [31, 32, 33, 34, 35, 36], []], [37, [38, 39, 40, 41, 42, 43], []], [44, [45, 46, 47, 48, 49, 50], []], [52, [53, 54, 55, 56, 57, 58], []], [59, [60, 61, 62, 63, 64, 65], []], [66, [67, 68, 69, 70, 71, 84], [83]], [79, [72, 73, 74, 75, 76, 77], []], [80, [85, 86, 87, 88, 89, 78], []], [81, [90, 91, 92, 93, 94, 95], []], [82, [96, 97, 98, 99, 100, 101], []], [102, [103, 104, 105, 106, 107, 108], []], [109, [110, 111, 112, 113, 114, 115], []], [128, [116, 117, 118, 119, 120, 121], []], [129, [122, 123, 124, 125, 126, 127], []], [130, [131, 132, 133, 134, 135, 136], []], [137, [138, 139, 140, 141, 142, 143], []], [144, [145, 146, 147, 148, 149, 150], []], [151, [152, 153, 154, 155, 156, 157], []], [158, [159, 160, 161, 162, 163, 164], []], [165, [166, 167, 168, 169, 170, 171], []], [179, [173, 174, 175, 176, 177, 172], []], [178, [180, 181, 182, 183, 184, 185], []], [186, [187, 188, 189, 190, 191, 192], []], [193, [194, 195, 196, 197, 198, 199], []], [200, [201, 202, 203, 204, 205, 206], []], [207, [208, 209, 210, 211, 212, 213], []], [214, [215, 216, 217, 218, 219, 220], []], [221, [222, 223, 224, 225, 226, 227], []], [228, [229, 230, 231, 232, 233, 240], []], [234, [235, 236, 237, 238, 239, 242], [241]], [243, [244, 245, 246, 247, 248, 306], []], [249, [250, 251, 252, 253, 254, 255], []], [256, [257, 258, 259, 260, 261, 262], []], [263, [264, 265, 266, 267, 268, 269], []], [303, [270, 271, 272, 273, 274, 275], []], [304, [276, 277, 278, 279, 280, 281], []], [305, [282, 283, 284, 285, 286, 287], []], [288, [289, 290, 291, 292, 293, 294], []], [295, [296, 297, 298, 299, 300, 301], []], [307, [308, 309, 310, 311, 312, 302], []], [313, [314, 315, 316, 317, 318, 319], []], [320, [321, 322, 323, 324, 325, 326], []], [327, [328, 329, 330, 331, 332, 333], []], [334, [335, 336, 337, 338, 339, 340], []], [342, [343, 344, 345, 346, 347, 341], []], [348, [349, 350, 351, 352, 353, 354], []], [355, [356, 357, 358, 359, 360, 361], []]], 64: [[2, [10, 11, 12, 13, 14, 15], []], [16, [17, 18, 19, 20, 21, 22], []], [23, [24, 25, 26, 27, 28, 29], []], [30, [31, 32, 33, 34, 35, 36], []], [37, [38, 39, 40, 41, 42, 43], []], [44, [45, 46, 47, 48, 49, 50], []], [58, [51, 52, 53, 54, 55, 56], []], [59, [60, 61, 62, 63, 64, 57], []], [65, [66, 67, 68, 69, 70, 71], []], [72, [73, 74, 75, 76, 77, 78], []], [79, [80, 81, 82, 83, 84, 98], [97]], [85, [86, 87, 88, 89, 90, 99], []], [91, [92, 93, 94, 95, 96, 101], [100]], [102, [103, 104, 105, 106, 107, 108], []], [109, [110, 111, 112, 113, 114, 115], []], [117, [118, 119, 120, 121, 122, 116], []], [123, [124, 125, 126, 127, 128, 129], []], [130, [131, 132, 133, 134, 135, 137], [136]], [138, [139, 140, 141, 142, 143, 151], []], [144, [145, 146, 147, 148, 149, 152], [150]], [153, [154, 155, 156, 157, 158, 160], [159]], [161, [162, 163, 164, 165, 166, 173], []], [167, [168, 169, 170, 171, 172, 174], []], [175, [176, 177, 178, 179, 180, 181], []], [182, [183, 184, 185, 186, 187, 188], []], [189, [190, 191, 192, 193, 194, 195], []], [196, [197, 198, 199, 200, 201, 202], []], [203, [204, 205, 206, 207, 208, 209], []], [210, [211, 212, 213, 214, 215, 216], []], [217, [218, 219, 220, 221, 222, 223], []], [224, [225, 226, 227, 228, 229, 230], []], [231, [232, 233, 234, 235, 236, 237], []], [238, [239, 240, 241, 242, 243, 244], []], [245, [246, 247, 248, 249, 250, 251], []], [252, [253, 254, 255, 256, 257, 258], []], [259, [260, 261, 262, 263, 264, 265], []], [266, [267, 268, 269, 270, 271, 272], []], [273, [274, 275, 276, 277, 278, 279], []], [280, [281, 282, 283, 284, 285, 286], []], [287, [288, 289, 290, 291, 292, 293], []], [294, [295, 296, 297, 298, 299, 300], []], [301, [302, 303, 304, 305, 306, 307], []]]}

def corrected_transcript():
    transcript=deepcopy(read(failed.HERE/'image-transcript.json'))
    changes=[(19,'Espírito Santo Investimentos, Ltda','Espirito Santo Investimentos, Ltda'),
             (45,'Espírito Santo International Asset Management','Espirito Santo International Asset Management')]
    for index,old,new in changes:
        require(transcript['directory'][1]['rows'][index][0]==old,'Unexpected failed transcript')
        transcript['directory'][1]['rows'][index][0]=new
    transcript['corrections']=[{'page':63,'row_zero_based':i,'from':a,'to':b} for i,a,b in changes]
    transcript['correction_basis']='Original-resolution page 63: two printed names omit the manually added accent; all raw source strings and exact matching retained'
    return transcript


def render_worker():
    require(sha(BASE/'attempt-001/interim.pdf')==PDF,'Wrong original PDF')
    require(read(failed.HERE/'result.json')['status']=='FAIL','Retain failed 040')
    require(not (failed.HERE/'stages/implement').exists(),'040 unexpectedly implemented')
    images=read(failed.HERE/'images.json')
    for item in images: require(sha(ROOT/item['path'])==item['sha256'],'Retained image changed')
    save(HERE/'images.json',images)
    save(HERE/'image-transcript.json',corrected_transcript())
    (HERE/'SOURCE-REVIEW.md').write_text((failed.HERE/'SOURCE-REVIEW.md').read_text()+
        '\n\n## Two corrected manual accents\n\n'
        'The printed page-63 company labels Espirito Santo Investimentos, Ltda and '
        'Espirito Santo International Asset Management omit the accent introduced '
        'during manual transcription. Only these two characters are corrected. '
        'The original failed transcript, images and failure remain sealed. '
        'The complete corrected source check and original-graph/adverse preflight '
        'passed before admission; actual ordinary/installed checks remain required.\n')
    save(HERE/'source-reuse.json',{'source_attempt':rel(failed.HERE),'images':images,
        'original_transcript_sha256':sha(failed.HERE/'image-transcript.json'),
        'corrected_transcript_sha256':sha(HERE/'image-transcript.json'),'new_rendering':False})


def original_units():
    return sorted([u for u in read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES],key=lambda u:(u['page'],u['order'],u['id']))


def combined_units(units):
    old=prior.combined_units(read(prior.HERE/'source-units.json'))
    require(len(old)==5026,'Wrong 039 baseline')
    by_id={u['id']:u for u in old}
    require(not set(by_id).intersection(u['id'] for u in units),'Unexpected source overlap')
    by_id.update({u['id']:u for u in units})
    require(len(by_id)==6288,'Wrong combined occurrences')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))


def normal(value):
    return ''.join(value.split())


def percent(value):
    from decimal import Decimal
    text=normal(value).replace('a)','').replace('b)','')
    require(text.endswith('%'),'Wrong percentage token')
    result=Decimal(text[:-1].replace(',','.'))
    require(0<=result<=100,'Percentage outside source range')
    return format(result,'.2f')


def group_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(p,i):
        u=lookup[p,i];return {'id':u['id'],'quote':u['raw']}
    def qs(p,a,b):return [q(p,i) for i in range(a,b+1)]
    directory=[]
    for p,specs in DIRECTORY_MAP.items():
        rows=[]
        for label,fields,markers in specs:
            values=[q(p,i) for i in fields]
            pct=percent(values[4]['quote']) if len(fields)==6 else None
            method=normal(values[5]['quote']) if len(fields)==6 else None
            require(method in ('Fullconsolidation','Equitymethod',None),'Unknown source method')
            marker_quotes=[q(p,i) for i in markers]
            marker='a' if any('a)' in x['quote'] for x in values+marker_quotes) else 'b' if any('b)' in x['quote'] for x in values+marker_quotes) else None
            rows.append({'label_source':q(p,label),'fields':values,'marker_sources':marker_quotes,
                'established':int(normal(values[0]['quote'])),
                'acquired':None if normal(values[1]['quote'])=='-' else int(normal(values[1]['quote'])),
                'economic_interest_percent':pct,
                'method':{'Fullconsolidation':'FULL','Equitymethod':'EQUITY',None:None}[method],
                'footnote':marker,'label_x':lookup[p,label]['bbox'][0],
                'missing_interest_and_method':'NOT_PRINTED' if len(fields)==4 else None})
        headers={62:[2,4,5,6,8,9,10,11],63:[2,4,5,6,7,8,9,10],64:[1,3,4,5,6,7,8,9]}[p]
        directory.append({'page':p,'section':'DIRECT_BANK_TABLE' if p==62 else 'SUBGROUP_TABLE',
            'headers':[q(p,i) for i in headers],'rows':rows,
            'immediate_legal_parent_inferred':False,'repeated_entities_merged':False})
    def cell(i):
        item=q(66,i);token=normal(item['quote'])
        value=None if token=='-' else -int(token[1:-1]) if token.startswith('(') else int(token)
        return {**item,'value':value,'unit':'EUR thousands','status':'UNKNOWN' if value is None else 'SOURCE_NUMBER'}
    movement_rows=[]
    for label,indices,inferred in [(8,[34,36,38,40,42,44,46],None),
        (None,[35,37,39,41,43,45,47],'SUBSIDIARIES TOTAL (unlabelled)')]+[
        (10+i,[a+i for a in (48,62,76,90,104,118,132)],None) for i in range(13)]+[
        (None,[61,75,89,103,117,131,145],'ASSOCIATES TOTAL (unlabelled)'),
        (None,list(range(146,153)),'TOTAL (unlabelled)')]:
        movement_rows.append({'label_sources':[] if label is None else [q(66,label)],
            'label':inferred,'cells':[cell(i) for i in indices]})
    clauses=[('activity-and-authorisation',61,5,8),('history',61,9,13),('listing',61,14,15),
        ('parent-consolidation',61,16,18),('branches',61,19,21),('table-scope',61,22,24),
        ('control-footnote',64,308,309),('influence-footnote',64,310,313),
        ('special-purpose-entities',65,1,2),('period-change-context',65,3,6),
        ('aman-acquisition',65,7,10),('associates-context',65,11,12),('nanium',65,13,15),
        ('auvisa',65,16,17),('mrn',65,18,20),('aenor-ascendi',65,21,23),
        ('aquaspy-exclusion',65,24,27),('unicre-influence',65,28,33),
        ('movement-period',66,1,2),('capital-increase-footnote',66,153,153)]
    return {'version':'bes-group-structure-reading.v1',
        'source_groups':[{'page':p,'sources':[q(p,u['order']) for u in units if u['page']==p]} for p in PAGES],
        'directory':directory,
        'movements':{'period':'SIX_MONTHS_ENDED_2010-06-30','unit_source':q(66,3),
            'columns':['Acquisition price','Other investments (a)','Acquisitions total','Sale price',
                       'Other reimbursements (a)','Disposals total','Gains/(losses) from sales/disposals'],
            'column_sources':[qs(66,5,6),qs(66,23,24),[q(66,26)],[q(66,29)],qs(66,27,28),[q(66,33)],qs(66,30,32)],
            'group_sources':[q(66,4),q(66,25),q(66,7),q(66,9)],'rows':movement_rows},
        'clauses':[{'key':k,'sources':qs(p,a,b)} for k,p,a,b in clauses],
        'reported_interpretation':{
            'control':'Full consolidation can occur below 50 percent economic interest; footnote (a) attributes this to control',
            'influence':'Equity method can occur below 20 percent economic interest; footnote (b) attributes this to significant influence',
            'aman':'40 percent acquired in April 2010; report attributes full consolidation to management control; narrative EUR 40.3 million and movement EUR 40269 thousand remain distinct',
            'unicre':'Additional 8.41 percent raises holding to 17.50 percent; significant influence and first equity-method application; reported revaluation gain EUR 8260 thousand',
            'aquaspy':'Report says no longer consolidated in June 2010 after shareholding change and loss of control',
            'movement_footnote':'Other investments and reimbursements marked (a) refer to capital increase; negative reimbursements retain their printed sign',
            'table_scope':'Opening text says at least 20 percent with control or influence, while tables explicitly include smaller economic interests explained by footnote (b)',
            'legal_status':'HISTORICAL_REPORT_ASSERTIONS_NOT_VERIFIED_RULES'},
        'distinctions':{k:False for k in ('economic_interest_equals_direct_voting_power',
            'majority_required_for_full_consolidation','below_twenty_always_excluded',
            'consolidation_proves_guarantee','current_authorisation_verified','current_control_verified',
            'reported_ifrs_treatment_verified','identical_names_establish_identity','dash_means_zero',
            'rounded_narrative_equals_exact_movement','acquisition_total_is_purchase_price')},
        'dependency_resolution':{'note1_source_delivered':True,'note41_original_unresolved_flag_retained':True,
            'all_group_relationships_legally_proven':False,'source_authority_or_incorporation_resolved':False}}


def source_check(reading,units,transcript):
    require(len(units)==len({u['id'] for u in units})==1262,'Complete 1262 occurrences required')
    lookup={u['id']:u for u in units};s=reading['group_structure_evidence']
    require(all(u['visible'] and u['source_sha256']==PDF and u['page'] in PAGES for u in units),'Changed source')
    def refs(value):
        found=[]
        if isinstance(value,dict):
            if 'id' in value and 'quote' in value:
                require(value['id'] in lookup and value['quote']==lookup[value['id']]['raw'],'Changed source quote')
                found.append(value['id'])
            for k,v in value.items():
                if k not in ('id','quote'):found+=refs(v)
        elif isinstance(value,list):
            for v in value:found+=refs(v)
        return found
    refs(s);require(set(refs(s['source_groups']))==set(lookup),'Incomplete original pages')
    mapped=[];total_rows=0
    require(len(s['directory'])==len(transcript['directory'])==3,'Missing directory table')
    for table,manual in zip(s['directory'],transcript['directory']):
        same(table['page'],manual['page'],'Wrong directory page')
        require(len(table['rows'])==len(manual['rows']),'Directory row count differs')
        for row,typed in zip(table['rows'],manual['rows']):
            require(normal(typed[0]).casefold() in normal(row['label_source']['quote']).casefold(),f'Wrong company label on page {table["page"]}: {typed[0]!r} versus {row["label_source"]["quote"]!r}')
            values=[row[k] for k in ('established','acquired','economic_interest_percent','method','footnote')]
            same(values,typed[1:],'Wrong company attributes')
            boxes=[lookup[q['id']]['bbox'] for q in [row['label_source'],*row['fields']]]
            require(all(a[2]<b[0] for a,b in zip(boxes,boxes[1:])) and
                max(b[1] for b in boxes)-min(b[1] for b in boxes)<2.8,'Wrong company geometry')
            require(row['label_x']==boxes[0][0],'Lost source indentation')
            require(len(row['fields'])==(4 if row['missing_interest_and_method']=='NOT_PRINTED' else 6),'Wrong directory fields')
            for marker in row['marker_sources']:
                require(abs(lookup[marker['id']]['bbox'][1]-boxes[0][1])<2.8,'Wrong footnote association')
            mapped+=refs(row);total_rows+=1
        require(not table['immediate_legal_parent_inferred'] and not table['repeated_entities_merged'],'Unsupported entity inference')
    expected={u['id'] for u in units if u['page'] in (62,63,64) and
        {62:130,63:100,64:80}[u['page']]<u['bbox'][1]<{62:700,63:770,64:515}[u['page']]}
    require(total_rows==142 and len(mapped)==len(set(mapped)) and set(mapped)==expected,'Directory source omission/duplication')
    movement=s['movements'];typed=transcript['movements'];same(movement['columns'],typed['columns'],'Wrong movement columns')
    same([normal(' '.join(q['quote'] for q in g)) for g in movement['column_sources']],
         [normal(x) for x in typed['header_quotes']],'Wrong movement headings')
    require(normal(movement['unit_source']['quote'])==normal('(in thousands of euro)'),'Wrong movement unit')
    same(movement['period'],typed['period'],'Wrong movement period')
    require(len(movement['rows'])==len(typed['rows'])==17,'Wrong movement row count')
    cells=[]
    for row,manual in zip(movement['rows'],typed['rows']):
        label=' '.join(q['quote'] for q in row['label_sources']) if row['label_sources'] else row['label']
        same(normal(label),normal(manual[0]),'Wrong movement label')
        require(len(row['cells'])==len(manual[1])==7,'Wrong movement width')
        for c,v in zip(row['cells'],manual[1]):
            token=normal(c['quote']);n=None if token=='-' else -int(token[1:-1]) if token.startswith('(') else int(token)
            require(c['value']==v==n and c['unit']=='EUR thousands' and
                c['status']==('UNKNOWN' if n is None else 'SOURCE_NUMBER'),'Wrong movement value/status/unit')
            cells.append(c)
        boxes=[lookup[c['id']]['bbox'] for c in row['cells']]
        require(all(a[2]<b[0] for a,b in zip(boxes,boxes[1:])) and max(b[1] for b in boxes)-min(b[1] for b in boxes)<2.8,'Wrong movement geometry')
        for q in row['label_sources']:
            box=lookup[q['id']]['bbox'];require(box[2]<boxes[0][0] and abs(box[1]-boxes[0][1])<2.8,'Wrong movement label geometry')
    require(len(cells)==len({c['id'] for c in cells})==119 and
        {c['id'] for c in cells}=={u['id'] for u in units if u['page']==66 and 34<=u['order']<=152},'Movement cells omitted/duplicated')
    expected_clauses={u['id'] for u in units if (u['page']==61 and 5<=u['order']<=24) or
        (u['page']==64 and 308<=u['order']<=313) or (u['page']==65 and 1<=u['order']<=33) or
        (u['page']==66 and u['order'] in (1,2,153))}
    clauses=refs(s['clauses']);require(len(clauses)==len(set(clauses))==62 and set(clauses)==expected_clauses,'Missing substantive clauses')
    same(transcript['pages_reviewed'],list(PAGES),'Incomplete image review')
    for k in ('reported_interpretation','distinctions'):same(s[k],transcript[k],'Wrong interpretation: '+k)
    require({a['key'] for a in transcript['anchors']}=={c['key'] for c in s['clauses']},'Missing manual anchors')
    for a in transcript['anchors']:
        text=' '.join(q['quote'] for c in s['clauses'] if c['key']==a['key'] for q in c['sources'])
        require(normal(a['quote']) in normal(text),'Wrong source anchor')
    old=read(prior.HERE/'reading.json')
    same({k:v for k,v in reading.items() if k!='group_structure_evidence'},old,'039 reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    return {'local_occurrences':1262,'combined_occurrences':len(combined_units(units)),
        'directory_rows':142,'directory_source_occurrences':len(mapped),'movement_rows':17,'movement_cells':119,
        'movement_unknown_dashes':sum(c['value'] is None for c in cells),'clause_groups':20,'substantive_occurrences':62,
        'complete_prior_fields_preserved':True,'financial_or_legal_truth_verified':False}


def full_graph_preflight(candidate,reading,graph):
    namespace={'__name__':'legalmath.prospectus.successor._group_candidate','__package__':'legalmath.prospectus.successor'}
    exec(compile(candidate,'candidate-statement_cells.py','exec'),namespace)
    packet={'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original source mappings','reason':'Actual full-graph preflight'},'reading':reading}
    admitted=namespace['admit'](graph,packet)
    bad=deepcopy(graph);bad['units']=[u for u in bad['units'] if u['id']!='bes-interim-h1-2010:p61:l0']
    negative=deepcopy(packet);negative['graph_sha256']=digest(bad)
    try:namespace['admit'](bad,negative)
    except ValueError as exc:require('original pages or geometry' in str(exc),'Wrong context refusal')
    else:raise ValueError('Missing source context accepted')
    return {'status':'PASS','actual_graph_admitted':True,'context_loss_refused':True,'admitted_sha256':admitted['sha256']}


def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    require(transcript['method']=='MANUALLY_TYPED_FROM_ORIGINAL_IMAGES','Independent image transcript required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['group_structure_evidence']=group_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['group_structure_evidence']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    graph=read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']
    save(HERE/'full-graph-preflight.json',full_graph_preflight(candidate,reading,graph))
    (HERE/'candidate-statement_cells.py').write_text(candidate);save(HERE/'registry-entry.json',entry)
    names=['reading.json','source-units.json','registry-entry.json','candidate-statement_cells.py',
        'image-transcript.json','SOURCE-REVIEW.md','images.json','full-graph-preflight.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try:cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc:require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else:raise ValueError('New profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Note 1 profile unsupported','source_review':common.ref(review)})



def candidate_frozen():
    f=read(HERE/'candidate-freeze.json')
    require(all(sha(HERE/n)==h for n,h in f['bindings'].items()),'Candidate interpretation changed')
    return f


def implement_worker():
    f=candidate_frozen(); require(sha(ROOT/PRODUCTION)==read(PREP/'freeze.json')['baseline_sha256'],'Baseline changed')
    shutil.copyfile(HERE/'candidate-statement_cells.py',ROOT/PRODUCTION)
    require(sha(ROOT/PRODUCTION)==f['candidate_sha256'],'Registry write failed')
    save(HERE/'candidate-production.json',common.production())


def supplied(graph):
    return {'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original page images,exact clauses and independently transcribed tables',
            'reason':'Complete 039 plus Note 1; economic interest, reported control, dated changes and source assertions remain explicit'},
        'reading':read(HERE/'reading.json')}


def build_products(original):
    from legalmath.prospectus.successor import service
    p1=deepcopy(original['P1']); request=p1['payload']['request']; request['source_statement_cells']=supplied(p1['payload']['graph'])
    p1=service.seal('P1',request['bundle'],{'request':digest(request)},p1['payload'])
    p2=service.construction_product(p1,ROOT); p3=service.interpretation_product(p1,p2,original['P3']['payload'].get('interpretation_input'))
    l,f=original['P4']['payload'],original['P5']['payload']
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3,l.get('cases'),l.get('law_input')),
            'P5':service.financial_product(p1,p2,p3,f.get('cases'),f.get('scenario_input'))}


def registry_controls():
    from legalmath.prospectus.successor import statement_cells as cells
    graph={'units':combined_units(read(HERE/'source-units.json'))};rows=[]
    changes={k:(lambda s,k=k:s['distinctions'].update({k:True})) for k in read(HERE/'reading.json')['group_structure_evidence']['distinctions']}
    changes.update({
        'aman-majority':lambda s:s['directory'][0]['rows'][3].update(economic_interest_percent='51.00'),
        'aman-method':lambda s:s['directory'][0]['rows'][3].update(method='EQUITY'),
        'unicre-excluded':lambda s:s['directory'][0]['rows'].pop(),
        'row-duplicated':lambda s:s['directory'][1]['rows'].append(deepcopy(s['directory'][1]['rows'][0])),
        'footnote-lost':lambda s:s['directory'][0]['rows'][3].update(footnote=None),
        'root-blanks-filled':lambda s:s['directory'][0]['rows'][0].update(economic_interest_percent='100.00',method='FULL'),
        'immediate-parent':lambda s:s['directory'][1].update(immediate_legal_parent_inferred=True),
        'unknown-zero':lambda s:s['movements']['rows'][0]['cells'][3].update(value=0,status='SOURCE_NUMBER'),
        'reimbursement-sign':lambda s:s['movements']['rows'][-1]['cells'][4].update(value=899),
        'wrong-unit':lambda s:s['movements']['rows'][0]['cells'][0].update(unit='EUR million'),
        'movement-lost':lambda s:s['movements']['rows'].pop(),
        'clause-lost':lambda s:s['clauses'].pop(),
        'control-threshold':lambda s:s['reported_interpretation'].update(control='At least 50 percent always required'),
        'authority-resolved':lambda s:s['dependency_resolution'].update(source_authority_or_incorporation_resolved=True)})
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['group_structure_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:
            require('reading differs' in str(exc),'Unexpected reading refusal')
            rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','context-occurrence-lost','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=65]
        elif name=='context-occurrence-lost':g['units']=[u for u in g['units'] if u['id']!='bes-interim-h1-2010:p61:l0']
        elif name=='source-hash':next(u for u in g['units'] if u['page']==61)['source_sha256']='0'*64
        elif name=='geometry':next(u for u in g['units'] if u['id']=='bes-interim-h1-2010:p62:l34')['bbox'][1]+=4
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==62)))
        bad=supplied(g)
        try:cells.admit(g,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered source accepted: '+name)
    return rows

def consumer_worker(kind):
    from legalmath.prospectus.successor import service
    candidate_frozen(); original=read(BASE/'attempt-007/products.json.gz')
    baseline=prior.build_products(original); before=service.consume(baseline,ROOT,include_artifacts=True)
    previous=read(prior.HERE/'ordinary.json.gz')
    require(digest(before)==previous['answer_sha256'],'Complete039baseline answer changed')
    current=build_products(original); after=service.consume(current,ROOT,include_artifacts=True)
    for phase in ('P2','P3','P4','P5'):
        left,right=deepcopy(baseline[phase]['payload']),deepcopy(current[phase]['payload'])
        if phase=='P2': left.pop('source_statement_cells'); right.pop('source_statement_cells')
        if phase=='P3': left.pop('source_statement_cells_sha256'); right.pop('source_statement_cells_sha256')
        same(left,right,'Unexpected phase payload change: '+phase)
    same(current['P1']['payload']['graph'],baseline['P1']['payload']['graph'],'Source graph changed')
    left,right=deepcopy(baseline['P1']['payload']['request']),deepcopy(current['P1']['payload']['request'])
    left.pop('source_statement_cells'); right.pop('source_statement_cells'); same(left,right,'Unrelated request changed')
    replacements={k:after[k] for k in ('request_sha256','consumed_products','report_sha256')}
    same({**before,**replacements,'source_statement_cells':after['source_statement_cells']},after,'Unrelated answer change')
    same(before['questions'],after['questions'],'Original questions changed')
    require(after['questions']['Q3']['status']=='PARTIAL' and not after['may_execute_transaction'] and
            not after['independent_legal_acceptance'],'Original limits changed')
    baseline_reading=read(prior.HERE/'reading.json')
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost039field '+key)
    body=after['source_statement_cells']; reading=read(HERE/'reading.json')
    for key in reading: same(body[key],reading[key],'Incomplete delivered field '+key)
    require(body['consumed'] and not body['independent_financial_acceptance'] and body['legal_dependency_resolution']=='UNCHANGED','Scope overclaim')
    checked=source_check(reading,read(HERE/'source-units.json'),read(HERE/'image-transcript.json'))
    cases=registry_controls()
    imported={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
    location=HERE/'installed' if kind=='installed' else ROOT/'src'
    require(imported and all(Path(p).resolve().is_relative_to(location) for p in imported.values()),'Wrong import origin')
    del original,baseline,current,left,right
    composed=read(BASE/'attempt-016/answer-supplement.json.gz'); composition=read(BASE/'attempt-017/composition.json')
    require(digest(composed)==composition['previous_content_sha256'],'Original016changed')
    composed.update(read(BASE/'attempt-017/answer-delta.json.gz'))
    require(digest(composed)==composition['complete_composed_sha256'],'Original017changed')
    keys={21:'h1_normal_statement_consumer',22:'h1_debt_context_consumer',23:'h1_debt_securities_consumer',
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer',28:'h1_risk_native_consumer',29:'h1_events_consumer',30:'h1_financial_policies_consumer',32:'h1_investment_hedges_consumer',33:'h1_income_collateral_consumer',35:'h1_afs_disclosures_consumer',36:'h1_critical_judgments_consumer',37:'h1_trading_balances_consumer',39:'h1_related_parties_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_group_structure_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct 039 from 007; preserve 016/017 and 021/022/023/024/025/026/028/029/030/032/033/035/036/037/039 compositions; add 040 as h1_group_structure_consumer'}
    del composed,before,after,answer
    if kind=='installed':
        ordinary=read(HERE/'ordinary.json.gz')
        for key in receipt:
            if key!='imports': same(receipt[key],ordinary[key],'Installed mismatch: '+key)
        controls_worker('installed-controls.json')
        same(read(HERE/'installed-controls.json'),read(HERE/'controls.json'),'Installed corruption refusals differ')
    save(HERE/(kind+'.json.gz'),receipt)


def controls_worker(output='controls.json'):
    from legalmath.prospectus.successor import service
    original=read(BASE/'attempt-007/products.json.gz'); current=build_products(original); rows=[]
    for change in ('missing_p2','changed_p2','missing_p3','changed_p3','unsupplied'):
        bad=deepcopy(current); request=bad['P1']['payload']['request']; p2,p3=bad['P2']['payload'],bad['P3']['payload']
        if change=='missing_p2': del p2['source_statement_cells']
        elif change=='changed_p2': p2['source_statement_cells']['reading']['group_structure_evidence']['distinctions']['current_control_verified']=True
        elif change=='missing_p3': del p3['source_statement_cells_sha256']
        elif change=='changed_p3': p3['source_statement_cells_sha256']='0'*64
        else: del request['source_statement_cells']
        b=request['bundle']; bad['P1']=service.seal('P1',b,{'request':digest(request)},bad['P1']['payload'])
        for phase,parents in [('P2',['P1']),('P3',['P1','P2']),('P4',['P1','P3']),('P5',['P2','P3'])]:
            bad[phase]=service.seal(phase,b,{p:bad[p]['sha256'] for p in parents},bad[phase]['payload'])
        try: service.consume(bad,ROOT,include_artifacts=True)
        except ValueError as exc:
            require('Consumed statement cells' in str(exc),'Unexpected refusal')
            rows.append({'case':change,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Forged rehashed product accepted: '+change)
    save(HERE/output,{'status':'PASS','actual_consumer_refusals':rows})


def package_worker():
    candidate_frozen(); source=HERE/'package-source'; source.mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
    shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo','*.egg-info'))
    config=read(PREP/'config.json'); python=config['package_python']
    require(sha(python)==config['python_sha256'],'Build interpreter changed')
    command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index',
        '--wheel-dir',str(HERE/'wheel'),str(source)],60)
    wheels=list((HERE/'wheel').glob('*.whl')); require(len(wheels)==1,'Exactly one wheel required')
    expected={n.removeprefix('src/legalmath/'):h for n,h in read(HERE/'candidate-production.json').items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual={n.removeprefix('legalmath/'):digest(archive.read(n)) for n in archive.namelist()
                if n.startswith('legalmath/') and not n.endswith('/')}
    same(actual,expected,'Wheel differs from candidate')
    command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile',
        '--target',str(HERE/'installed'),str(wheels[0])],60)
    folder=HERE/'installed/legalmath'
    same({str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()},expected,'Installed bytes differ')
    save(HERE/'package.json',{'python':python,'wheel':common.ref(wheels[0]),'files':expected})


def coverage_worker():
    rows=deepcopy(read(prior.HERE/'requirements.json')['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):
            row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=common.ref(prior.HERE/'result.json'))
    rows.append({'requirement':'Original Note 1 group structure and acquisition/disposal movements with complete 039 retained',
                 'status':'THIS_ATTEMPT_MUST_PASS; see actual stage results'})
    inventory=deepcopy(read(prior.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note']==41:row['status']='RETAINED_FINITE_INTEGRATION'
        elif row['note']==1:row['status']='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,
        'external_adviser_opinion_required':False,
        'next_discriminating_work':'Inspect remaining accounting policies and Note 27 investments in associates against original requirements and actual retained coverage; controlling edition/source authority remain.'})

def stage(name):
    require(name in DEPENDENCIES and not (HERE/'stages'/name).exists(),'Stage already started or unknown')
    for parent in DEPENDENCIES[name]: require(read(HERE/'stages'/parent/'result.json')['status']=='PASS','Failed predecessor '+parent)
    frozen(); require(costs(46*1024**2 if name=='package' else 4*1024**2)['execution_allowed'],'Stage reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    save(HERE/'stages'/name/'started.json',{'identity':process_identity(os.getpid()),'at':datetime.now(timezone.utc).isoformat(),'stage':name})
    error=None
    try:
        if name=='render': render_worker()
        elif name=='package': package_worker()
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],300)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],360)
        frozen()
    except Exception as exc: error={'type':type(exc).__name__,'reason':str(exc)}
    save(HERE/'stages'/name/'result.json',{'status':'FAIL' if error else 'PASS','error':error})
    return {'stage':name,'status':'FAIL' if error else 'PASS','error':error,'resources':costs()}


def finalize():
    require(not (HERE/'outputs.json').exists(),'Already sealed')
    outcomes={n:read(HERE/'stages'/n/'result.json')['status'] if (HERE/'stages'/n/'result.json').exists() else 'BLOCKED' for n in DEPENDENCIES}
    passed=all(v=='PASS' for v in outcomes.values())
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':outcomes,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# Original group-structure disclosures\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Note 1 retains reported group structure, economic interests, consolidation methods, changes and signed movements. '
        +'Control and significant influence are not inferred from percentage thresholds; unknown dashes remain unknown. '
        +'The full 039 answer and all original compositions including supplied OCR risk tables remain preserved. '
        +'Historical report claims do not establish current standards,rights,valuation or whole-source acceptance.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh;reconcile remaining source obligations with actual current coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
        +'Post-run review: exact profiles preserve supplied readings; a shared wrong interpretation remains the strongest alternative explanation. '
        +'The independent image transcript and full quote/geometry review address source association and omissions. '
        +'They do not prove external financial or legal truth. Remaining coverage is an implementation/evidence gap,not evidence that a package is fundamentally unsuitable.\n')
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU_ONLY;CUDA_VISIBLE_DEVICES=-1;GPU intentionally hidden',
        'random_seeds':'N/A deterministic','plan':PLAN,'result':rel(HERE/'RESULT.md'),
        'data_version':common.ref(PREP/'freeze.json'),'resources':costs()})
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'SEALED','candidate_passed':passed,'resources':costs()}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    action=sys.argv[1]
    if action.startswith('worker-'):
        kind=action.removeprefix('worker-'); sys.path.insert(0,str(HERE/'installed') if kind=='installed' else str(ROOT/'src'))
        def forbidden(*args,**kwargs): raise RuntimeError('No native/network child in source/consumer worker')
        subprocess.Popen=forbidden
        if kind in ('ordinary','installed'): consumer_worker(kind)
        else: {'source':source_worker,'implement':implement_worker,'controls':controls_worker,'coverage':coverage_worker}[kind]()
        result={'status':'PASS','worker':kind}
    elif action=='prepare': result=prepare()
    elif action=='finalize': result=finalize()
    else: result=stage(action)
    print(json.dumps(result))
