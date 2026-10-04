"""Export the retained conformance corpus from the application environment.

The solver environment deliberately has no test-runner dependency. This fixed
entry point supplies data across that boundary without importing test modules
inside the independent solver process.
"""
from pathlib import Path
from argparse import ArgumentParser
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))


def main():
    from tests.catala.backend_support import corpus_groups, interaction_cases
    parser = ArgumentParser(__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    groups = corpus_groups() + [interaction_cases()]
    Path(args.out).write_text(json.dumps(groups, sort_keys=True))
    print(json.dumps({'groups': len(groups), 'cases': sum(map(len, groups))}))


if __name__ == '__main__':
    main()
