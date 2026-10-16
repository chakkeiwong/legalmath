"""Independent retained-byte and rendered-source checks for the master."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import zipfile
from xml.etree import ElementTree

from scripts.legal_integration_master import ROOT, BASE, PRIOR, read, save, ref, verify, require


def run():
    directory = ROOT / BASE / 'corpus-work'
    directory.mkdir(parents=True, exist_ok=True)
    provenance = read(ROOT / PRIOR / 'gatecoin-source-provenance.json')
    rows = []
    for source in provenance:
        original = {k: source['original'][k] for k in ('path', 'sha256')}
        verify(ROOT, original); verify(ROOT, source['derived_text'])
        paragraphs = []
        with zipfile.ZipFile(ROOT / original['path']) as archive:
            for member in ('word/document.xml', 'word/footnotes.xml', 'word/endnotes.xml'):
                if member in archive.namelist():
                    tree = ElementTree.fromstring(archive.read(member))
                    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    paragraphs += [''.join(t.text or '' for t in p.findall('.//w:t', ns))
                                   for p in tree.findall('.//w:p', ns)]
        reproduced = '\n'.join(re.sub(r'\s+', ' ', p).strip() for p in paragraphs if p.strip())
        retained = (ROOT / source['derived_text']['path']).read_text()
        equal = ' '.join(reproduced.split()) == ' '.join(retained.split())
        require(equal, 'Retained Gatecoin derivative differs from original OOXML extraction')
        document = directory / (source['name'] + '.docx')
        if not document.exists(): shutil.copyfile(ROOT / original['path'], document)
        command = ['libreoffice', '-env:UserInstallation=file:///tmp/legalmath-master-lo',
            '--headless', '--convert-to', 'pdf', '--outdir', str(directory), str(document)]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (directory / (source['name'] + '-conversion.log')).write_text(proc.stdout + proc.stderr)
        pdf = document.with_suffix('.pdf')
        if pdf.exists():
            subprocess.run(['pdftotext', '-layout', str(pdf), str(document.with_suffix('.rendered.txt'))], check=True, timeout=30)
        rows.append({'name': source['name'], 'original': original, 'derivative': source['derived_text'],
            'ooxml_text_reproduced': equal, 'pdf': ref(ROOT, pdf) if pdf.exists() else None,
            'rendered_text': ref(ROOT, document.with_suffix('.rendered.txt')) if pdf.exists() else None,
            'conversion_exit': proc.returncode,
            'visual_acceptance': 'PENDING_INSPECTION; conversion is not certification'})
    research = read(ROOT / PRIOR / 'research-evidence.json')
    def verify_all(value):
        if isinstance(value, dict):
            if isinstance(value.get('path'), str) and 'sha256' in value:
                verify(ROOT, {k: value[k] for k in ('path', 'sha256')})
            for child in value.values(): verify_all(child)
        elif isinstance(value, list):
            for child in value: verify_all(child)
    verify_all(research)
    result = {'sources': rows, 'research': ref(ROOT, PRIOR / 'research-evidence.json'),
        'dated_searches': [{k: s[k] for k in ('query', 'response_dates', 'returned_count', 'limitation')}
                          for s in research['searches']],
        'legal_disposition': 'Conditional source analysis remains usable within the dated research scope.',
        'open': ['Rendered layout and legal numbering inspection',
                 'Official correction/appeal or later-treatment source addressing scenario seven',
                 'Applicable P10 discharge/cure standard; P14 footnote/request clarification',
                 'Private arrangement facts and applicable assessment interval'],
        'impossible_claims': 'No item is labelled impossible merely because current sources do not resolve it.'}
    save(directory / 'result.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
