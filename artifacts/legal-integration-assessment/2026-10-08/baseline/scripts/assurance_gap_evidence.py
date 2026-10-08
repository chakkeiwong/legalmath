"""Authority retrieval and dependency commitments for phase G5."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
from zipfile import ZipFile
from run_assurance_gap_master import ROOT,OUT,save,read,receipt,sha


def execute(work):
    from assurance_gap_checks import tests
    from legalmath.interpretation.assurance import evidence_identity as evidence
    checks=tests(work,['tests/assurance/test_evidence_identity.py'],timeout=120)
    dependencies=evidence.dependency_identity(['pydantic','pydantic-core','jsonschema','httpx','pypdf','z3-solver'])
    save(work/'dependencies.json',dependencies)
    dependency_check=evidence.verify_dependencies(dependencies)
    tasks=[
        ('cap571-pdf','https://www.elegislation.gov.hk/hk/cap571!en.pdf',['application/pdf'],20_000_000),
        ('legislation-catalog','https://data.gov.hk/en-data/dataset/hk-doj-hkel-legislation-current',['text/html'],5_000_000),
        ('cap301-600','https://resource.data.one.gov.hk/doj/data/hkel_c_leg_cap_301_cap_600_en.zip',['application/zip'],600_000_000),
        ('26ec22','https://apps.sfc.hk/edistributionWeb/api/circular/list-content?lang=EN&refNo=26EC22',['application/json'],5_000_000)]
    def fetch(task):
        name,url,media,limit=task
        return name,evidence.acquire(url,work/'sources'/name,expected_media=media,maximum_bytes=limit,maximum_seconds=300)
    with ThreadPoolExecutor(max_workers=3) as pool:acquired=dict(pool.map(fetch,tasks))
    save(work/'acquisitions.json',acquired)
    # Full selected members are retained. Selection locates a chapter; it does
    # not drop paragraphs from that chapter or assert that it applies to 2023.
    members=[]
    if acquired['cap301-600']['status']=='ACQUIRED':
        with ZipFile(work/'sources/cap301-600/response.bin') as archive:
            names=archive.namelist();save(work/'archive-members.json',names)
            selected=[n for n in names if re.search(r'(?:^|[/_\-])(?:cap[ _\-]?)?0*571(?:[._/\-]|$)',n,re.I)]
            for index,name in enumerate(selected):
                info=archive.getinfo(name)
                if info.is_dir():continue
                if info.file_size>50_000_000:raise RuntimeError('Selected member exceeds reviewed extraction size')
                path=work/'chapter571'/f'{index:03d}-{Path(name).name}'
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(name))
                members.append({'member':name,'crc32':str(info.CRC),'file':receipt(path)})
    old=ROOT/'artifacts/authority-source-revision/2026-09-29/attempt-01/result.json'
    retained=read(old)
    questions=retained['questions']
    save(work/'retained-questions.json',{'original':receipt(old),'questions':questions,
        'new_evidence':members,'affected_question':'23ec52-appendix',
        'qualification':'Current published archive bytes require temporal applicability and provision analysis; acquisition does not settle any question.',
        'old_attempt_limits_reset':False})
    result={'tests':checks,'dependency_check':dependency_check,'dependency_identity':receipt(work/'dependencies.json'),
        'source_status':{k:v['status'] for k,v in acquired.items()},'chapter571_members':members,
        'old_questions_retained':len(questions),'new_source':'26ec22',
        'source_legal_current_force':'NOT_ESTABLISHED','historical_studies_complete':False,
        'legal_correctness':'NOT_ESTABLISHED'}
    save(work/'result.json',result)
    network=[k for k,v in acquired.items() if v['status']=='FAILED' and v.get('error') in ('ConnectError','ProxyError','ConnectTimeout')]
    if network:raise RuntimeError('Source network access requires trusted retry; retained failures: '+','.join(network))
    return result


def repair_acquisition(work):
    from assurance_gap_checks import tests
    from legalmath.interpretation.assurance.official_archive import chapter
    from legalmath.interpretation.assurance.evidence_identity import verify_acquisition
    checked=tests(work,['tests/assurance/test_official_archive.py','tests/assurance/test_evidence_identity.py'],timeout=120)
    original=OUT/'G5/attempt-02'
    row=verify_acquisition(original/'sources/26ec22')
    body=(original/'sources/26ec22/response.bin').read_text()
    if row['media_type']!='text/html' or '<title>Circular on tokenisation of SFC-authorised investment products</title>' not in body:
        raise RuntimeError('New circular was not located; preserve original returned bytes')
    value=chapter('https://resource.data.one.gov.hk/doj/data/hkel_c_leg_cap_301_cap_600_en.zip',work/'chapter571')
    if not value['members']:raise RuntimeError('No complete Chapter 571 member was located')
    result={'tests':checked,'prior_attempt':receipt(original/'manifest.json'),
        'correction':'G5 retained valid acquisition failures; its phase success did not mean source acquisition succeeded. This mandatory repair checks actual complete chapter members.',
        'chapter571':value,'26ec22':{'source':receipt(original/'sources/26ec22/response.bin'),
             'actual_media_type':'text/html','original_wrong_expectation':'application/json'},
        'old_questions_preserved':receipt(original/'retained-questions.json'),
        'legal_current_force':'NOT_ESTABLISHED'}
    save(work/'result.json',result);return result
