"""Real retained extraction geometry must survive dossier composition exactly."""
import json
from pathlib import Path
import pytest
from legalmath.canonical import canonical,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integrated import diagnostic_numbers,source_processing_identity


def test_real_pdf_sidecar_report_has_a_lossless_diagnostic_view():
    path=Path(__file__).resolve().parents[2]/'artifacts/assurance-successor/2026-09-28/S1/attempt-01/appendix/output.json'
    raw=path.read_bytes();before=raw_digest(raw);original=json.loads(raw)
    with pytest.raises(LegalMathError):loads(raw)
    projected=diagnostic_numbers(original)
    assert loads(canonical(projected))==projected
    def compare(a,b):
        if type(a)is float:assert b==str(a)
        elif isinstance(a,dict):
            assert set(a)==set(b)
            for key in a:compare(a[key],b[key])
        elif isinstance(a,list):
            assert len(a)==len(b)
            for x,y in zip(a,b):compare(x,y)
        else:assert type(a)is type(b) and a==b
    compare(original,projected)
    assert raw_digest(path.read_bytes())==before


@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf')])
def test_invalid_diagnostics_are_rejected_instead_of_stringified(value):
    with pytest.raises(LegalMathError):diagnostic_numbers({'coordinate':[value]})


def test_diagnostic_representation_is_part_of_source_processing_identity(tmp_path):
    identity=source_processing_identity(tmp_path/'python')
    assert identity['profile']=='source-processing.v3'
    assert any(k.endswith('/integrated.py') for k in identity['files'])
