"""Source section readings, explicit chains and conservative scope refusals."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import gzip,json,pytest
from legalmath.prospectus.successor import standalone_sections as module
from legalmath.prospectus.successor.contracts import digest
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/implementation/prospectus-execution-authority'
PREP=BASE/'reviews/standalone-sections-348'

@pytest.mark.parametrize('text,raw,law,numbers,onward',[
 ('§ 13 gilt.','§ 13',None,['13'],False),
 ('§ 15 Aktiengesetz.','§ 15 Aktiengesetz','AktG',['15'],False),
 ('§ 18 und §§ 5 ff.\nSchVG','§ 18 und §§ 5 ff.\nSchVG','SchVG',['18','5'],True),
 ('§§ 5 ff. SchVG','§§ 5 ff. SchVG','SchVG',['5'],True),
 ('§ 7 BGB','§ 7 BGB','BGB',['7'],False),
 ('§ 13 gilt. § 5 SchVG','§ 13',None,['13'],False),
 ('§ 7 gilt. des SchVG','§ 7',None,['7'],False),
])
def test_declared_section_grammar(text,raw,law,numbers,onward):
    row=module.parse(text,0)
    assert row['raw']==raw and row['statute']==law and row['onward_scope']==onward
    assert [m['number'] for m in row['members']]==numbers and row['issues']==[]

@pytest.mark.parametrize('text,issue',[
 ('§§ 5','ONWARD_OR_PLURAL_SCOPE_UNRESOLVED'),
 ('§ 5 ff.','ONWARD_OR_PLURAL_SCOPE_UNRESOLVED'),
 ('§ 5 und § 7','CHAIN_SCOPE_UNRESOLVED'),
 ('§ 5 und §','INCOMPLETE_CHAIN'),
 ('§ 7 Sondergesetz','UNRECOGNIZED_QUALIFIER'),
 ('§ 7 des Sondergesetzes','UNRECOGNIZED_QUALIFIER'),
 ('§ 7 Absatz (2)','UNRECOGNIZED_QUALIFIER'),
 ('§ 07','NONCANONICAL_NUMBER'),
])
def test_unknown_scope_is_not_contract_target(text,issue):
    row=module.parse(text,0);assert issue in row['issues']
    assert module.resolve(row,{'document':'d','context':'c'},[])['status']=='UNRESOLVED'

@lru_cache(maxsize=1)
def source_case():
    manifest=json.loads((BASE/'reviews/conditional-cli-311/products.json').read_text())
    products={k:json.loads((ROOT/r['path']).read_text()) for k,r in manifest['products'].items()}
    old=json.loads(gzip.decompress((BASE/'attempts/basf-references/attempt-086/ordinary-answer.json.gz').read_bytes()))
    return products,old

def test_full_source_before_consumers():
    from scripts.prospectus_standalone_sections_oracle import verify
    products,old=source_case();profile=json.loads((PREP/'profile.json').read_text())
    actual={**old,**module.evaluate(products,old,profile,ROOT,expected_profile_sha256=digest(profile))}
    actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
    assert verify(actual,old,products,json.loads((PREP/'expected.json').read_text()))['status']=='PASS'

@pytest.mark.parametrize('kind',['missing','duplicate','foreign-document','foreign-context'])
def test_unique_same_source_destination_required(kind):
    header={'document':'d','context':'c'}
    target={'document':'d','context':'c','section':'13'};targets=[target]
    if kind=='missing':targets=[]
    elif kind=='duplicate':targets.append(dict(target))
    elif kind=='foreign-document':target['document']='other'
    else:target['context']='other'
    assert module.resolve(module.parse('§ 13',0),header,targets)['status']=='UNRESOLVED'

def test_named_statute_never_resolves_contract_label():
    target={'document':'d','context':'c','section':'15'}
    row=module.resolve(module.parse('§ 15 Aktiengesetz',0),target,[target])
    assert row['status']=='EXTERNAL_STATUTE' and row['targets']==[]

def test_section_sign_not_double_counted_and_heading_excluded():
    text='§ 1\nHeading. §§ 5 ff. SchVG'
    signs,groups=module.discover(text,[{'start':0,'end':3}],[])
    assert len(signs)==2 and len(groups)==1 and signs[0]['classification']=='SECTION_HEADER'

def test_reviewed_target_lists_are_not_used():
    products,old=source_case();changed=deepcopy(products)
    changed['P3']['payload']['interpretation_input']['reference_admission']['references']=[]
    assert module.content(changed,old)==module.content(products,old)
