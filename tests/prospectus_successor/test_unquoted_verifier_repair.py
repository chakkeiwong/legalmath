"""A malformed report must be refused explicitly, never counted as a crash."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from scripts import prospectus_unquoted_verifier_oracle as oracle

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'


@pytest.fixture(scope='module')
def report():
    path = AUTH / 'attempts/basf-references/attempt-088/ordinary-answer.json.gz'
    return json.loads(gzip.decompress(path.read_bytes()))[oracle.KEY]


def test_valid_schema(report):
    oracle.shape(report)


@pytest.mark.parametrize('field', ['term', 'value', 'scope', 'condition'])
@pytest.mark.parametrize('bad', [None, [], '', 1])
def test_required_span_wrong_type_is_explicit_refusal(report, field, bad):
    changed = deepcopy(report)
    row = next(r for r in changed['candidates'] if r['kind'] == 'REFERENCE_EXPANSION')
    row[field] = bad
    # In particular, scope=None reproduced an uncaught TypeError in attempt088.
    with pytest.raises(AssertionError):
        oracle.shape(changed)


@pytest.mark.parametrize('field', ['term', 'value', 'scope', 'condition'])
@pytest.mark.parametrize('missing', ['start', 'end', 'raw', 'source_projection'])
def test_required_span_missing_field_is_explicit_refusal(report, field, missing):
    changed = deepcopy(report)
    row = next(r for r in changed['candidates'] if r['kind'] == 'REFERENCE_EXPANSION')
    del row[field][missing]
    with pytest.raises(AssertionError):
        oracle.shape(changed)


@pytest.mark.parametrize('bad', [None, [], '', 1])
def test_missing_candidate_is_explicit_refusal(report, bad):
    changed = deepcopy(report)
    changed['candidates'][0] = bad
    with pytest.raises(AssertionError):
        oracle.shape(changed)


@pytest.mark.parametrize('field', ['term', 'value', 'scope', 'condition'])
def test_boolean_offset_is_not_an_integer_offset(report, field):
    changed = deepcopy(report)
    row = next(r for r in changed['candidates'] if r['kind'] == 'REFERENCE_EXPANSION')
    row[field]['start'] = True
    with pytest.raises(AssertionError):
        oracle.shape(changed)


def test_missing_address_is_explicit_refusal(report):
    changed = deepcopy(report)
    next(r for r in changed['candidates'] if r['kind'] == 'PURPOSE_CONDITIONED_AMOUNT')['printed_scope_address'] = None
    with pytest.raises(AssertionError):
        oracle.shape(changed)


def test_missing_report_is_explicit_refusal():
    with pytest.raises(AssertionError):
        oracle.verify({}, {}, {}, {}, {})


@pytest.mark.parametrize('bad', [None, [], {}, 1, 'UNLISTED'])
def test_malformed_kind_is_explicit_refusal(report, bad):
    changed = deepcopy(report)
    changed['candidates'][0]['kind'] = bad
    with pytest.raises(AssertionError):
        oracle.shape(changed)


@pytest.mark.parametrize('field', ['candidates', 'issues', 'version'])
def test_missing_report_field_is_explicit_refusal(report, field):
    changed = deepcopy(report)
    del changed[field]
    with pytest.raises(AssertionError):
        oracle.shape(changed)


def test_changed_profile_identity_is_explicit_refusal(report):
    with pytest.raises(AssertionError, match='profile identity'):
        oracle.verify({oracle.KEY: report, 'report_sha256': '0' * 64}, {}, {}, {}, {})
