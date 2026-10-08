"""Deliver only verified, inspected local documents and preserve qualified results."""
from pathlib import Path
from zipfile import ZipFile
import shutil

from run_assurance_new_grant import ROOT, OUT, PHASES, GRANT, read, sha, ref, state, checked, save, now


def run():
    from legalmath.interpretation.assurance.grants import GrantedAllowance
    from run_executable_reference_master import material
    receipts = {name: state()['phases'][name][-1] for name in PHASES}
    phases = {name: checked(receipt) for name, receipt in receipts.items()}
    if any(p['status'] != 'PASSED' for p in phases.values()): raise RuntimeError('Incomplete phase')
    final = phases['F4']['result']; directory = (ROOT/receipts['F4']['path']).parent
    snapshot = Path(final['snapshot']); frozen = read(directory/'snapshot.json')['inputs']
    review = read(OUT/'rendered-review.json')
    if review['status'] != 'INSPECTED_NO_CONFIRMED_LAYOUT_DEFECT': raise RuntimeError('Inspect the rendered addition')
    for name in ('monograph.pdf', 'technical-companion.pdf', 'process-guide.pdf'):
        if review['pdf_hashes'][name] != sha(directory/'documents'/name): raise RuntimeError('Different inspected PDF')
    if not (OUT/'future-window-result.json').is_file(): raise RuntimeError('Freeze the tested future method first')
    # Frozen source identity, not elapsed time or a passing label, governs delivery.
    changed = sorted(name for name, h in frozen.items() if not (ROOT/name).is_file() or sha(ROOT/name) != h)
    added = sorted(set(material(ROOT))-set(frozen))
    document_changes = [name for name in changed+added if name.startswith('docs/monograph/') and Path(name).suffix in ('.tex', '.bib')]
    if document_changes: raise RuntimeError('Manuscript changed after verification: '+str(document_changes))
    protected = read(OUT/'manuscript-before.json')
    archive = OUT/'manuscript-before.zip'
    if sha(archive) != protected['archive_sha256']: raise RuntimeError('Protected baseline archive changed')
    preservation = []; missing = []
    with ZipFile(archive) as prior:
        for name in prior.namelist():
            if not (ROOT/name).is_file(): missing.append(name); continue
            old = prior.read(name).decode().splitlines(); new = (ROOT/name).read_text().splitlines()
            iterator = iter(new)
            intact = all(any(candidate == line for candidate in iterator) for line in old)
            preservation.append({'path': name, 'all_prior_lines_retained_in_order': intact,
                                 'changed': old != new})
    if missing or not all(row['all_prior_lines_retained_in_order'] for row in preservation):
        save(OUT/'preservation-review-needed.json', {'missing': missing, 'files': preservation})
        raise RuntimeError('Inspect every removed or reordered substantive manuscript line')
    selection = read(ROOT/read(OUT/'selection.json')['path'])
    for receipt in selection['old_grants']+[arm['receipt'] for arm in selection['arms']]:
        if sha(ROOT/receipt['path']) != receipt['sha256']: raise RuntimeError('Historical allowance changed')
    prior_remaining = set(map(tuple, selection['previously_incomplete']))
    new_pairs = set(); unassessed = set(); disputes = []; excluded = []
    scoped_refs = []
    for name in ('F1-pilot', 'F1-breadth'):
        result = phases[name]['result']['result']
        new_pairs.update(tuple(p) for b in result['batches'] if not b['missing_perspectives'] for p in b['required_pairs'])
        unassessed.update(map(tuple, result['pairs_with_unassessed_dimensions']))
        disputes += [d for b in result['batches'] if b['reconciliation'] for d in b['reconciliation']['disputes']]
        path = (ROOT/receipts[name]['path']).parent
        if name == 'F1-breadth': path = (ROOT/phases[name]['result']['prior']['path']).parent
        excluded += read(path/'dispatch-eligibility.json')['excluded_original_limit']
        scoped_refs.append(ref(path/'scoped/result.json'))
    if not new_pairs <= prior_remaining: raise RuntimeError('Changed selected denominator')
    remaining = prior_remaining-new_pairs
    if remaining != set(map(tuple, excluded)): raise RuntimeError('Lost excluded pair')
    old_used = read(ROOT/selection['prior_slice']['path'])['reservations']
    continued = read(OUT/'ucits-ensemble-allowance.json')['reservations']
    if len(old_used)+len(continued) > 120: raise RuntimeError('Original arm exceeded')
    book = ROOT/'docs/monograph'; proposal = ROOT/'docs/proposal'
    for name in ('monograph.pdf', 'technical-companion.pdf', 'process-guide.pdf'):
        shutil.copy2(directory/'documents'/name, book/name)
    for source, target in (('monograph.pdf', 'proposal.pdf'), ('monograph.pdf', 'monograph.pdf'),
                           ('technical-companion.pdf', 'technical-companion.pdf')):
        shutil.copy2(book/source, proposal/target)
    for name in ('document-check.json', 'hierarchy.json', 'page-inventory.json', 'rendered-text.txt'):
        shutil.copy2(snapshot/'docs/monograph/review'/name, book/'review'/name)
    documents = {str(p.relative_to(ROOT)): sha(p) for p in
        [book/'monograph.pdf', book/'technical-companion.pdf', book/'process-guide.pdf',
         proposal/'proposal.pdf', proposal/'monograph.pdf', proposal/'technical-companion.pdf']}
    save(OUT/'manuscript-preservation.json', {'status': 'PRIOR_CONTENT_RETAINED',
        'baseline': ref(archive), 'files': preservation, 'prior_files': len(preservation),
        'removed_lines': 0, 'scope': 'Exact old source lines retained in order; not a readability or legal quality certification.'})
    grant = GrantedAllowance(GRANT).verify()
    result = {'status': 'ENGINEERING_INCREMENT_EXECUTED_WITH_RETAINED_UNCERTAINTY', 'at': now(),
        'phase_receipts': receipts, 'grant': grant, 'remaining_calls': grant['maximum']-grant['used'],
        'historical_allowances_unchanged': True, 'tested_source_archive': ref(directory/'tested-inputs.zip'),
        'regression': final['regression'], 'tested_snapshot': str(snapshot),
        'workspace_changes_after_snapshot': changed, 'workspace_additions_after_snapshot': added,
        'page_counts': final['page_counts'], 'published_documents': documents,
        'rendered_review': ref(OUT/'rendered-review.json'),
        'preservation': ref(OUT/'manuscript-preservation.json'),
        'ucits': {'original_pairs': selection['original_denominator'], 'prior_two_perspectives': 165,
            'new_two_perspectives': len(new_pairs), 'total_two_perspectives': 165+len(new_pairs),
            'new_four_dimensions_assessed': len(new_pairs-unassessed),
            'remaining_pairs': sorted(remaining), 'deadline_exclusions': excluded,
            'new_disputes_or_unresolved': len(disputes),
            'new_pairs_with_disagreeing_dimensions': sum(bool(d['disagreeing_dimensions']) for d in disputes),
            'historical_disputes_retained': 42, 'task_calls': len(old_used)+len(continued),
            'task_maximum': 120, 'evidence': scoped_refs,
            'breadth_identity': 'RETAINED_RESPONSES_RECHECKED; ORIGINAL_SHARED_METHOD_CHANGED'},
        'table_diagnostic': phases['F2-table-identity']['result'],
        'source_revision': {'evidence': receipts['F2-source-repair'],
            'authority_questions': 6, 'legally_closed': 0},
        'future_window': ref(OUT/'future-window-result.json'),
        'historical_study_complete': False, 'legal_correctness': 'NOT_ESTABLISHED',
        'unknown_future_legal_generalization': 'NOT_ESTABLISHED', 'release_eligible': False,
        'next_phase_plan': 'docs/implementation/assurance-new-grant/next-phase-plan.md'}
    save(OUT/'final-report.json', result)
    save(OUT/'delivery-next-phase-plan.json', {'delivery': ref(OUT/'final-report.json'),
        'next': result['next_phase_plan'], 'remaining_calls': result['remaining_calls'],
        'original_issue_limits_preserved': True, 'real_future_observations': 0,
        'action': 'Admit genuinely later sources under the frozen full method; retain blocked capacity and missing-premise work without resets.'})
    notes = ROOT/'docs/implementation/assurance-new-grant'
    table_rows = '\n'.join('| '+role+' | '+str(len(value['addressed_concerns']))+' / '+
        str(value['total_concerns'])+' | '+str(value['accounting_complete'])+' | '+
        str(len(value['question_disagreements']))+' |' for role, value in result['table_diagnostic']['roles'].items())
    pages = result['page_counts']; regression = result['regression']
    (notes/'execution-result.md').write_text(f'''# Additional-grant execution result

The reviewed increment completed its engineering phases with retained
uncertainty. The frozen full regression passed **{regression['tests']} tests**,
with {regression['failures']} failures, {regression['errors']} errors and
{regression['skipped']} skips. The separate grant used **{grant['used']} / 500**
requests, leaving **{result['remaining_calls']}**. Both exhausted predecessor
ledgers and all original arm/deadline histories remain unchanged.

The [final report](../../../artifacts/assurance-new-grant/2026-09-29/final-report.json)
binds every phase receipt, the exact tested source archive, grant spending,
published PDFs and inspection. The monograph has **{pages['monograph.pdf']} pages**,
the technical companion **{pages['technical-companion.pdf']}**, and the illustrated
guide **{pages['process-guide.pdf']}**. The 275-file protected manuscript baseline
was checked for retention of its prior source lines in order. Page count and
successful compilation are not evidence of legal correctness or readability.

## What was executed

UCITS coverage increased from 165 to **223 of 225 claim–reading pairs** with two
validated perspectives. Fifty-eight additional pairs were processed; 42 of
those had all four dimensions assessed. The new records retain 20 unresolved
or disputed pairs, four with differing dimension judgments. The earlier 42
disputes remain historical evidence. Two original pairs expired and remain in
the full denominator. The ninth candidate still lacks a formal program.
The original UCITS task has used **109 / 120** calls.

One later UCITS follow-up lost its connection. Concurrent prospectus edits also
changed the shared package while that phase ran. Its original phase is retained
as FAILED. A separate offline recovery rechecked every returned response against
the original source, reading and question with zero new model calls. This does
not retroactively freeze or attest the original live execution. Later phases
use copied source trees, and final verification uses the archived repository.

Two complete-output table attempts timed out. Two smaller-output attempts
returned responses but exposed unsupplied individual question hashes. The
repair provides deterministic identity data, preserves the full context and
joins bounded answers without inventing missing concerns or changing their
judgments. All failures remain spent and rejected. Its final per-role accounting
is:

| Perspective | Concerns accounted for | Accounting complete | Differing question statuses between batches |
|---|---:|---|---:|
{table_rows}

These concerns were synthetic stress inputs over 263 actual source units.
Their accounting is not a legal accuracy experiment. Proposed explanations,
unresolved concerns, revisions and missing groups remain in the retained result.
No cross-batch semantic consistency is established by the joining check.

The joined 23EC52 circular and appendix were investigated using both fresh
perspectives and bounded follow-ups. The follow-up transport preserves all 177
units and prior proposals. It retains the distinction between available
appendix text and still-missing legislative/applicability premises. All six
authority questions remain legally unclosed. The eDDA and authentication
original inventories remain unfinished; the private-market arm remains 120/120.

The new whole-investigation observer binds actual method settings, provider
and spending identity, source processing, question/authority/scoped stages and
each candidate qualification. It re-executes the registered qualification
checks. Tests cover changed inputs/methods, Unicode journals, missing stages,
duplicate observations, repaired windows and incomplete dossiers. Admission
retains renamed duplicate source/questions and late encounters as ineligible.
A frozen future window now exists with **zero real observations**. Its method
is the tested snapshot, not a moving shared workspace.

## Evidence and decision

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Deliver this engineering increment | Frozen regression and retained-file checks passed | Earlier failures retained; current engineering checks passed | Untested source meanings and dependency assumptions | Use the tested method with explicit qualifications | Production/legal readiness |
| Retain the live interpretation proposals | Exact source/program references and full reported denominators checked | Two expired UCITS pairs, unassessed dimensions, disagreement and dispatch failure remain | Same-model shared interpretation errors | Investigate genuinely new source premises within declared limits | English interpretation proved |
| Retain the table diagnostic | Full-context identity and per-role accounting shown above | Timeouts and invalid identities remain in history | Synthetic concerns; semantic interactions unproved | Review optional integration on a new eligible task/method revision | General model comprehension |
| Freeze future observation rules | Whole-method API and admission rejection tests passed | Changed methods cannot enter the same confirmation window | No later-source observations; clocks and remote model un-attested | Admit genuinely later sources before any execution | Future-law generalization |

| Inference status | Finding |
|---|---|
| Hard veto screen | Invalid responses were rejected; expired issues and missing evidence were retained |
| Statistically supported ranking | None; no superiority or model-independence estimate was tested |
| Descriptive-only differences | Returned/assessed counts, timeouts, disagreements and elapsed times |
| Default-readiness | Diagnostic transport success does not make it a whole-dispatcher default |
| Next evidence needed | Eligible later sources under the unchanged frozen method; exact new legal premises and domain-specific formal propositions |

The strongest alternative explanation for apparent interpretation success is a
shared misunderstanding expressed in a valid response format. Exact quotations
and matching program executions do not exclude it. A new contradictory source,
failed native/proof check or changed method would require revising the scoped
engineering claim. Natural-language legal correctness and unrestricted future
generalization remain **NOT_ESTABLISHED**. No human quality labels or approval
gates were used. The [next plan](next-phase-plan.md) specifies the remaining work
without resetting an exhausted or expired issue.
''')
    return {k: result[k] for k in ('status', 'remaining_calls', 'regression', 'page_counts')}
