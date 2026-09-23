#!/bin/bash
# TEST CLINGO.sh
#   by Lut99
#
# Created:
#   08 Apr 2025, 22:20:26
# Last edited:
#   08 Apr 2025, 22:31:41
# Auto updated?
#   Yes
#
# Description:
#   Small Bash script wrapping the Python one to make sure dependencies are
#   setup.
#


# Setup the env
if [[ ! -d "$(dirname "$0")/.venv" ]]; then
    echo "Environment \"$(dirname "$0")/.venv\" not setup; initializing..."
    /usr/bin/env python3 -m venv "$(dirname "$0")/.venv" || exit "$?"
    source "$(dirname "$0")/.venv/bin/activate" || exit "$?"
    /usr/bin/env python3 -m pip install -r "$(dirname "$0")/requirements.txt" || exit "$?"
else
    echo "Environment \"$(dirname "$0")/.venv\" already setup"

    # Only activate the env
    source "$(dirname "$0")/.venv/bin/activate" || exit "$?"
fi

# Run the command
/usr/bin/env python3 "$(dirname "$0")/test-clingo.py" $@ || exit "$?"
