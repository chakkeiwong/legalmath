"""Observed changes veto currentness without upgrading a native boundary."""
from legalmath.prospectus.successor import native_inputs as n
from legalmath.prospectus.successor.read_context import reusable


def test_file_absence_content_and_symlink_changes(tmp_path):
    source, other, link = (tmp_path / name for name in ("source", "other", "link"))
    source.write_text("first")
    other.write_text("first")
    link.symlink_to(source)
    missing = tmp_path / "absent" / "data"
    state = n.snapshot([link, missing])
    assert n.observations_current(state)
    source.write_text("changed")
    assert not n.observations_current(state)
    source.write_text("first")
    assert n.observations_current(state)
    link.unlink()
    link.symlink_to(other)
    assert not n.observations_current(state)
    link.unlink()
    link.symlink_to(source)
    missing.parent.mkdir()
    missing.write_text("new")
    assert not n.observations_current(state)
    missing.unlink()
    assert n.observations_current(state)
    source.unlink()
    assert not n.observations_current(state)


def test_environment_is_hashed_and_native_reuse_stays_denied(tmp_path, monkeypatch):
    path = tmp_path / "input"
    path.write_text("same")
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("TEST_SECRET_TOKEN", "must-not-be-recorded")
    state = n.snapshot([path])
    assert n.observations_current(state)
    assert state["environment"]["LC_ALL"] != "C"
    assert "TEST_SECRET_TOKEN" not in state["environment"]
    monkeypatch.setenv("LC_ALL", "C.UTF-8")
    assert not n.observations_current(state)
    assert not state["complete_native_closure"]
    assert not reusable(tmp_path, {"records": [{"kind": "invocation"}]})


def test_empty_nonregular_and_unknown_manifest_are_not_current(tmp_path):
    assert not n.observations_current(n.snapshot([]))
    assert not n.observations_current(n.snapshot([tmp_path]))
    assert not n.observations_current({})


def test_failed_mapping_observation_cannot_be_current(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise PermissionError("maps unavailable")
    monkeypatch.setattr(n.Path, "read_text", unavailable)
    observed = n.loaded_inputs()
    assert observed['status'] == 'INCOMPLETE'
    assert observed['issues'] and observed['files'] == []
    assert not n.observations_current(observed)
