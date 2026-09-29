"""Bind an investigated question and reading to shared machine qualification."""
from pathlib import Path

from ...canonical import digest, loads, raw_digest
from ...errors import LegalMathError
from ...qualification import assurance
from ...translation.model import from_reading
from ..contracts import Packet, parse
from ..search.models import Reading
from .controls import check_controls
from .semantics import check_quotes
from .diversity import save

PROFILE = 'legalmath.investigation-qualification.v1'


def identity(packet, reading, question, assignment_status):
    parse(Packet, packet); parse(Reading, reading); check_quotes(reading['citations'], packet)
    check_controls([question], packet)
    if assignment_status not in ('PROPOSED', 'UNCERTAIN'): raise LegalMathError('E_SCHEMA')
    return {'profile': PROFILE, 'packet_hash': digest(packet), 'reading_hash': digest(reading),
            'question_hash': digest(question), 'assignment_status': assignment_status,
            'method_hash': digest(assurance.method_manifest()),
            'adapter_hash': raw_digest(Path(__file__).read_bytes())}


def run(packet, reading, question, cases, directory, jdk, at, *, assignment_status='PROPOSED', toolchain=None):
    bound = identity(packet, reading, question, assignment_status); assurance.check_cases(cases)
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    inputs = {'packet': packet, 'reading': reading, 'question': question, 'assignment_status': assignment_status,
              'cases': cases, 'at': at}
    save(directory/'inputs.json', inputs)
    if reading['formalization'] is None:
        summary = {'status': 'UNENCODED', 'formal_lowering': 'UNSUPPORTED', 'executed_target_cases': 0,
                   'legal_correctness': 'NOT_ESTABLISHED', 'unknown_future_legal_generalization': 'NOT_ESTABLISHED'}
        qualification = None
    else:
        model = from_reading(reading, packet, at)
        qualification = assurance.run(model, cases, directory/'machine', jdk, toolchain=toolchain)
        summary = qualification['summary']
    result = {'profile': PROFILE, 'identity': bound, 'inputs_hash': digest(inputs),
        'machine_report_hash': qualification['report_hash'] if qualification else None,
        'summary': summary, 'unresolved_premises': {
            'source_meaning': 'NOT_ESTABLISHED', 'complete_question_inventory': 'NOT_ESTABLISHED',
            'reading_answers_declared_question': assignment_status,
            'fact_classifications': reading['formalization']['facts'] if reading['formalization'] else [],
            'source_dependencies': packet['dependencies'], 'reading_assumptions': reading['assumptions'],
            'reading_questions': reading['questions']}, 'release_eligible': False}
    save(directory/'qualification.json', result)
    return result


def verify(directory, packet, reading, question, jdk, *, assignment_status='PROPOSED', compiler=None):
    directory = Path(directory); result = loads((directory/'qualification.json').read_bytes())
    if set(result) != {'profile', 'identity', 'inputs_hash', 'machine_report_hash', 'summary',
                       'unresolved_premises', 'release_eligible'}:
        raise LegalMathError('E_SCHEMA')
    inputs = loads((directory/'inputs.json').read_bytes())
    if (result['identity'] != identity(packet, reading, question, assignment_status) or
            result['inputs_hash'] != digest(inputs) or inputs['packet'] != packet or
            inputs['reading'] != reading or inputs['question'] != question or
            inputs['assignment_status'] != assignment_status or result['release_eligible'] is not False):
        raise LegalMathError('E_INTEGRITY')
    assurance.check_cases(inputs['cases'])
    if reading['formalization'] is not None:
        model = from_reading(reading, packet, inputs['at'])
        machine = assurance.verify(directory/'machine', model, jdk, compiler=compiler)
        if result['machine_report_hash'] != machine['report_hash'] or result['summary'] != machine['summary']:
            raise LegalMathError('E_INTEGRITY')
    elif result['machine_report_hash'] is not None or result['summary'] != {
            'status': 'UNENCODED', 'formal_lowering': 'UNSUPPORTED', 'executed_target_cases': 0,
            'legal_correctness': 'NOT_ESTABLISHED', 'unknown_future_legal_generalization': 'NOT_ESTABLISHED'}:
        raise LegalMathError('E_INTEGRITY')
    expected = {'source_meaning': 'NOT_ESTABLISHED', 'complete_question_inventory': 'NOT_ESTABLISHED',
        'reading_answers_declared_question': assignment_status,
        'fact_classifications': reading['formalization']['facts'] if reading['formalization'] else [],
        'source_dependencies': packet['dependencies'], 'reading_assumptions': reading['assumptions'],
        'reading_questions': reading['questions']}
    if result['unresolved_premises'] != expected or result['profile'] != PROFILE:
        raise LegalMathError('E_INTEGRITY')
    return result
