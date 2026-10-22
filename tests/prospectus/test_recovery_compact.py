"""Compact probe output preserves complete values and original computations."""
import ast
import json
from pathlib import Path
import types

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBE = "docs/implementation/prospectus-execution-authority/reviews/compact-recovery-198/probe.py"
OLD = "docs/implementation/prospectus-execution-authority/attempts/recovery/attempt-009/probe.py"


def test_compact_probe_changes_only_complete_serialization():
    original = (ROOT / OLD).read_text()
    expected = original.replace("import os\n", "import os\nimport json\n", 1).replace(
        "    write(output,result)",
        '    Path(output).parent.mkdir(parents=True, exist_ok=True)\n'
        '    with Path(output).open("x") as stream:\n'
        '        json.dump(result, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":"))\n'
        '        stream.write("\\n")')
    assert (ROOT / PROBE).read_text() == expected


def test_compact_probe_preserves_nested_values_refusals_and_exclusive_output(tmp_path):
    tree = ast.parse((ROOT / PROBE).read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "evaluate")
    observed = {"text": "português 漢字", "values": [None, False, -1, 1.25],
        "all_nested_fields": {"unresolved": ["authority", "source"]}}
    def assess(req, path):
        if path.name == "correction":
            raise ValueError("expected original refusal")
        return observed
    namespace = dict(ROOT=tmp_path, Path=Path, json=json, read=lambda p: {},
        service=types.SimpleNamespace(assess=assess))
    exec(compile(ast.Module(body=[fn], type_ignores=[]), PROBE, "exec"), namespace)
    target = tmp_path / "new/complete.json"
    namespace["evaluate"](target)
    assert json.loads(target.read_text()) == {"portuguese": {"report": observed},
        "correction": {"error": "ValueError: expected original refusal"}}
    with pytest.raises(FileExistsError):
        namespace["evaluate"](target)


def test_focused_helper_preserves_original_suites_and_adds_compact_checks():
    before = (ROOT / OLD).with_name("run_tests.py").read_text()
    after = (ROOT / PROBE).with_name("run_tests.py").read_text()
    assert after == before.replace(
        "          '--junitxml='+str(HERE/'tests.xml')]",
        "          'tests/prospectus/test_recovery_compact.py',\n"
        "          '--junitxml='+str(HERE/'tests.xml')]")


def test_initialization_copies_every_helper_inside_loop():
    tree = ast.parse((ROOT / "scripts/prospectus_recovery_compact.py").read_text())
    loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For)
                and isinstance(n.target, ast.Name) and n.target.id == "helper")
    assert [n.value for n in loop.iter.elts] == ["probe.py", "run_tests.py", "finalize_recovery.py"]
    copied = [n for n in ast.walk(loop) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == "copyfile"]
    assert len(copied) == 1
    assert ast.unparse(copied[0].args[1]) == "folder / helper"


def test_stage_manifest_references_full_admission_by_digest():
    source = (ROOT / "scripts/prospectus_recovery_compact.py").read_text()
    assert '"input_binding_sha256": digest(admitted["binding"])' in source
    assert '"input_binding_file": name + "/admission.json"' in source
    assert 'admitted["binding"] == a.binding(task)' in source
    assert 'charged_storage(folder)["unique_bytes"]' in source
