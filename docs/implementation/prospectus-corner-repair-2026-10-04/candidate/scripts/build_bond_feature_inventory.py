#!/usr/bin/env python3
"""Assemble document identities and issue scopes, without expected answers."""
import json
from pathlib import Path

from legalmath.prospectus.common import ROOT, now, read, sha, write


def build():
    archive = ROOT / 'docs/prospectus'
    documents = {}
    for folder in ('classification-additions', 'classification-controls', 'bank-senior-controls'):
        for item in read(archive / folder / 'manifest.json')['documents']:
            row = dict(item)
            original = row.get('original', row.get('path'))
            text = row.get('text', row.get('text_path'))
            if not original.startswith('docs/'):
                original = str(Path('docs/prospectus') / folder / original)
                text = str(Path('docs/prospectus') / folder / text)
            documents[row['id']] = {'id': row['id'], 'original': original, 'text': text,
                'sha256': row.get('sha256', row.get('source_sha256')),
                'text_sha256': row['text_sha256'], 'pages': row['pages'], 'url': row['url'],
                'identity_markers': []}
    retained = ('ubs-sgd-at1-2024-final-published', 'barclays-at1-2025',
                'hsbc-at1-2026-specific', 'standard-chartered-at1-2025-january')
    main = read(archive / 'manifest.json')['documents']
    for key in retained:
        row = main[key]; text = archive / 'text' / (key + '.json')
        documents[key] = {'id': key, 'original': str(Path('docs/prospectus') / row['file']),
            'text': str(text.relative_to(ROOT)), 'sha256': row['sha256'],
            'text_sha256': sha(text.read_bytes()), 'pages': row['page_count'], 'url': row['url'],
            'identity_markers': []}
    issues = []
    def selection(key, *, markers=(), page_markers=(), pages=None, shelf=None, priority=None, basis=None):
        result = {'id': key, 'required_markers': list(markers)}
        if page_markers:
            result['required_page_markers'] = [{'page': page, 'text': text} for page,text in page_markers]
        if pages is not None: result['operative_pages'] = pages
        if shelf: result['shelf_pages'] = shelf
        if priority: result['evidence_priority_pages'] = priority
        result['scope_basis'] = basis or 'The identified issue offering terms; all retained pages searched. English applicability remains a qualified premise.'
        return result
    def issue(key, title, issuer, jurisdiction, rank, docs, identifiers=(), **extra):
        issues.append({'id': key, 'title': title, 'issuer': issuer, 'jurisdiction': jurisdiction,
            'rank': rank, 'security_type': 'debt', 'identifiers': list(identifiers),
            'documents': docs, 'data_role': 'development', **extra})

    issue('tesco-2033', 'Tesco treasury 3.500% senior notes due 2033',
          'Tesco Corporate Treasury Services PLC', 'UK', 'senior unsecured', [
        selection('tesco-2025-final', markers=['XS3201918409', '9 July, 2025', '2 October, 2025']),
        selection('tesco-2025-base', markers=['9 July, 2025', 'TERMS AND CONDITIONS OF THE NOTES'], page_markers=[(2,'The date of this Offering Circular is 9 July, 2025')], priority=[[59,98]]),
        selection('tesco-2025-supplement', markers=['Tesco', '2 October'])], ['XS3201918409'],
        dependency_boundary='Offering-circular conditions and selected final terms, as supplemented. Financial statements and the separate trust/agency agreements are not reconstructed as complete legal contracts.')
    for maturity, isin in [('2031','FR0014017P12'), ('2036','FR0014017P04')]:
        coupon = '3.690%' if maturity == '2031' else '4.122%'
        issue('veolia-'+maturity, 'Veolia '+coupon+' senior notes due '+maturity,
              'Veolia Environnement', 'France / EU', 'senior unsecured', [
            selection('veolia-'+maturity+'-final', markers=[isin, '30 March 2026']),
            selection('veolia-2026-base', markers=['30 March 2026', 'TERMS AND CONDITIONS OF THE SENIOR NOTES'], page_markers=[(1,'30 March 2026')],
                pages=[[1,92],[143,197]], priority=[[46,92]],
                basis='Senior conditions pp.46–92 selected by final terms. Subordinated conditions pp.93–142 are a different security class. Remaining programme disclosures searched.')], [isin],
            dependency_boundary='Dated final terms and base-prospectus disclosures. Separate agency agreement, corporate filings and subsequent changes are not proved complete.')
    issue('deutsche-at1-2025', 'Deutsche Bank 6.75% perpetual AT1, December 2025',
          'Deutsche Bank AG', 'Germany / EU', 'additional tier 1', [
        selection('deutsche-at1-2025', markers=['DE000A460DG7'], priority=[[34,65]])], ['DE000A460DG7'],
        source_language_qualification='German terms prevail; English translation and two-column extraction are not independently certified equivalent.')
    issue('sogecap-rt1-2025', 'Sogécap 6.25% perpetual restricted tier 1, July 2025',
          'SOGECAP', 'France / EU', 'insurance restricted tier 1', [
        selection('sogecap-rt1-2025', markers=['FR00140112W8'], priority=[[48,86]])], ['FR00140112W8'])

    issue('ubs-sgd-at1-2024', 'UBS 5.600% SGD perpetual AT1 (June issue and July tap)',
          'UBS Group AG', 'Switzerland', 'additional tier 1', [
        selection(retained[0], markers=['CH1357852636'], priority=[[3,45],[47,89]])], ['CH1357852636'])
    issue('barclays-at1-2025', 'Barclays 7.625% perpetual AT1, first reset 2035',
          'Barclays PLC', 'UK', 'additional tier 1', [
        selection(retained[1], markers=['US06738EDC66'], pages=[[1,112]],
            shelf=[[113,208]], priority=[[63,96]],
            basis='Issue supplement and contingent-capital base conditions apply; other debt/share offerings in the shelf are not selected.')], ['US06738EDC66'])
    for coupon, reset in [('6.750','2031'), ('7.000','2036')]:
        issue('hsbc-at1-2026-'+reset, 'HSBC '+coupon+'% perpetual AT1, first reset '+reset,
              'HSBC Holdings plc', 'UK', 'additional tier 1', [
            selection(retained[2], markers=['HSBC Holdings plc', reset],
                pages=[[1,115]], shelf=[[116,191]], priority=[[58,96]],
                basis='Two series share the issue supplement and contingent-capital conditions; each series retains its own row. Generic debt and ordinary-share shelf descriptions do not select new features.')],
            identity_qualification='Exact series title/coupon/reset year used; no independently resolved ISIN in the retained PDF.')
    issue('standard-chartered-at1-2025', 'Standard Chartered 7.625% perpetual AT1, January 2025',
          'Standard Chartered PLC', 'UK', 'additional tier 1', [
        selection('standard-chartered-at1-2025-executed-deed', markers=['16 January 2025', 'STANDARD CHARTERED PLC', 'US853254DF47', 'USG84228GP72'], priority=[[34,74]])],
          ['US853254DF47', 'USG84228GP72'],
        source_language_qualification='Issuer-linked execution-version trust deed supplies final conditions. The retained offering circular has a subject-to-completion warning and remains excluded from final-term evidence.',
        identity_qualification='Issuer capital-instruments portal links this executed deed to both displayed ISINs; deed identity also uses issuer, amount, issue type and 16 January 2025 date.')

    control_scopes = {'apple-senior-2025': (28, [[38,48]]), 'duke-senior-2024': (32, [[37,38]]),
                      'duke-junior-2024': (41, [[46,47]]), 'southern-junior-2025a': (26, [[30,35]])}
    for row in read(archive / 'classification-controls/manifest.json')['documents']:
        key = row['id']; end, debt_pages = control_scopes[key]
        issuer = 'Apple Inc.' if key.startswith('apple') else 'Duke Energy Corporation' if key.startswith('duke') else 'The Southern Company'
        for bond in row['issues']:
            issue(bond['provisional_id'], issuer+' '+bond['security'], issuer, 'US', row['rank_selection'], [
                selection(key, pages=[[1,end]], shelf=[[end+1,row['pages']]],
                    priority=[[10,end]], basis='Issue-specific supplement controls. Accompanying general shelf also searched, but unselected securities and optional future issue terms cannot supply this issue’s conversion features.')],
                identity_qualification='Prospectus filing accession '+row['filing_accession']+' plus exact series title; ISIN/CUSIP not independently resolved.')
    issue('nwm-series-14-2025', 'NatWest Markets 4.789% senior notes due 2028',
          'NatWest Markets plc', 'UK', 'senior unsecured', [
        selection('nwm-2025-final', markers=['USG6382RGD47']),
        selection('nwm-2025-base', markers=['17 March 2025'], priority=[[69,70]]),
        selection('nwm-2025-registration', markers=['NatWest Markets'])], ['USG6382RGD47', 'US63906YAM03'],
        identity_qualification='Reg S and Rule 144A identifiers of this offering; fungibility is not asserted.')
    issue('bpce-2025-23', 'BPCE USD SOFR + 1.03% senior preferred notes due 2030',
          'BPCE S.A.', 'France / EU', 'senior preferred', [
        selection('bpce-2025-23-final', markers=['FR0014014YQ1', 'Senior Preferred']),
        selection('bpce-2025-base', markers=['14 November 2025'], priority=[[150,150],[167,167]])], ['FR0014014YQ1'])
    issue('cba-series-6700', 'CBA EUR ESTR + 0.26% senior notes due October 2026',
          'Commonwealth Bank of Australia', 'Australia', 'senior unsecured', [
        selection('cba-2025-6700-final', markers=['XS3206613666']),
        selection('cba-2025-base', markers=['1 July 2025'], priority=[[60,141]]),
        selection('cba-2025-emtn-supplement', markers=['13 August 2025'])], ['XS3206613666'],
        dependency_boundary='Dated offering-circular disclosures and selected supplement. The separate agency/deed documents and later law are outside the source conclusion.')
    used = {d['id'] for issue in issues for d in issue['documents']}
    dispositions = [
        {'id': key, 'disposition': 'retained supporting/rejected source; not selected operative terms'}
        for key in documents if key not in used]
    for key, row in main.items():
        if key in retained: continue
        dispositions.append({'id': key, 'disposition':
            'excluded preferred-share security' if any(x in key for x in ('series-pp','series-ss','series-d')) else
            'not an available final individual CoCo issue: programme, background, preliminary, duplicate or failed acquisition',
            'archive_role': row.get('role'), 'archive_status': row.get('status')})
    return {'schema': 'bond-prospectus-feature-inventory.v1', 'created_at': now(),
        'scope': 'Explicit disclosures in the dated retained offering documents; not complete contract reconstruction, current law or trade eligibility.',
        'documents': {key:documents[key] for key in sorted(used)}, 'issues': issues,
        'archive_dispositions': dispositions,
        'quality_labels': False, 'expected_answers': False,
        'scope_provenance': 'Source-based document/section proposals by the coding agent; conditional premises, not independent proof of legal relevance.'}


if __name__ == '__main__':
    target = ROOT / 'docs/prospectus/classification-additions/issue-inventory.json'
    write(target, build())
    print(target.relative_to(ROOT))
