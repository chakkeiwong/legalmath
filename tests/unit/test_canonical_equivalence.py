"""Equivalence of the optimized predicate, not a new serialization policy."""
import importlib.util
import hashlib
from pathlib import Path
import pytest
from legalmath import canonical as candidate
from legalmath.errors import BoundaryError

ROOT = Path('/home/chakwong/python/legalmath')
BASELINE=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure/canonical-baseline.py'
assert hashlib.sha256(BASELINE.read_bytes()).hexdigest()=='a109857dc69d6f666ab2a078515eefddce45f3d2205fa27a5ab77172be23bf31'
spec = importlib.util.spec_from_file_location('legalmath.canonical_baseline', BASELINE)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

def test_every_unicode_codepoint_has_identical_surrogate_membership():
    for code in range(0x110000):
        assert bool(candidate._SURROGATE.search(chr(code))) == (0xD800 <= code <= 0xDFFF)

@pytest.mark.parametrize('value', [None, True, 0, -1, candidate.LIMIT,
    {'a':['港😀', '\n\t', 1], 'z':[]}, 'x'*200000, chr(0xD7FF)+chr(0xE000),
    chr(0xD800), 'prefix'+chr(0xDFFF)+'suffix', 1.1, {'港':1}, candidate.LIMIT+1])
def test_original_bytes_and_errors(value):
    def outcome(module):
        try:return ('value', module.canonical(value))
        except BoundaryError as error:return ('error', error.code)
    assert outcome(candidate) == outcome(baseline)

@pytest.mark.parametrize('text', ['{"a":1,"a":2}', '1.0', '-0', 'NaN',
    '"\\ud800"', '{"a":[1,true,null,"港"]}', '"\\ud83d\\ude00"'])
def test_load_policy_unchanged(text):
    def outcome(module):
        try:return ('value', module.loads(text))
        except BoundaryError as error:return ('error', error.code)
    assert outcome(candidate) == outcome(baseline)

def test_depth_and_size_boundaries_unchanged(monkeypatch):
    deep = 1
    for _ in range(130): deep=[deep]
    for module in (baseline, candidate):
        with pytest.raises(BoundaryError): module.canonical(deep)
        monkeypatch.setattr(module, 'MAX_BYTES', 10)
        assert module.canonical('abcdefgh') == b'"abcdefgh"'
        with pytest.raises(BoundaryError): module.canonical('abcdefghi')
