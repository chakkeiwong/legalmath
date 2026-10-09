"""Copied into the isolated runtime directory; imports only the installed wheel."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
from copy import deepcopy
import legalmath
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest, read, write


def question_summary(questions):
    """Bind every answer field without repeating large source/dependency trees."""
    return {key: {'status': value['status'], 'payload_sha256': digest(value)}
            for key, value in questions.items()}


def main():
    fixture_file, case_root, result_path = map(Path, sys.argv[1:4])
    if not Path(legalmath.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError('Installed check imported the checkout')
    fixtures = runpy.run_path(str(fixture_file))
    basf_check = runpy.run_path(str(fixture_file.with_name('basf_consumer.py')))['check_report']
    existing = '--existing' in sys.argv
    questions = {}
    for name in ('repayment', 'exception', 'coupon', 'full_coupon', 'cross_document', 'ast_reference', 'large_z3', 'compass', 'basf'):
        folder = case_root/name
        if not existing:
            folder.mkdir(parents=True,exist_ok=name in {'compass','basf'})
            if name == 'repayment':
                request = fixtures['request'](folder, [fixtures['PREFIX']])
            elif name == 'exception':
                request = fixtures['annotation_fixture'](folder)
                request['observations'] = {'exempt': True}
            elif name == 'coupon':
                request = fixtures['term_fixture'](folder)
            elif name in {'compass','basf'}:
                request = read(folder/'request.json')
            else:
                builder = {'full_coupon':'full_term_fixture','cross_document':'cross_document_fixture',
                           'ast_reference':'ast_reference_fixture','large_z3':'large_z3_fixture'}[name]
                request = fixtures[builder](folder)
                if name == 'cross_document':
                    request['observations'] = {'exempt':True}
            write(folder/'request.json', request)
        request = read(folder/'request.json')
        argv = [sys.executable, '-I', '-m', 'legalmath.cli', 'prospectus', 'assess',
                '--request', str(folder/'request.json'), '--repository', str(folder), '--output', str(folder/'cli-report.json')]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=180 if name=='basf' else 60)
        if result.returncode:
            # The outer restoration runner preserves these streams even after
            # its temporary runtime is removed. A CalledProcessError alone loses
            # the child diagnostic needed to distinguish usage from code failure.
            print(result.stdout, end='')
            print(result.stderr, end='', file=sys.stderr)
            raise RuntimeError('Installed CLI case failed: '+name)
        report = read(folder/'cli-report.json')
        if name=='basf':
            if (folder/'agent-review.json').is_file():
                agent_check = runpy.run_path(str(fixture_file.with_name('basf_agents_consumer.py')))['check_report']
                outcome = agent_check(report, request, read(folder/'agent-review.json'),
                                      scalar_check=basf_check, notice_packet=read(folder/'notice-review.json'))
            elif (folder/'notice-review.json').is_file():
                notice_check = runpy.run_path(str(fixture_file.with_name('basf_notices_consumer.py')))['check_report']
                outcome = notice_check(report, request, read(folder/'notice-review.json'), scalar_check=basf_check)
            else:
                outcome=basf_check(report,request)
            # The original PDFs are retained. Avoid duplicating the 90 MB raw
            # source graph in each evidence attempt; keep its exact identity and
            # the actual consumer dependencies plus CLI product identities.
            summary = question_summary(report['questions'])
            write(folder/'cli-report-summary.json',{'version':'basf-installed-consumer-summary.v2',
                'outcome':outcome,'questions':summary, 'dependencies':report['dependencies'],
                'consumed_products':report['consumed_products'],'source_graph_sha256':report['source_graph_sha256'],
                'full_cli_output_sha256':digest((folder/'cli-report.json').read_bytes()),
                'report_sha256':report['report_sha256'],'scope':'Fresh installed CLI assessment; P1-P5 built by the CLI'})
            (folder/'cli-report.json').unlink()  # this invocation's temporary output only
            questions[name]=summary
            if 'notices' in outcome:
                questions[name]['notice_meanings'] = outcome['notices']
            if 'agents' in outcome:
                questions[name]['agent_meanings'] = outcome['agents']
            continue
        p1 = service.source_product(request, folder)
        p2 = service.construction_product(p1, folder)
        p3 = service.interpretation_product(p1,p2)
        products = {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
        if service.consume(products, folder, mode='current')['questions'] != report['questions']:
            raise ValueError('Installed assess/current consume mismatch')
        write(folder/'products.json', products)
        if name in {'repayment','exception','cross_document'} and report['questions']['Q1']['status'] != 'NO':
            raise ValueError('Wrong installed source-to-answer control')
        if name == 'coupon':
            payments = report['questions']['Q5']['value']['calculation']['transfers']
            if [row['amount'] for row in payments] != ['1001/100','501/100']:
                raise ValueError('Wrong installed exact coupon result')
            changed = deepcopy(request)
            changed['term_interpretations']['terms']['annual_rate']['value']='0.06'
            try:
                service.assess(changed, folder)
            except ValueError:
                pass
            else:
                raise ValueError('Installed service accepted an unbound rate')
        if name == 'full_coupon':
            value = report['questions']['Q5']['value']
            if value['regular_due_dates'] != ['2025-01-01','2026-01-01'] or value['calculation']['transfers'][0]['amount'] != '501/50':
                raise ValueError('Installed calculation-amount coupon/schedule differs')
        if name == 'ast_reference' and (not report['dependencies'] or any(d['status']!='RESOLVED' for d in report['dependencies'])):
            raise ValueError('Installed AST reference mapping failed')
        if name == 'large_z3' and (report['questions']['Q4']['status'] != 'YES' or
                report['assembly']['rendered_ast']['reasoning'][0]['result']['status'] != 'YES'):
            raise ValueError('Installed larger-domain construction/law routing failed')
        if name == 'compass':
            value = report['questions']['Q5']['value']
            if (value['regular_due_dates'] != [f'{year}-01-15' for year in range(2027,2036)] or
                    value['calculation']['transfers'][0]['amount'] != '3500' or
                    report['questions']['Q3']['status'] != 'PARTIAL' or report['mode'] != 'ASSISTED'):
                raise ValueError('Installed Compass conditional calculation or scope differs')
        source = folder/request['bundle']['documents'][0]['path']
        original = source.read_bytes()
        source.write_bytes(original+b'changed')
        try:
            try:
                service.assess(request, folder)
            except ValueError:
                pass
            else:
                raise ValueError('Installed service accepted mutated source')
        finally:
            source.write_bytes(original)
        questions[name] = report['questions']
    write(result_path, {'questions':questions, 'module_path':legalmath.__file__, 'prefix':sys.prefix,
        'sys_path':sys.path, 'real_instrument':'Compass conditional first coupon and BASF reviewed scalar occurrences/references; full contracts partial', 'independent_review':False})


if __name__ == '__main__':
    main()
