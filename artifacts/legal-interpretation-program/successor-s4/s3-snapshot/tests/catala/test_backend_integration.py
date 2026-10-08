"""Run the existing contracts with real Catala-built binaries, not the pilot API."""
import inspect
from pathlib import Path
import pytest

from legalmath.canonical import loads
from legalmath.catala.generator import ENGINE
from legalmath.java.manifest import build_candidate
from legalmath.review import releases
from tests.catala.backend_support import JDK, TOOLCHAIN
from tests.conformance import test_operator_interactions
from tests.integration import test_host_transactions, test_java_host, test_release
from tests.helpers import prepare_release
from tests.assurance import test_operations, test_output_semantics
from legalmath.java import host_package

CONTRACTS = [
    test_host_transactions.test_forced_java_host_interleavings,
    test_java_host.test_separate_host_uses_generated_library,
    test_operator_interactions.test_generated_nonboolean_date_arithmetic_and_selected_branches,
    test_release.test_exact_release_export_history_and_retirement,
    test_release.test_corrupt_jar_cannot_release,
    test_release.test_overlapping_release_is_rejected,
    test_operations.test_java_package_runs_separate_host_and_rejects_corruption,
    test_output_semantics.test_java_host_package_binds_predicate_meaning_to_actual_program,
]


@pytest.mark.parametrize("contract", CONTRACTS, ids=lambda f: f.__name__)
def test_existing_contract_with_catala(contract, db, root, case, tmp_path, monkeypatch):
    built = []
    def builder(bundle, output, jdk, **kwargs):
        result = build_candidate(bundle, output, jdk, backend="catala", catala_toolchain=TOOLCHAIN)
        built.append(result)
        return result
    module = inspect.getmodule(contract)
    if hasattr(module, "build_candidate"):
        monkeypatch.setattr(module, "build_candidate", builder)
    monkeypatch.setattr(releases, "build_candidate", builder)
    monkeypatch.setattr(host_package, "build_candidate", builder)
    values = {"db": db, "root": root, "case": case, "tmp_path": tmp_path}
    contract(**{name: values[name] for name in inspect.signature(contract).parameters})
    assert built and all(b["manifest"]["decision_engine"] == ENGINE for b in built)
    # The copied assertions above must have actually compiled the optional backend.
    assert all((Path(b["jar"]).parent / "Lowered.java").is_file() for b in built)


def test_explicit_release_backend_and_build_identity(db, root, case, tmp_path):
    work = prepare_release(db, root, tmp_path, case, backend="catala", catala_toolchain=TOOLCHAIN)
    with db.connect() as con:
        manifest = db.get(con, work["build"]["build_manifest_hash"])
    assert manifest["decision_engine"] == ENGINE
    # Reusing an idempotency key for a different engine must not retrieve the old build.
    from legalmath.errors import LegalMathError
    with pytest.raises(LegalMathError) as e:
        work["releases"].build("engineer", "build", work["state"]["bundle_hash"], tmp_path / "other", JDK, [work["case"]])
    assert e.value.code == "E_IDEMPOTENCY"


def test_cli_requires_explicit_catala_toolchain(monkeypatch, capsys, tmp_path):
    from legalmath import cli
    import sys
    from legalmath.canonical import canonical
    from tests.helpers import IDENTITIES
    identities = tmp_path / "identities.json"
    identities.write_bytes(canonical(IDENTITIES))
    cases = tmp_path / "cases.json"
    cases.write_text("[]")
    args = ["legalmath", "build-java", "--data-dir", str(tmp_path / "db"), "--bundle-hash", "a"*64,
            "--cases", str(cases), "--jdk", str(JDK), "--output", str(tmp_path / "build"),
            "--identities", str(identities), "--caller", "engineer", "--backend", "catala"]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 2
    assert "--backend catala requires" in capsys.readouterr().err
    seen = []
    def capture(self, *positional, **keywords):
        seen.append(keywords)
        return {"checked": True}
    monkeypatch.setattr(releases.Releases, "build", capture)
    monkeypatch.setattr(sys, "argv", args + ["--catala", "compiler", "--catala-upstream", "upstream", "--catala-lock", "lock"])
    cli.main()
    assert seen == [{"backend": "catala", "catala_toolchain": {"compiler": "compiler", "upstream": "upstream", "lock": "lock"}}]
