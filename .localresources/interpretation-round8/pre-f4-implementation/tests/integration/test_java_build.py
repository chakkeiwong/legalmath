from pathlib import Path
import zipfile
from legalmath.java.manifest import build_candidate


def test_wrong_toolchain_cannot_build(case, tmp_path):
    import pytest
    from legalmath.errors import LegalMathError
    bin_dir = tmp_path / "jdk" / "bin"
    bin_dir.mkdir(parents=True)
    for tool in ("java", "javac"):
        path = bin_dir / tool
        path.write_text("#!/bin/sh\nprintf 'javac 21.0.1\\n'\n")
        path.chmod(0o700)
    with pytest.raises(LegalMathError) as error:
        build_candidate(case["bundle"], tmp_path / "out", bin_dir.parent)
    assert error.value.code == "E_UNSUPPORTED_PROFILE"


def test_reproducible_fresh_build_excludes_stale_classes(case, tmp_path, root):
    jdk = root / ".localresources/java-toolchain/jdk-17.0.20.1+1"
    out = tmp_path / "candidate"
    out.mkdir()
    (out / "Stale.class").write_bytes(b"not-a-real-class")
    a = build_candidate(case["bundle"], out, jdk)
    b = build_candidate(case["bundle"], tmp_path / "other", jdk)
    assert Path(a["jar"]).read_bytes() == Path(b["jar"]).read_bytes()
    assert a["manifest"] == b["manifest"]
    with zipfile.ZipFile(a["jar"]) as jar:
        assert all("Stale" not in name for name in jar.namelist())
        for name in jar.namelist():
            assert jar.read(name)[6:8] == b"\x00="  # classfile version 61 / Java 17
