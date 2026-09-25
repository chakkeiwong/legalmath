#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"
task_venv="$(mktemp -d /tmp/legalmath-fresh-XXXXXX)"
python3 -m venv "$task_venv"
"$task_venv/bin/python" -m pip install --quiet -r requirements-dev.lock
"$task_venv/bin/python" -m pip install --quiet --no-build-isolation --no-deps .
mkdir -p artifacts/runs/fresh-install
"$task_venv/bin/python" -m pip check > artifacts/runs/fresh-install/pip-check.txt
"$task_venv/bin/python" -m pip freeze > artifacts/runs/fresh-install/environment.txt
"$task_venv/bin/python" -c 'import legalmath, importlib.resources; from legalmath.java.emit import runtime_sources; from legalmath.ir.load import validator; validator("rule-bundle"); assert importlib.resources.files("legalmath").joinpath("web/static/api.js").is_file(); print(legalmath.__version__, len(runtime_sources()))' > artifacts/runs/fresh-install/import.txt
"$task_venv/bin/legalmath" --version > artifacts/runs/fresh-install/cli.txt
printf '%s\n' "$task_venv" > artifacts/runs/fresh-install/environment-path.txt
echo 'Fresh non-editable installation, packaged schemas/Java runtime, CLI and dependency checks passed.'
