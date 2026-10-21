from pathlib import Path
root=Path.cwd()
work=root/'artifacts/legal-mission-control/2026-10-19/gap-preservation'
assert (work/'baseline.json').exists(), 'Freeze settled predecessor before editing'
def replace(path,old,new,count=1):
    p=root/path;text=p.read_text();assert text.count(old)==count,(path,text.count(old))
    p.write_text(text.replace(old,new))

replace('src/legalmath/interpretation/assurance/bounded_product.py',
'''                    require(value['source_gaps'] == request['account_correction']['required_source_gaps'],
                        'Account correction changed required document-qualified source gaps')''',
'''                    from .phased.account_gap_preservation import preserve
                    preserve(request['account_correction']['required_source_gaps'], value['source_gaps'])''')

replace('src/legalmath/interpretation/assurance/phased/account_receipt.py',
'''    config = checkpoint['account_recovery']''',
'''    from . import account_gap_preservation
    if entry.get('profile') == account_gap_preservation.PROFILE:
        return account_gap_preservation.checked(root, checkpoint, key, entry)
    config = checkpoint['account_recovery']''')
replace('src/legalmath/interpretation/assurance/phased/account_receipt.py',
'''    old, old_schema, value, measurement = checked(root, checkpoint, key, entry)''',
'''    from . import account_gap_preservation
    if entry.get('profile') == account_gap_preservation.PROFILE:
        return account_gap_preservation.retained(root, checkpoint, reference, key, request, schema,
            limits=limits, encode=encode)
    old, old_schema, value, measurement = checked(root, checkpoint, key, entry)''')

replace('src/legalmath/interpretation/assurance/phased/failure_recovery.py',
'''        if reason == NUMBERED:''',
'''        from . import account_gap_preservation
        entry = value.get('completed_account_receipts', {}).get(key)
        if entry and entry.get('profile') == account_gap_preservation.PROFILE:
            account_gap_preservation.checked(root, value, key, entry)
            category = 'REVIEWED_GAP_PRESERVATION_REASSESSMENT'
            actions[key] = 'REASSESS_COMPLETE_RESPONSE'
        elif reason == NUMBERED:''')

replace('scripts/legal_mission_execution.py',
'''    if program.get('failure_recovery'):''',
'''    if program.get('gap_preservation'):
        from scripts.legal_integration_gap_preservation import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('failure_recovery'):''')
replace('scripts/legal_mission_execution.py',
'''            if self.program.get('failure_recovery'):''',
'''            if self.program.get('gap_preservation'):
                from scripts.legal_integration_gap_preservation import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('failure_recovery'):''')
replace('scripts/legal_mission_execution.py',
'''        refresh = self.program.get('failure_recovery', refresh)''',
'''        refresh = self.program.get('failure_recovery', refresh)
        refresh = self.program.get('gap_preservation', refresh)''')

replace('scripts/legal_integration_phased_live.py',
'''def active_live(program):
    if program.get('failure_recovery'):''',
'''def active_live(program):
    if program.get('gap_preservation'):
        return Path(program['gap_preservation']['work']) / 'live'
    if program.get('failure_recovery'):''')
replace('scripts/legal_integration_phased_live.py',
'''def question_live(program, q):
    if program.get('failure_recovery') and q == 'p10':''',
'''def question_live(program, q):
    if program.get('gap_preservation') and q == 'p10':
        return Path(program['gap_preservation']['work']) / 'live'
    if program.get('failure_recovery') and q == 'p10':''')
replace('scripts/legal_integration_phased_live.py',
'''def common_directory(program, q):
    if program.get('failure_recovery') and q == 'p10':''',
'''def common_directory(program, q):
    if program.get('gap_preservation') and q == 'p10':
        from scripts.legal_integration_gap_preservation import completion
        done = completion()
        if done is not None:
            return Path(done['common_directory'])
    if program.get('failure_recovery') and q == 'p10':''')
replace('scripts/legal_integration_phased_live.py',
'''            from scripts.legal_integration_failure_recovery import completion
            done=completion()''',
'''            if program.get('gap_preservation'):
                from scripts.legal_integration_gap_preservation import completion
            else:
                from scripts.legal_integration_failure_recovery import completion
            done=completion()''')
replace('scripts/legal_integration_phased_live.py',
'''    if q=='p10' and read(ROOT/PROGRAM).get('failure_recovery'):''',
'''    if q=='p10' and read(ROOT/PROGRAM).get('gap_preservation'):
        from scripts.legal_integration_gap_preservation import acquire as recover_failed
        return recover_failed(q,service)
    if q=='p10' and read(ROOT/PROGRAM).get('failure_recovery'):''')

replace('scripts/legal_integration_master.py',
'''    if args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('failure_recovery'):''',
'''    if args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('gap_preservation'):
        from scripts.legal_integration_gap_preservation import verification
        result = verification()
    elif args.action == "verify" and (ROOT / PROGRAM).exists() and read(ROOT / PROGRAM).get('failure_recovery'):''')
replace('scripts/legal_integration_master.py',
'''        if (ROOT / Path('artifacts/legal-mission-control/2026-10-19/failure-recovery/local-result.json')).exists():''',
'''        if (ROOT / Path('artifacts/legal-mission-control/2026-10-19/gap-preservation/local-result.json')).exists():
            from scripts.legal_integration_gap_preservation import register
        elif (ROOT / Path('artifacts/legal-mission-control/2026-10-19/failure-recovery/local-result.json')).exists():''')
replace('scripts/legal_integration_master.py',
'''        if read(ROOT / PROGRAM).get('failure_recovery'):
            from scripts.legal_integration_failure_recovery import verification''',
'''        if read(ROOT / PROGRAM).get('gap_preservation'):
            from scripts.legal_integration_gap_preservation import verification
        elif read(ROOT / PROGRAM).get('failure_recovery'):
            from scripts.legal_integration_failure_recovery import verification''')

replace('scripts/legal_mission_control.py',
'''    else:
        master_state = None
    require(mission["current_task"] in tasks, "No current substantive task")''',
'''        gap_preservation = master.get('gap_preservation')
        if gap_preservation:
            require(gap_preservation.get('profile') == 'integration-gap-preservation.v1'
                and gap_preservation.get('prior_detours') == detours == 55
                and gap_preservation.get('additional_consolidated_revision') == 1
                and gap_preservation.get('additional_task_attempts') == 1
                and gap_preservation.get('reopened_nodes') == ['acquire-p10']
                and gap_preservation.get('maximum_passes') == 1
                and gap_preservation.get('live_calls_added') == 0
                and program.get('gap_preservation') == gap_preservation, 'Unreviewed gap preservation')
            require(any(r['id'] == 'integration-master-gap-preservation-2026-10-19'
                and gap_preservation['review'] in r['result_evidence'] for r in history), 'Missing gap-preservation history')
            verify_refs(root, gap_preservation)
            detours += 1
    else:
        master_state = None
    require(mission["current_task"] in tasks, "No current substantive task")''')
print('Patched explicit gap-preservation integration points.')
