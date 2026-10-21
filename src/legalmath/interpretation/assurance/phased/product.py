"""Opt-in exact acquisition and independently admitted answer phases."""
from copy import deepcopy
from pathlib import Path
import json
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from ..bounded_context import require
from ..bounded_product import BoundedProduct, NOTE, AUDIT
from ..monitor import save
from .evidence_store import save_exact
from . import inventory, synthesis, group_review, context_bridge, warrant_groups
from .source_review import assignments
from .phase import execute


class PhasedProduct(BoundedProduct):
    def __init__(self, *args, phase_admit, phase_identity, downstream_instruction_profile=None,
                 downstream_capacity_profile=None, retained_preparation=None, **kwargs):
        from .downstream_input import CAPACITY_PROFILE
        require(downstream_capacity_profile in (None, CAPACITY_PROFILE),
            'Unknown downstream capacity selection', 'E_AUTHORITY')
        self.downstream_capacity_profile = downstream_capacity_profile
        super().__init__(*args, **kwargs)
        from . import downstream_instructions
        require(downstream_instruction_profile in (None, downstream_instructions.PROFILE),
            'Unknown downstream instruction profile', 'E_AUTHORITY')
        require(downstream_instruction_profile is None or self.downstream_input_profile is not None,
            'Downstream instructions require their input profile', 'E_AUTHORITY')
        self.downstream_instruction_profile = downstream_instruction_profile
        require(callable(phase_admit) and phase_identity, 'Missing phase execution binding', 'E_AUTHORITY')
        self.phase_admit, self.phase_identity = phase_admit, phase_identity
        self.current_dependencies = []
        self.prepared_checkpoint = None
        if retained_preparation is not None:
            from .prepared_checkpoint import load
            self.prepared_checkpoint = load(self, retained_preparation)
            checkpoint_path = self.directory / 'retained-preparation.json'
            if checkpoint_path.exists():
                require(json.loads(checkpoint_path.read_text()) == retained_preparation,
                    'Prepared checkpoint changed on resume', 'E_INTEGRITY')
            else:
                save_exact(checkpoint_path, retained_preparation)
            # A preparation with no new successful calls still supplies an
            # authenticated empty journal to independent downstream arms.
            journal_path = self.dispatch.directory / 'dispatch.json'
            if not journal_path.exists():
                save_exact(journal_path, {'input_hash': self.route.input_hash,
                    'maximum_calls': self.dispatch.maximum_calls, 'calls': {}})
        if downstream_capacity_profile is not None:
            require(self.downstream_input_profile is not None,
                'Capacity requires explicit downstream transport', 'E_AUTHORITY')
            save_exact(self.directory/'synthesis-resolution-options.json', {
                'downstream_capacity_profile': downstream_capacity_profile,
                'pair_search_maximum_frontier': 16})

    def request(self, task, *args, **kwargs):
        value = super().request(task, *args, **kwargs)
        from .downstream_input import TASKS
        if self.downstream_capacity_profile is not None and task in TASKS and task != 'SYNTHESIZE_FINDINGS':
            value['downstream_capacity_profile'] = self.downstream_capacity_profile
        return value

    def run_phase(self, name, calls):
        return execute(self, name, calls, implementation_identity=self.phase_identity,
                       admit=self.phase_admit)

    def prepare_calls(self, calls):
        """Apply guidance after original packing; keep retained successes exact."""
        if self.downstream_instruction_profile is None:
            return calls
        from ..integration_contract import read_evidence
        from . import downstream_instructions, synthesis_recovery, synthesis_catalog
        from .downstream_input import TASKS
        from .tool_input import TASKS as TOOL_TASKS
        checkpoint = None
        if self.dispatch.retained_initial:
            root, reference = self.dispatch.retained_initial
            combined = read_evidence(reference, root)
            if combined.get('profile') == synthesis_recovery.PROFILE:
                checkpoint = combined['synthesis']
        prepared, service_first = [], set()
        for call in calls:
            request = call['request']
            if request.get('task') not in TASKS or request.get('task') in TOOL_TASKS:
                prepared.append(call)
                continue
            revised = None
            if checkpoint is not None and call['key'].startswith('reduce-'):
                metadata = read_evidence(checkpoint, self.root)
                require(metadata.get('instruction_profile') == self.downstream_instruction_profile,
                    'Synthesis instruction scope differs from checkpoint', 'E_AUTHORITY')
                revised = synthesis_recovery.rewrite(self.root, checkpoint, call['key'], request,
                    call['schema'], self.route.input_hash, limits=self.route.limits)
                pointer = (synthesis_catalog.selected(self.root, checkpoint, call['key'], self.route.input_hash)
                    if metadata.get('profile') == synthesis_catalog.PROFILE else None)
                row = (read_evidence(pointer,self.root)['rows'][call['key']] if pointer
                    else metadata['rows'].get(call['key'], {}))
                if row.get('disposition') == 'CHARGED_NO_OUTPUT_FAILURE':
                    service_first.add(call['key'])
            if revised is None:
                revised = downstream_instructions.annotate(request)
            validate = call['validate']
            def checked(value, validate=validate, request=revised):
                downstream_instructions.validate_correction(request, value)
                validate(value)
            prepared.append({**call, 'request': revised, 'validate': checked})
        require(len(service_first) <= 1 or (checkpoint and
            read_evidence(checkpoint,self.root).get('profile') == synthesis_catalog.PROFILE),
            'More than one explicit service retry', 'E_AUTHORITY')
        return sorted(prepared, key=lambda call: call['key'] not in service_first)

    def install_dispatch_admission(self):
        original = self.dispatch.call
        self.dispatch._phase_original_call = original
        def call(key, request, schema, validator):
            # execute() uses _phase_original_call to avoid recursive phases.
            result = self.run_phase('call-' + key,
                [{'key': key, 'request': request, 'schema': schema, 'validate': validator}])
            if result['results']:
                return result['results'][0]['result']
            return result['resource_refusal']
        self.dispatch.call = call

    def investigate(self):
        raise LegalMathError('E_AUTHORITY', details='Phased answers require an explicitly retained acquisition')

    def reduce(self, qid, question, rows):
        if self.prepared_checkpoint is not None:
            from .prepared_checkpoint import findings
            return findings(self, qid, question, self.prepared_checkpoint)
        # answer() supplies the exact original acquisition; replace only the
        # redundant copies in its synthesis population, with audited mapping.
        rows, _ = synthesis.prepare(self, qid, self.retained_acquisition, self.retained_details)
        from .grouping import pack_items, contract_pair
        normalized = set()
        maximum_levels = len(rows) + 1
        large_capacity = False
        def build(group):
            request = self.request('SYNTHESIZE_FINDINGS', question, self.source_records(group),
                payload=group, expected=[r['id'] for r in group])
            if self.downstream_input_profile is not None:
                request['synthesis_scope'] = ('Produce a bounded source-supported synthesis for the original '
                    'question, preserving operative conditions, exceptions, supported alternatives and '
                    'unresolved dependencies. A single member is normalized once for subsequent combination. '
                    'This summary is a proposal: complete original accounts and sources remain separately '
                    'retained for independent answer review. Do not equate considered-ID coverage with '
                    'semantic completeness. State any unfinished analysis explicitly in unresolved.')
            if large_capacity:
                request['downstream_capacity_profile'] = self.downstream_capacity_profile
            return request
        level = 0
        while len(rows) > 1:
            large_capacity = False
            require(level < maximum_levels, 'Synthesis exceeded its finite progress bound', 'E_RESOURCE_LIMIT')
            def measure(group):
                request = build(group)
                if self.downstream_instruction_profile is not None:
                    from ..integration_contract import read_evidence
                    from . import synthesis_recovery, downstream_instructions, synthesis_catalog
                    retained = self.dispatch.retained_initial
                    historical_first = (level == 0 and retained is not None and
                        read_evidence(retained[1], retained[0]).get('profile') == synthesis_recovery.PROFILE)
                    if historical_first:
                        combined=read_evidence(retained[1],retained[0])
                        metadata=read_evidence(combined['synthesis'],self.root)
                        if metadata.get('profile') == synthesis_catalog.PROFILE:
                            historical_first = not metadata['first_level_instructions']
                    if not historical_first:
                        request = downstream_instructions.annotate(request)
                try:
                    return self.dispatch.measure(request, NOTE)
                except LegalMathError as exc:
                    if exc.code != 'E_RESOURCE_LIMIT':
                        raise
                    return None
            groups, blocked = pack_items(rows, measure, maximum_items=6)
            if blocked and self.downstream_capacity_profile is not None:
                large_capacity = True
                groups, blocked = pack_items(rows, measure, maximum_items=6)
            require(not blocked, 'Atomic finding cannot enter synthesis', 'E_RESOURCE_LIMIT')
            normalize = {i for i, g in enumerate(groups) if len(g['members']) == 1
                and g['members'][0]['id'] not in normalized and self.downstream_input_profile is not None}
            if len(groups) == len(rows) and not normalize and self.downstream_capacity_profile is not None:
                paired = contract_pair(rows, measure)
                if paired is not None:
                    groups = paired
                elif not large_capacity:
                    large_capacity = True
                    groups, blocked = pack_items(rows, measure, maximum_items=6)
                    require(not blocked, 'Atomic finding exceeds reviewed enlarged input', 'E_RESOURCE_LIMIT')
                    if len(groups) == len(rows):
                        groups = contract_pair(rows, measure) or groups
            require(len(groups) < len(rows) or normalize,
                'Synthesis cannot contract without losing support', 'E_RESOURCE_LIMIT')
            calls, carry = [], {}
            for i, group in enumerate(groups):
                members = group['members']
                if len(members) == 1 and i not in normalize:
                    carry[i] = members[0]
                    continue
                ids = [r['id'] for r in members]
                request = build(members)
                def check(value, ids=ids, records=request['records']):
                    require(len(value['considered']) == len(set(value['considered'])) and
                            set(value['considered']) == set(ids), 'Synthesis omitted an input')
                    self.citations(value, records)
                    require(value['support'] or value['unresolved'], 'Unsupported settled synthesis')
                calls.append({'key': f'reduce-{qid}-{level}-{i}', 'request': request,
                              'schema': NOTE, 'validate': check})
            phase = self.run_phase(f'reduction-{qid}-{level}', calls)
            require(phase['execution_complete'], 'Dependent synthesis failed', 'E_DEPENDENCY')
            outcomes = {r['key']: r['result'] for r in phase['results']}
            save_exact(self.directory / f'reduction-{qid}-{level}-membership.json', {
                'input_hashes': {r['id']: digest(r) for r in rows},
                'groups': [[r['id'] for r in g['members']] for g in groups],
                'normalized_singletons': sorted(normalize),
                'scope': 'Exact input membership only; summaries require original-source and account review.'})
            rows = [carry[i] if i in carry else {'id': f'reduce-{qid}-{level}-{i}',
                'value': outcomes[f'reduce-{qid}-{level}-{i}']['value'],
                'children': [r['id'] for r in g['members']]} for i, g in enumerate(groups)]
            normalized.update(r['id'] for i, r in enumerate(rows) if i not in carry)
            save_exact(self.directory / f'reduction-{qid}-{level}.json', rows)
            level += 1
        return rows

    def requirement_details(self):
        rows = (deepcopy(self.prepared_checkpoint[2]) if self.prepared_checkpoint is not None
            else super().requirement_details())
        if self.prepared_checkpoint is not None:
            save_exact(self.directory / 'requirement-details.json', rows)
        self.retained_details = rows
        exact = inventory.preserve(self)
        save_exact(self.directory / 'exact-inventory.json', exact)
        for qid in self.active_questions:
            relevant = [r for r in rows if self.applicable(self.route.records[r['id']], qid)]
            inventory.require_complete_accounts(self, exact, relevant, qid)
        return rows

    def answer(self, investigation, backend=None, *, preparation_only=False):
        self.retained_acquisition = investigation
        self.current_dependencies = investigation.get('discovered_dependencies', [])
        return super().answer(investigation, backend, preparation_only=preparation_only)

    def audit_answer(self, qid, question, answer, details, *, prefix=''):
        # Source and dependency decisions have one complete population.
        # audit_dependencies returns no second copy of those same decisions.
        reviews = group_review.run(self, qid, question, answer, self.current_dependencies,
            implementation_identity=self.phase_identity, admit=self.phase_admit, prefix=prefix)
        items = {r['id']: r for r in assignments(self, qid, self.current_dependencies)}
        for index, review in enumerate(reviews):
            if review.get('status') != 'VALIDATED' or review['value']['verdict'] != 'UNRESOLVED':
                continue
            needs = review['value'].get('context_needs', [])
            if not needs or any(n['kind'] != 'SOURCE_TEXT' for n in needs):
                continue
            item = items[review['value']['considered'][0]]
            bridge = context_bridge.review(self, qid, question, answer, item, review, needs,
                                          prefix=prefix, admit=self.phase_admit)
            # Failed bridge cannot erase its original unresolved decision.
            if bridge['result']['status'] == 'VALIDATED':
                reviews[index] = {**bridge['result'], 'context_continuation': bridge}
            else:
                reviews[index] = {**review, 'context_continuation': bridge}
        for i, detail in enumerate(details):
            material = {'answer': answer, 'requirement': self.route.records[detail['id']],
                        'detailed_account': detail['result']['value']}
            try:
                outcome = self.note(prefix + f'audit-requirement-{qid}-{i}',
                    'AUDIT_ANSWER_AND_DETAILED_ACCOUNT', question, self.source_records(material),
                    material, [detail['id']], audit=True)
            except Exception as exc:
                outcome = self.failure(exc)
            reviews.append(outcome)
        return reviews

    def audit_dependencies(self, *args, **kwargs):
        return []  # Included individually in audit_answer's verified population.

    def review_warrants(self, qid, question, answer, reviews, details):
        groups = warrant_groups.group(reviews)
        save_exact(self.directory / f'correction-{qid}-warrant-membership.json', groups)
        grouped = [r['review'] for r in groups]
        assessed, warranted, settled = super().review_warrants(qid, question, answer, grouped, details)
        expanded = []
        for assessment in assessed:
            for original in groups[assessment['review_index']]['originals']:
                expanded.append({**deepcopy(assessment), 'review_index': original['index'],
                    'original_review_hash': original['sha256'],
                    'shared_assessment_index': assessment['review_index']})
        save_exact(self.directory / f'correction-{qid}-warrants-expanded.json', expanded)
        return expanded, warranted, settled

    def review_population_identity(self, reviews):
        return {'sha256': digest([digest(r) for r in reviews]),
                'hash_method': 'ordered-individual-review-digests'}
