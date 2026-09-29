"""Independent bounded Gregorian codec and audited calendar theorem."""
from pathlib import Path
import re
import subprocess

from ..canonical import raw_digest
from ..errors import LegalMathError

PROFILE = 'gregorian.date-order.v1'
PRELUDE = Path(__file__).with_name('Gregorian.lean')
THEOREMS = {'year_step', 'ordinal_order', 'rank_ordinal_order'}
STANDARD_AXIOMS = {'propext', 'Quot.sound', 'Classical.choice'}


def leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def month_lengths(year):
    return (31, 29 if leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def parse(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError('Canonical Gregorian date required')
    year, month, day = map(int, value.split('-'))
    if not 1 <= year <= 9999 or not 1 <= month <= 12 or not 1 <= day <= month_lengths(year)[month - 1]:
        raise ValueError('Invalid Gregorian date')
    return year, month, day


def ordinal(value):
    year, month, day = parse(value)
    previous = year - 1
    return 365 * previous + previous // 4 - previous // 100 + previous // 400 + sum(month_lengths(year)[:month-1]) + day - 1


def produce(directory, lean):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/'Gregorian.lean'
    path.write_bytes(PRELUDE.read_bytes())
    run = subprocess.run([str(lean), str(path.resolve())], cwd=directory,
                         capture_output=True, text=True, timeout=60)
    log = run.stdout + run.stderr
    (directory/'lean.log').write_text(log)
    dependencies = re.findall(r"'LegalMathGregorian\.([a-z_]+)' depends on axioms: \[([^\]]*)\]", log)
    axioms = {x.strip() for _, names in dependencies for x in names.split(',') if x.strip()}
    if run.returncode or 'sorry' in log or {name for name, _ in dependencies} != THEOREMS or not axioms <= STANDARD_AXIOMS:
        raise LegalMathError('E_INTEGRITY', details='Gregorian theorem/axiom check failed')
    return {'profile': PROFILE, 'status': 'KERNEL_CHECKED', 'theorems': sorted(THEOREMS),
        'standard_axioms': sorted(axioms), 'domain': 'Valid proleptic Gregorian dates in years 1 through 9999',
        'proposition': 'Ordinal day counts, lexicographic date triples and the bounded integer date rank have the same strict order. Year transitions have 365 or 366 days under the Gregorian leap rule.',
        'trust_boundary': 'Independent Python parser and production codecs are tested separately; this theorem defines integer calendar semantics, not string-library or compiler correctness.',
        'excludes': ['Which date a legal provision intends', 'English interpretation', 'evidence validity timestamps',
                     'business-day calendars', 'date arithmetic libraries', 'end-to-end Java/Catala correctness'],
        'prelude_sha256': raw_digest(PRELUDE.read_bytes()), 'tool_sha256': raw_digest(Path(lean).read_bytes()),
        'checker_sha256': raw_digest(Path(__file__).read_bytes()), 'log_sha256': raw_digest(log.encode())}


def exhaustive_codec_check():
    """Check every valid date against production parsing and Python's day codec.

    This finite computation is not itself a Lean proof of either Python library.
    The independently implemented ordinal must increase by exactly one each day.
    """
    from datetime import date
    from ..domain import scalar
    count, previous, previous_text = 0, -1, ''
    for year in range(1, 10000):
        for month, length in enumerate(month_lengths(year), 1):
            for day in range(1, length + 1):
                text = f'{year:04d}-{month:02d}-{day:02d}'
                current = ordinal(text)
                if (current != previous + 1 or text <= previous_text or not scalar('date', text)
                        or current != date.fromisoformat(text).toordinal() - 1):
                    raise LegalMathError('E_INTEGRITY', details='Gregorian codec/order discrepancy: ' + text)
                previous, previous_text, count = current, text, count + 1
    return {'status': 'EXHAUSTIVE_FINITE_CHECK_PASSED', 'valid_dates': count,
            'domain': '0001-01-01 through 9999-12-31', 'last_ordinal_zero_based': previous,
            'whole_compiler_correctness': 'NOT_ESTABLISHED'}
