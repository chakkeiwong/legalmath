"""Current full-consumer comparisons against immutable finite component evidence.

Validation helpers are repository code; legalmath must already be imported from
the intended source or installed package before this module is loaded.
"""
import gzip
import importlib
import json
from pathlib import Path
import sys
from legalmath.prospectus.execution_authority import REL, read, file_hash
from legalmath.prospectus.successor.contracts import digest

COMPONENTS = {
    'comparative': ('source-bes-dep-06', 'attempt-010', 'comparative-accounting-basis', 'prospectus_comparative_production'),
    'pension': ('basf-references', 'attempt-009', 'pension-rounding', 'prospectus_pension_reconciliation'),
    'cash-flow': ('source-bes-dep-07', 'attempt-010', 'individual-cash-flow', 'prospectus_bes_cash_flow'),
    'h1-unit': ('source-bes-dep-05', 'attempt-017', 'individual-unit-conflict', 'prospectus_h1_unit_integration'),
    'quantity': ('finance-conventions', 'attempt-004', 'exact-quantity-refusal', 'prospectus_exact_quantity'),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def same(actual, expected, label):
    require(digest(actual) == digest(expected), 'Complete retained evidence differs: '+label)


def helper(root, kind):
    require(kind in COMPONENTS, 'Unknown finite component')
    module = importlib.import_module('scripts.'+COMPONENTS[kind][3])
    # Historical helpers pin source imports for their own commands. The installed
    # worker imports legalmath first; remove these search paths before evaluation.
    source = (Path(root)/'src').resolve()
    sys.path[:] = [p for p in sys.path if Path(p or '.').resolve() != source]
    return module


def baseline(root, kind):
    task, attempt, _, _ = COMPONENTS[kind]
    return Path(root)/REL/'attempts'/task/attempt


def prepare_controls(root, kind):
    if kind not in ('comparative', 'h1-unit'):
        return None
    h = helper(root, kind); fixture = load(Path(root)/h.FIXTURE)
    cases = h.control_helpers(root)
    if kind == 'comparative':
        value = h.basis.evaluate(fixture['graph'], fixture['baseline'], fixture['profile'], root,
            expected_profile_sha256=digest(fixture['profile']))
        prose = h.basis.explain(value)
    else:
        value = h.unit.evaluate(fixture['graph'], fixture['prior'], fixture['profile'], root,
            expected_profile_sha256=digest(fixture['profile']))
        prose = h.unit.explain(value)
    return {'kind':kind, 'fixture_sha256':file_hash(Path(root)/h.FIXTURE),
        'profiles':[{'case':name, 'value':cases.profile_change(fixture['profile'],name)} for name in cases.PROFILE_CASES],
        'outputs':[{'case':name, 'value':list(cases.output_change(value,prose,name))} for name in cases.OUTPUT_CASES]}


def packet_controls(root, kind, packet):
    h = helper(root,kind); f = load(Path(root)/h.FIXTURE)
    require(packet['kind'] == kind and packet['fixture_sha256'] == file_hash(Path(root)/h.FIXTURE), 'Wrong adverse-input packet')
    if kind == 'comparative':
        evaluate = lambda p:h.basis.evaluate(f['graph'],f['baseline'],p,root,expected_profile_sha256=digest(p))
        verify = lambda a,e:h.verify(a,e,f['profile'],f['graph'],f['baseline'],f['original'],f['sources'],root,f['prose_sha256'])
    else:
        evaluate = lambda p:h.unit.evaluate(f['graph'],f['prior'],p,root,expected_profile_sha256=digest(p))
        verify = lambda a,e:h.verify(a,e,f['profile'],f['graph'],f['prior'],f['original'],root)
    rows = []
    for row in packet['profiles']:
        try: evaluate(row['value'])
        except ValueError: rows.append({'case':'repinned-profile:'+row['case'],'rejected':True})
        else: raise ValueError('Altered source profile accepted: '+row['case'])
    def outputs(checker):
        result = []
        for row in packet['outputs']:
            try: checker(*row['value'])
            except ValueError: result.append({'case':'output:'+row['case'],'rejected':True})
            else: raise ValueError('Incorrect output accepted: '+row['case'])
        return result
    rows += outputs(verify)
    caught = False
    try: outputs(lambda *_:True)
    except ValueError as exc: caught = str(exc).startswith('Incorrect output accepted:')
    require(caught,'Permissive checker undetected')
    return {'cases':rows,'permissive_checker_detected':True}


def evaluate(root, kind, packet=None):
    root = Path(root); h = helper(root,kind); old = baseline(root,kind)
    outputs = read(old/'outputs.json')
    # The orchestrator authenticates this manifest against its original event.
    # The evaluator independently verifies every recorded payload it reads.
    def retained(name):
        require(name in outputs and file_hash(old/name) == outputs[name], 'Changed original output: '+name)
        return load(old/name)
    if kind in ('comparative','h1-unit'):
        delta, proof, composition = h.evaluate_result(root)
        controls = packet_controls(root,kind,packet)
        for name,value in [('answer-delta.json.gz',delta),('verification.json',proof),
                           ('composition.json',composition),('controls.json',controls)]:
            same(value,retained(name),name)
        return {'component':kind,'whole_normal_answer_sha256':composition['normal_answer_sha256'],
            'delta_sha256':digest(delta),'proof_sha256':digest(proof),'composition_sha256':digest(composition),
            'controls_sha256':digest(controls),'control_count':len(controls['cases']),
            'complete_baseline_preserved':True}
    if kind == 'quantity':
        actual = h.actual_checks(); same(actual,retained('actual-checks.json.gz'),'all financial checks')
        return {'component':kind,'complete_checks_sha256':digest(actual),
            'full_valid_comparisons':actual['full_valid_comparisons'],'actual_refusals':actual['actual_refusals'],
            'complete_baseline_preserved':True}
    if kind == 'pension':
        values = h.inputs(root); graph = values[0]['P1']['payload']['graph']; profile = retained('profile.json')
        same(profile,h.make_profile(root,values[0],values[-1]),'original pension profile')
        same(h.consume(root,values),values[-1],'unconfigured pension consumer')
        actual = h.consume(root,values,profile); same(actual,retained('consumer.json.gz'),'entire pension consumer')
        proof = h.verify(actual,values[-1],profile,graph)
        controls = h.controls(actual,values[-1],profile,graph,root)
        same(proof,retained('verification.json'),'pension oracle'); same(controls,retained('controls.json'),'pension controls')
        return {'component':kind,'whole_normal_answer_sha256':digest(actual),'proof_sha256':digest(proof),
            'controls_sha256':digest(controls),'control_count':len(controls['controls']),'complete_baseline_preserved':True}
    if kind == 'cash-flow':
        ps = h.products(root); profile = retained('profile.json'); graph = ps['P1']['payload']['graph']
        same(profile,h.make_profile(root,graph),'cash-flow profile')
        before = h.load(root/h.NORMAL/'candidate-answer.json.gz')
        same(h.service.consume(ps,root,mode='frozen',include_artifacts=True),before,'unconfigured cash-flow answer')
        revised = h.updated(ps,profile); actual = h.service.consume(revised,root,mode='frozen',include_artifacts=True)
        h.verify_answer(actual,before,revised); delta = retained('normal-answer-delta.json.gz')
        same(actual,{**before,**delta},'entire cash-flow answer')
        fixture = h.load(root/h.FIXTURE)
        same(fixture['original_units'],h.load(root/h.PRIOR/'source-units.json.gz'),'cash-flow source fixture')
        same(fixture['original_reading'],h.load(root/h.PRIOR/'profile.json.gz')['reading'],'cash-flow reading fixture')
        proof = h.verify_review(actual[h.production.ADDED],profile,graph,fixture['original_reading'],fixture['original_units'],root)
        controls = h.controls(root,fixture)
        same(proof,retained('verification.json'),'cash-flow oracle'); same(controls,retained('controls.json'),'cash-flow controls')
        composition = retained('composition.json'); normal_hash = digest(actual)
        require(composition['normal_answer_sha256'] == normal_hash,'Whole cash-flow digest changed')
        del actual,before,ps,revised,graph
        prior = h.reconstruct(root,composition['prior_composition'])
        require(digest(prior) == composition['prior_answer_sha256'] and
            digest({**prior,h.production.ADDED:delta[h.production.ADDED]}) == composition['complete_composed_answer_sha256'],
            'Entire prior cash-flow composition changed')
        return {'component':kind,'whole_normal_answer_sha256':normal_hash,'proof_sha256':digest(proof),
            'composition_sha256':digest(composition),'controls_sha256':digest(controls),
            'control_count':len(controls['controls']),'complete_baseline_preserved':True}
    raise ValueError('Unimplemented component')
