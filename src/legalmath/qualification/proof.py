"""Regenerate and kernel-check formal-expression to shared-model preservation.

The independent parser below never calls the production expression parser or
reading_program. A certificate proves constructor preservation, universally over
semantics and input contexts; it does not prove a legal reading or backend code.
"""
import json
from copy import deepcopy
from pathlib import Path
import re
import subprocess

from ..canonical import canonical, digest, raw_digest
from ..errors import LegalMathError
from ..translation.model import validate

LEAN = Path('/home/chakwong/.elan/toolchains/leanprover--lean4---v4.20.0/bin/lean')
PRELUDE = Path(__file__).with_name('Lowering.lean')
PROFILE = 'shared.constructor-preservation.v1'
SCOPE = {
    'proved': 'The independently parsed formal proposal and typed shared model have identical constructor trees; every interpretation of those constructors yields the same result for every input context.',
    'assumptions': ['The specified constructor meanings and factual interface are the premises.',
                    'The independent parser and tree encoder implement the declared normalization.'],
    'excludes': ['Natural-language meaning', 'Source completeness', 'Fact classification',
                 'Catala or RuleIR lowering', 'Compiler/JVM/codec correctness',
                 'Time/evidence selection', 'Unknown future legal documents'],
}


def unsupported(detail):
    raise LegalMathError('E_UNSUPPORTED_PROFILE', details=detail)


def parse(text):
    """Stack parser separate from translation.expressions, with bounded input."""
    if not isinstance(text, str) or len(text.encode()) > 64000:
        unsupported('Formal expression size')
    tokens = re.findall(r'\(|\)|[^\s()]+', text)
    if not 0 < len(tokens) <= 1000:
        unsupported('Formal expression token budget')
    stack = [[]]
    for token in tokens:
        if token == '(':
            stack.append([])
            if len(stack) > 34:
                unsupported('Formal expression depth')
        elif token == ')':
            if len(stack) == 1 or not stack[-1]:
                unsupported('Malformed formal expression')
            item = stack.pop(); stack[-1].append(item)
        else:
            stack[-1].append(token)
    if len(stack) != 1 or len(stack[0]) != 1:
        unsupported('Malformed formal expression')
    return stack[0][0]


def node(name, *children):
    return (name, list(children))


def source_tree(item, facts, bound=()):
    if isinstance(item, str):
        if item in ('true', 'false'):
            return node('literal.bool', item)
        if item in bound:
            return node('var', item)
        if item in facts:
            return node('fact', item)
        unsupported('Unbound source name: ' + item)
    if not item or not isinstance(item[0], str):
        unsupported('Malformed source operator')
    op, *args = item
    convert = lambda x: source_tree(x, facts, bound)
    if op in ('integer', 'money_hkd') and len(args) == 1:
        if not isinstance(args[0], str) or not re.fullmatch(r'-?(0|[1-9][0-9]*)', args[0]):
            unsupported('Noncanonical integer')
        return node('literal.' + op, args[0])
    if op in ('fact', 'rule') and len(args) == 1 and isinstance(args[0], str):
        if op == 'fact' and args[0] not in facts:
            unsupported('Unknown fact')
        return node(op, args[0])
    arities = {'not': 1, '+': 2, '-': 2, '=': 2, '>': 2, '>=': 2, 'if': 3}
    names = {'+': 'add', '-': 'sub', '=': 'eq', '>': 'gt', '>=': 'ge', 'and': 'all', 'or': 'any'}
    if (op in arities and len(args) == arities[op]) or (op in ('and', 'or') and args):
        return node(names.get(op, op), *map(convert, args))
    if op == 'scale' and len(args) == 3:
        if any(not isinstance(x, str) or not re.fullmatch(r'-?(0|[1-9][0-9]*)', x) for x in args[1:]):
            unsupported('Malformed exact scale')
        return node('scale', convert(args[0]), args[1], args[2])
    if op == 'call' and args and isinstance(args[0], str):
        return node('call', args[0], *map(convert, args[1:]))
    if op == 'default' and args:
        exceptions = []
        for ex in args[1:]:
            if not isinstance(ex, list) or len(ex) != 4 or ex[0] != 'exception' or not isinstance(ex[1], str):
                unsupported('Malformed exception')
            exceptions.append(node('exception', ex[1], convert(ex[2]), convert(ex[3])))
        return node('default', convert(args[0]), *exceptions)
    unsupported('No registered constructor proof for ' + str(op))


def model_tree(n):
    op = n['op']; one = lambda k: model_tree(n[k])
    if op == 'literal' and n['type'] in ('bool', 'integer', 'money_hkd'):
        value = ('true' if n['value'] else 'false') if n['type'] == 'bool' else n['value']
        return node('literal.' + n['type'], value)
    if op in ('fact', 'var', 'rule'):
        return node(op, n['name'])
    if op in ('all', 'any'):
        return node(op, *map(model_tree, n['args']))
    if op == 'not':
        return node(op, one('arg'))
    if op in ('add', 'sub', 'compare'):
        return node(n['cmp'] if op == 'compare' else op, one('left'), one('right'))
    if op == 'if':
        return node(op, one('condition'), one('then'), one('else'))
    if op == 'scale':
        return node(op, one('arg'), n['numerator'], n['denominator'])
    if op == 'call':
        return node(op, n['name'], *map(model_tree, n['args']))
    if op == 'default':
        return node(op, one('base'), *(node('exception', x['exception_id'], model_tree(x['guard']), model_tree(x['value'])) for x in n['exceptions']))
    unsupported('No registered constructor proof for ' + str(op))


def trees(model, formal):
    facts = [f['name'] for f in model['facts']]
    if [(f['name'], f['type']) for f in formal['facts']] != [(f['name'], f['type']) for f in model['facts']]:
        raise LegalMathError('E_INTEGRITY', details='Proof factual interfaces differ')
    if model['types'] or any(f['type'] not in ('bool', 'integer', 'money_hkd') for f in model['facts']):
        unsupported('This constructor proof covers Boolean/integer/money syntax')
    if formal.get('version') == '2':
        outputs, helpers = formal['outputs'], formal['helpers']
    else:
        outputs = [{'id': 'selected.control', 'result_type': formal['result_type'], 'scope': formal['scope'], 'result': formal['result']}]
        helpers = []
    if [(x['id'], x['result_type']) for x in outputs] != [(r['id'], r['type']) for r in model['rules']]:
        raise LegalMathError('E_INTEGRITY', details='Proof outputs differ')
    if [(h['name'], h['parameters'], h['result_type']) for h in helpers] != [(h['name'], h['parameters'], h['type']) for h in model.get('helpers', [])]:
        raise LegalMathError('E_INTEGRITY', details='Proof helper interfaces differ')
    left = [node('output', x['id'], x['result_type'], source_tree(parse(x['scope']), facts), source_tree(parse(x['result']), facts)) for x in outputs]
    right = [node('output', x['id'], x['type'], model_tree(x['scope']), model_tree(x['body'])) for x in model['rules']]
    for a, b in zip(helpers, model.get('helpers', [])):
        parameters = [node('parameter', p['name'], p['type']) for p in a['parameters']]
        left.append(node('helper', a['name'], a['result_type'], node('parameters', *parameters), source_tree(parse(a['body']), facts, [p['name'] for p in a['parameters']])))
        right.append(node('helper', b['name'], b['type'], node('parameters', *parameters), model_tree(b['body'])))
    return node('program', *left), node('program', *right)


def encode(tree):
    if isinstance(tree, str):
        # Validated identifiers/numerals only; no caller-supplied Lean syntax.
        if not re.fullmatch(r'[a-zA-Z0-9_.:-]+', tree):
            unsupported('Unencodable constructor atom')
        return '(Tree.atom ' + json.dumps(tree) + ')'
    return '(Tree.node ' + json.dumps(tree[0]) + ' [' + ', '.join(map(encode, tree[1])) + '])'


def produce(model, directory, *, formalization=None, lean=LEAN):
    m, _ = validate(model)
    reading = m['review']['reading']
    formal = formalization if formalization is not None else reading['formalization'] if reading else None
    if formal is None:
        unsupported('No retained formal proposal; authored expected answers are not a proof')
    source, target = trees(m, formal)
    source_text = PRELUDE.read_text() + '\nopen LegalMathSharedLowering\n'
    source_text += 'def proposed : Tree := ' + encode(source) + '\n'
    source_text += 'def lowered : Tree := ' + encode(target) + '\n'
    source_text += ('theorem translation_preserved {Context Value : Type} '
                    '(interpret : Context → Tree → Value) (context : Context) :\n'
                    '  interpret context proposed = interpret context lowered := by\n'
                    '  apply preservation\n  rfl\n#print axioms translation_preserved\n')
    work = Path(directory); work.mkdir(parents=True, exist_ok=True)
    path = work/'Translation.lean'; path.write_text(source_text)
    run = subprocess.run([str(lean), str(path.resolve())], capture_output=True, text=True, timeout=60, cwd=work)
    log = run.stdout + run.stderr; (work/'lean.log').write_text(log)
    if run.returncode or 'sorry' in log or 'depends on axioms' in log or 'does not depend on any axioms' not in log:
        raise LegalMathError('E_INTEGRITY', details='Lean rejected the preservation proposition')
    result = {'profile': PROFILE, 'model_hash': digest(m), 'formalization_hash': digest(formal),
              'status': 'KERNEL_CHECKED', 'scope': deepcopy(SCOPE),
              'tool_sha256': raw_digest(Path(lean).read_bytes()),
              'checker_sha256': raw_digest(Path(__file__).read_bytes()),
              'prelude_sha256': raw_digest(PRELUDE.read_bytes()),
              'proof_sha256': raw_digest(source_text.encode()), 'log_sha256': raw_digest(log.encode()),
              'human_quality_evidence': False, 'legal_correctness': 'NOT_ESTABLISHED'}
    (work/'certificate.json').write_bytes(canonical(result))
    return result


def verify(certificate, model, directory, *, formalization=None, lean=LEAN):
    # Never execute imported proof text, commands or asserted checker outcomes.
    checked = produce(model, directory, formalization=formalization, lean=lean)
    if certificate != checked:
        raise LegalMathError('E_INTEGRITY', details='Certificate identity or proposition changed')
    return checked
