from pathlib import Path
import json
import subprocess
from legalmath.java.manifest import build_candidate


def test_separate_host_uses_generated_library(case, tmp_path, root):
    jdk = root / ".localresources/java-toolchain/jdk-17.0.20.1+1"
    b = build_candidate(case["bundle"], tmp_path / "build", jdk)
    caller = tmp_path / "BankCaller.java"
    caller.write_text('''import java.nio.file.*;
public final class BankCaller {
  public static void main(String[] args) throws Exception {
    String snapshot=Files.readString(Path.of(args[0]));
    System.out.println(''' + b["class_name"] + '''.evaluate(snapshot,args[1],args[2],args[2],"draft"));
  }
}
''')
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(case["snapshot"]))
    subprocess.run([str(jdk / "bin/javac"), "--release", "17", "-Xlint:all", "-Werror", "-cp", b["jar"], "-d", str(tmp_path), str(caller)], check=True, capture_output=True)
    out = subprocess.check_output([str(jdk / "bin/java"), "-cp", str(tmp_path) + ":" + b["jar"], "BankCaller", str(snap), case["rule_id"], case["valid_at"]], text=True)
    assert json.loads(out)["status"] == "TRUE"
