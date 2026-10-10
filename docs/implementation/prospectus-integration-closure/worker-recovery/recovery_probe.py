"""Actual isolated closure-executor probe, also callable for clean recomputation."""
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[2]
REL = Path('docs/implementation/prospectus-integration-closure/inputs/R0/cases')
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import service  # noqa: E402
from legalmath.prospectus.successor.contracts import read, write  # noqa: E402


def evaluate(output):
    if not Path(service.__file__).resolve().is_relative_to((ROOT / 'src').resolve()):
        raise RuntimeError('Isolated executor imported another checkout')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cases = ROOT / REL
    result = {}
    for name in ('scan', 'annotation'):
        case = cases / name
        request = read(case / 'request.json')
        if name == 'annotation':
            decoded_path = output.with_name(output.stem + '-decoded.json')
            argv = ['/tmp/prospectus-adoption-tools/bin/python',
                str(ROOT / 'scripts/prospectus_integration_codec.py'), 'admit',
                str(case / 'source.json'), str(case / 'authored.xmi'), str(decoded_path),
                '--types', str(case / 'TypeSystem.xml')]
            run = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                timeout=30, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'})
            if run.returncode:
                result[name] = {'error': 'AnnotationCodecError: ' +
                    (run.stderr.strip().splitlines()[-1] if run.stderr.strip() else 'no stderr')}
                continue
            packet = read(decoded_path)['packet']
            request['annotation_admission']['packets'][0]['packet'] = packet
        try:
            report = service.assess(request, case)
        except (ValueError, FileNotFoundError) as exc:
            result[name] = {'error': type(exc).__name__ + ': ' + str(exc)}
        else:
            result[name] = {'report': report}
            if name == 'annotation':
                result[name]['decoded_packet'] = packet
    write(output, result)
    return result


def test_actual_assessment(pytestconfig):
    evaluate(Path(pytestconfig.option.xmlpath).with_name('assessment.json'))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Provide one output path')
    evaluate(sys.argv[1])
