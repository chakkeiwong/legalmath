"""Offline B1 acceptance on retained actual source versions; no legal approval."""
from argparse import ArgumentParser
from pathlib import Path
from legalmath.canonical import loads, raw_digest
from legalmath.interpretation.assurance.authorities import AuthorityCatalog, root_reference
from legalmath.interpretation.assurance.sources import packet_from_context, audit_packet
from legalmath.interpretation.assurance.monitor import save

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'.localresources/sfc-authorities/b1'


def execute(out):
    manifest = loads((SOURCES/'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        if raw_digest((SOURCES/name).read_bytes()) != expected:
            raise ValueError('Retained authority bytes changed: ' + name)
    out = Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round4'):
        raise ValueError('Use a new round4 output directory')
    out.mkdir(parents=True)
    c = AuthorityCatalog.load(SOURCES/'catalog.json'); rows = []
    for alias in c.value['aliases']:
        for at in ('2023-11-30', '2026-09-24'):
            resolution = c.resolve(alias['locator'], at); selected = c.select(resolution)
            if alias['authority_id'] == 'sfc.code':
                expected = 'code.2023' if at.startswith('2023') else 'code.current'
                assert resolution['status'] == 'RESOLVED' and resolution['edition_id'] == expected
                assert selected['status'] == 'CONTEXT_INCOMPLETE'
                assert any(f['kind'] == 'UNRESOLVED_CONTEXT_REFERENCE' for f in selected['findings'])
                context = {'documents': selected['documents'], 'findings': []}
                packet = packet_from_context(context, 'Paragraph 3.11 gift control, definitions and qualifications')
                assert any('fees or charges' in u['text'] for u in packet['units'])
                assert any('Schedule 1' in u['text'] for u in packet['units'])
                assert not any(f['kind'] == 'MISSING_SOURCE_TEXT' for f in audit_packet(packet, context))
                save(out/(expected+'-packet.json'), packet)
            else:
                assert resolution['status'] == 'UNKNOWN_VERSION' and not selected['documents']
            rows.append({'at': at, 'resolution': resolution,
                         'selection': {k:v for k,v in selected.items() if k != 'documents'}})
    raw = (ROOT/'.localresources/sfc/24EC16.json').read_bytes()
    identity = root_reference('SFC circular, refNo=24EC16 (official locator in source packet)', [
        {'url':'https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=24EC16',
         'media_type':'application/json', 'data':raw}])
    assert identity and identity['status'] == 'RESOLVED_ROOT_IDENTITY'
    save(out/'resolutions.json', rows)
    save(out/'root-reference.json', identity)
    ledger = loads((ROOT/'artifacts/interpretation/round2/live-allowance.json').read_bytes())
    save(out/'summary.json', {'status':'PASS_WITH_UNRESOLVED_AUTHORITIES', 'catalog_hash': c.hash,
        'complete_official_sources':len(c.documents), 'resolutions':len(rows), 'new_live_calls':0,
        'allowance_used':len(ledger['calls']), 'historical_code_edition_selected':True,
        'current_code_edition_selected':True, 'unknown_faq_version_preserved':True,
        'unresolved_definition_context_preserved':True, 'exact_root_reference_resolved':True,
        'legal_accuracy_evaluated':False, 'semantic_context_completeness':False})
    save(out/'manifest.json', {'files':{str(p.relative_to(out)):raw_digest(p.read_bytes()) for p in sorted(out.iterdir())}})
    print('B1 PASS: two Code editions selected; FAQ history and remote definitions remain unresolved; zero new model calls.')


if __name__ == '__main__':
    p = ArgumentParser(description=__doc__); p.add_argument('--out', required=True)
    execute(p.parse_args().out)
