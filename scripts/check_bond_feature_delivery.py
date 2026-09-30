#!/usr/bin/env python3
"""Verify preserved source reports and publish a reproducible combined view."""
import csv
from bisect import bisect_right
from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile
import time
import xml.etree.ElementTree as ET

from legalmath.prospectus.common import ROOT, now, read, sha, write
from legalmath.prospectus.loss_absorption import decide, explain
from legalmath.prospectus.loss_absorption_reader import analyze_issue, joined, load_document, definition_scope, WATCH

DIRECTORY=ROOT/'docs/implementation/bond-loss-absorption-classification'
RUNS=DIRECTORY/'execution'


def report_witness(row):
    """Choose a concise source witness, without changing the frozen decision.

    This is a bounded presentation filter, not an English entailment checker.
    Preserve the original engine reason and every candidate in the JSON.
    """
    if row['answer'] is None:
        return None
    if 'derivation' in row:
        identity=row['derivation']['evidence_ids'][0]
        return next(e for e in row['evidence'] if e['id']==identity)
    candidates=[e for e in row['evidence'] if e['disposition']=='applicable'
                and e['scope']=='operative']
    if row['answer']:
        conversions=[e for e in candidates if e['kind']=='mandatory_common_conversion'
                     and not re.search(r'Newco Scheme|shall be construed accordingly',e['quote'],re.I)]
        candidates=conversions or [e for e in candidates if e['kind']=='principal_write_down']
    else:
        candidates=[e for e in candidates if e['kind']=='cash_repayment']
        maturity=re.search(r'\bdue\s+(\d{4})\b',row['title'],re.I)
        if maturity:
            year=maturity.group(1)
            def series_years(item):
                return set(re.findall(r'\b((?:19|20)\d{2})\s+(?:Notes|Debentures)\b',item['quote'],re.I))
            candidates=[e for e in candidates if not series_years(e) or year in series_years(e)]
            candidates.sort(key=lambda e:0 if series_years(e)=={year} else 1 if year in series_years(e) else 2)
    if not candidates:
        raise ValueError('No adequate summary witness for '+row['id'])
    return candidates[0]


def report_reason(row, documents):
    if 'derivation' in row:
        from legalmath.prospectus.loss_absorption_derivation import render
        reason=render(row)
        for key,doc in documents.items():
            if doc.get('kind')=='html':reason=reason.replace(key+', PDF p.1',key+', HTML text unit 1')
        return reason,row['derivation']['evidence_ids'][:1]
    witness=report_witness(row)
    if witness is None:
        return row['summary_reason'], []
    doc=documents[witness['document']]
    if doc.get('kind')=='html':
        location='HTML text unit '+str(witness['page'])
    elif witness['end_page']!=witness['page']:
        location=f"PDF pp.{witness['page']}–{witness['end_page']}"
    else:
        location='PDF p.'+str(witness['page'])
    citation=witness['document']+', '+location
    if row['answer'] is False:
        reason=('No within the examined offering terms: the debt provides for cash principal repayment ('+
                citation+'); the declared operative document set has been examined and no applicable '
                'principal write-down or compulsory common-share conversion was identified.')
    elif witness['kind']=='mandatory_common_conversion':
        reason=('Yes: the selected bond can be compulsorily converted into common/ordinary shares ('+
                citation+'). The conversion power need not have been exercised.')
    else:
        origin={'statutory-disclosed':'a disclosed statutory resolution power',
                'contractual':'the contractual terms'}.get(witness['origin'],'the disclosed mechanism')
        reason=('Yes: the principal can be reduced or cancelled under '+origin+' ('+
                citation+'). The applicable trigger conditions are stated in the cited clause; '
                'the power need not have been exercised.')
    return reason,[witness['id']]


def verify():
    started=time.monotonic()
    config=read(RUNS/'delivery-config.json')
    frozen=read(RUNS/config['freeze'])
    if any(sha((ROOT/p).read_bytes()) != h for p,h in frozen['source_hashes'].items()):
        raise ValueError('The frozen implementation changed')
    if sha((ROOT/'tests/prospectus/test_loss_absorption.py').read_bytes()) != frozen['tests_sha256']:
        raise ValueError('The frozen controlled tests changed')
    all_results=[]; all_documents={}; reports=[]; baseline=[]; quotation_count=0
    inventories={}
    for source_set in config['source_sets']:
        folder,run_name=source_set[:2]
        inventory_path=ROOT/'docs/prospectus'/folder/(source_set[2] if len(source_set)>2 else 'issue-inventory.json')
        inventory=read(inventory_path); inventories.setdefault(folder,inventory)
        directory=RUNS/run_name; manifest=read(directory/'run-manifest.json')
        if manifest['status'] != 'COMPLETE' or sha(inventory_path.read_bytes()) != manifest['inventory_sha256']:
            raise ValueError('Run or inventory changed: '+run_name)
        for name,expected in manifest['artifacts'].items():
            if sha((directory/name).read_bytes()) != expected:
                raise ValueError('Run artifact changed: '+name)
        cached={key:(load_document(row,ROOT),row) for key,row in inventory['documents'].items()}
        normalized={key:joined(doc) for key,(doc,_) in cached.items()}
        texts={key:value[0] for key,value in normalized.items()}
        rows=read(directory/'classification.json')['results']
        if manifest['dirty_source_hashes']!={p:sha((ROOT/p).read_bytes()) for p in manifest['dirty_source_hashes']}:
            raise ValueError('Run used another method: '+run_name)
        if {r['id'] for r in rows}!={r['id'] for r in inventory['issues']}:
            raise ValueError('Missing/extra issue rows')
        for row in rows:
            if 'derivation' in row:
                from legalmath.prospectus.loss_absorption_derivation import check
                issue=next(i for i in inventory['issues'] if i['id']==row['id'])
                verified={s['id']:{'text':texts[s['id']], 'sha256':cached[s['id']][0]['source_sha256'],
                    'definition_text':definition_scope(*normalized[s['id']],s)} for s in issue['documents']}
                check(row,verified)
            decision=decide(row['facts'])
            if any(row[k] != decision[k] for k in ('answer','classification','status')):
                raise ValueError('Decision/report mismatch')
            for evidence in row['evidence']:
                doc,_=cached[evidence['document']];text=texts[evidence['document']]
                if doc['source_sha256'] != evidence['source_sha256'] or text[evidence['start']:evidence['end']] != evidence['quote']:
                    raise ValueError('Quotation binding mismatch: '+evidence['id'])
                if evidence['page'] != bisect_right(normalized[evidence['document']][1],evidence['start']):
                    raise ValueError('Quotation page mismatch')
                quotation_count+=1
            if row['answer'] is True and not any(e['kind'] in ('principal_write_down','mandatory_common_conversion')
                                                  and e['disposition']=='applicable' for e in row['evidence']):
                raise ValueError('Positive without a witness')
            if row['answer'] is False and (not row['facts']['coverage_complete'] or row['open_issues']):
                raise ValueError('Negative with missing evidence')
            sources={c['document'] for c in row['coverage']}
            baseline.append({'id':row['id'],'keyword_any_hit':any(WATCH.search(texts[k]) is not None for k in sources),
                             'qualified_source_answer':row['answer'],'role':'Explanatory comparison only; neither side is an independent English/legal oracle'})
        # Presentation changes do not alter the frozen inputs or decisions.
        for row in rows:
            row['engine_summary_reason']=row['summary_reason']
            row['summary_reason'],row['summary_evidence_ids']=report_reason(row,inventory['documents'])
        all_results.extend(rows);all_documents.update(inventory['documents'])
        reports.append({'run':run_name,**read(directory/'summary.json')})

    # Faults use copied real documents. The archived originals are never edited.
    development=inventories.get('classification-additions') or read(ROOT/'docs/prospectus/classification-additions/issue-inventory.json')
    tesco=next(r for r in development['issues'] if r['id']=='tesco-2033')
    faults=[]
    with tempfile.TemporaryDirectory(prefix='bond-feature-source-faults-') as tmp:
        tmp=Path(tmp)
        def check(name,issue,documents):
            result=analyze_issue(issue,documents,ROOT)
            if result['answer'] is not None:
                raise ValueError('Fault yielded a supported answer: '+name)
            faults.append({'fault':name,'status':'REJECTED_OR_UNRESOLVED','reason':result['summary_reason']})
        docs=deepcopy(development['documents']);row=docs['tesco-2025-base']
        altered=tmp/'altered.pdf';altered.write_bytes((ROOT/row['original']).read_bytes()+b'\nchanged')
        row['original']=str(altered);check('altered_original_bytes',tesco,docs)
        docs=deepcopy(development['documents']);row=docs['tesco-2025-base']
        document=read(ROOT/row['text']);document['pages'].pop()
        truncated=tmp/'truncated.json';write(truncated,document)
        row['text']=str(truncated);row['text_sha256']=sha(truncated.read_bytes())
        check('missing_last_page_even_with_updated_text_hash',tesco,docs)
        docs=deepcopy(development['documents']);del docs['tesco-2025-supplement']
        check('missing_named_supplement',tesco,docs)
        docs=deepcopy(development['documents']);row=docs['tesco-2025-base']
        document=read(ROOT/row['text']);document['pages'][0],document['pages'][1]=document['pages'][1],document['pages'][0]
        reordered=tmp/'reordered.json';write(reordered,document)
        row['text']=str(reordered);row['text_sha256']=sha(reordered.read_bytes())
        check('reordered_real_pages',tesco,docs)
        docs=deepcopy(development['documents']);row=docs['tesco-2025-base']
        row['original']=docs['veolia-2026-base']['original']
        check('different_issuer_original_substitution',tesco,docs)
        held=inventories.get('classification-holdout') or read(ROOT/'docs/prospectus/classification-holdout/issue-inventory.json')
        issue=held['issues'][0];docs=deepcopy(held['documents'])
        wrong=next(r for r in read(ROOT/'docs/prospectus/classification-holdout/manifest.json')['documents'] if r['id']=='compass-2026-base')
        docs['compass-2025-base']={**wrong,'id':'compass-2025-base'}
        check('newer_base_with_consistent_hashes_but_wrong_named_edition',issue,docs)
    if config.get('additional_source_faults'):
        extra=read(ROOT/config['additional_source_faults'])
        if extra['status']!='PASS' or any(f['answer'] is not None for f in extra['faults']):
            raise ValueError('Additional source-fault verification failed')
        faults.extend(extra['faults'])
    regression=ET.parse(RUNS/config['regression']).getroot()
    suites=list(regression.iter('testsuite'))
    test_count=sum(int(s.attrib['tests']) for s in suites)
    if any(int(s.attrib.get('errors',0))+int(s.attrib.get('failures',0)) for s in suites):
        raise ValueError('Regression failure')
    fresh=[r for r in all_results if r['data_role']=='post-freeze-challenge']
    native_count=sum(r['native']['executed_target_cases'] for r in reports)
    report={'recorded_at':now(),'frozen_method_unchanged':True,'bonds':len(all_results),
        'yes':sum(r['answer'] is True for r in all_results),'no':sum(r['answer'] is False for r in all_results),
        'unresolved':sum(r['answer'] is None for r in all_results),'documents_used':len(all_documents),
        'unique_source_pages':sum(r['pages'] for r in all_documents.values()),'checked_quotations':quotation_count,
        'real_document_faults':faults,'native_runs':[{k:r[k] for k in ('run','native')} for r in reports],
        'tests_passed':test_count,'classifier_tests':config['classifier_tests'],
        'fresh_transfer_bonds':[{'id':r['id'],'answer':r['answer']} for r in fresh],
        'derivation_checks':sum(r.get('derivation_check',{}).get('status')=='CHECKED' for r in all_results),
        'wall_seconds':time.monotonic()-started,'legal_entailment':'NOT_PROVED','human_quality_labels':False,
        'unknown_future_generalization':'NOT_PROVED','verification_scope':'Source integrity, finite declared-premise logic, native execution and limited conditional transfer. English relevance/completeness is not independently proved.'}
    write(RUNS/'delivery-verification.json',report)
    write(RUNS/'keyword-baseline.json',baseline)
    archive_rows=[]
    for key,row in read(ROOT/'docs/prospectus/manifest.json')['documents'].items():
        if key in all_documents:
            disposition='USED_IN_PUBLISHED_RESULTS'
        elif any(term in key for term in ('series-pp','series-ss','series-d')):
            disposition='PREFERRED_SHARE_OUTSIDE_REQUESTED_DEBT_CLASSIFICATION'
        elif row.get('preliminary_indicator'):
            disposition='PRELIMINARY_OR_COMPLETION_WARNING_NOT_FINAL_EVIDENCE'
        else:
            disposition='PROGRAMME_BACKGROUND_DUPLICATE_OR_UNSELECTED_SOURCE; see original archive role'
        archive_rows.append({'id':key,'archive_role':row.get('role'),'disposition':disposition})
    write(RUNS/'inventory-reconciliation.json',{'recorded_at':now(),'documents':archive_rows,
          'correction':'Lloyds final HTML mirror is included. Earlier omission of this retained source is not carried into the published inventory.'})
    write(DIRECTORY/'results.json',{'verification':report,'results':all_results})
    columns=['id','title','issuer','jurisdiction','rank','identifiers','answer','classification','status','summary_reason','qualification']
    with (DIRECTORY/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for row in all_results:
            writer.writerow({k:('; '.join(row[k]) if isinstance(row.get(k),list) else row.get(k)) for k in columns})
    lines=['# Bond-by-bond loss-absorption results','',
        f"The programme produced {report['yes']} positive, {report['no']} negative and {report['unresolved']} unresolved results for {report['bonds']} bond series. "
        'These are qualified readings of dated offering documents. Preferred-share securities are excluded. '
        'A positive identifies principal write-down or compulsory common-share conversion, including disclosed statutory bail-in. '
        'A negative requires affirmative debt/repayment terms and no unresolved potentially qualifying candidate in the declared source set. '
        'Ordinary creditor-approved restructuring is treated separately.','',
        '| Bond | ISIN / identity | Result | Supporting reason |','| --- | --- | --- | --- |']
    for row in all_results:
        answer='Yes — loss absorption' if row['answer'] is True else 'No — non loss absorption' if row['answer'] is False else 'Unresolved'
        reason=row['summary_reason']
        for key,document in sorted(all_documents.items(),key=lambda pair:-len(pair[0])):
            reason=reason.replace('('+key+', PDF p.', '(['+key+'](../../../'+document['original']+'), PDF p.')
            reason=reason.replace('('+key+', PDF pp.', '(['+key+'](../../../'+document['original']+'), PDF pp.')
            reason=reason.replace('('+key+', HTML text unit ', '(['+key+'](../../../'+document['original']+'), HTML text unit ')
        lines.append('| '+' | '.join(str(v).replace('|','/') for v in (row['title'],', '.join(row['identifiers']) or row['id'],answer,reason))+' |')
    lines += ['', '## What was checked', '',
        f"{test_count} prospectus tests passed, including {config['classifier_tests']} tests for this classifier. The independent specification checked all 256 known/unknown/conflict input states; "
        'two SMT equivalence obligations passed and four deliberately wrong formal rules were detected. '
        f"RuleIR/Java and Catala executed the same {len(all_results)} bond input sets, plus 24 formal challenge cases in each of {len(reports)} runs, for {native_count} native executions. "
        'Kernel-checked lowering and source integrity establish conditional software properties, not legal interpretation.', '',
        f"Every one of the {quotation_count:,} emitted evidence records was rebound to its preserved source text. {len(faults)} faults involving actual PDFs/text were rejected or left unresolved. "
        'The reader repairs were checked against action, polarity, issue, definition, source and monetary-relation challenges. '
        'Previously inspected documents are development cases. '
        + ('The new frozen version processed these fresh cases: '+', '.join(r['id']+' ('+('yes' if r['answer'] is True else 'no' if r['answer'] is False else 'unresolved')+')' for r in fresh)+'. ' if fresh else 'No fresh transfer claim is made in this interim report. ')
        + 'No source-answer labels were used.', '',
        '## Qualifications and remaining work', '',
        'The binary result is the existence of the requested prospectus feature. Positive rows can still contain unresolved subsidiary clauses: '
        'a sufficient witness establishes the feature without establishing every possible mechanism or its limits. '
        'The full JSON retains those open clauses. A negative is conditional on the declared document selection and bounded English analysis; '
        'it is not a proof that all incorporated contracts, later amendments and applicable law have been found. '
        'The system cannot independently prove unrestricted English meaning or correctness for every unknown future document. '
        'It makes that qualification explicitly and uses missing-evidence states rather than inventing certainty.', '',
        'Standard Chartered uses an issuer-published executed trust deed because the retained circular carries subject-to-completion language. '
        'Deutsche Bank’s German terms prevail; the English translation has not been independently proved equivalent. '
        'Lloyds uses a retained final filing mirror: official issuer-PDF acquisition failed, and byte identity with EDGAR is not established. '
        'Some US/HSBC series use filing/series identities because their ISINs were not independently resolved. '
        'Issuer names, domicile and rank are metadata, never classification rules.', '',
        'Shell now has an exact repayment derivation: £1,000 final redemption per £1,000 calculation amount. '
        'The definitions and money fields, source positions, selected issue and generated explanation are checked together. '
        'A separate checker evaluates the decision and rejects inconsistent or altered evidence. '
        'It shares the bounded English constructions with the reader; it is independent of the decision implementation, '
        'not an independent proof of natural-language interpretation.', '',
        'Next work: strengthen semantic subject/condition resolution, close incorporated-document and amendment dependencies, '
        'validate authoritative language alignment, and run further frozen document-family challenges. '
        'Treat future source or law changes as reasons to re-acquire and re-evaluate. A negative here does not mean low investment risk or transaction permission.', '',
        '[Machine-readable results](results.json) · [CSV](results.csv) · [verification](execution/delivery-verification.json) · '
        '[reviewed execution plan](../../../'+config.get('plan','docs/plans/bond-reader-repair-program.md')+') · [source freeze](execution/'+config['freeze']+')', '']
    review=DIRECTORY/'source-review.md'
    if review.exists():
        lines += [review.read_text().strip(), '']
    (DIRECTORY/'results.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in report.items() if k not in ('native_runs','real_document_faults')},indent=2))


if __name__=='__main__':
    verify()
