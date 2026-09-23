import json
import subprocess
from legalmath.java.manifest import build_candidate
from tests.conformance.test_java import spi_cases


def test_forced_java_host_interleavings(root, tmp_path):
    cases = spi_cases()
    jdk = root / ".localresources/java-toolchain/jdk-17.0.20.1+1"
    build = build_candidate(cases[0]["bundle"], tmp_path / "build", jdk)
    (tmp_path / "snapshot.json").write_text(json.dumps(cases[0]["snapshot"]))
    source = '''import hk.legalmath.*;
import java.math.BigInteger;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Function;
public final class HostProbe {
  public static void main(String[] args) throws Exception {
    String snapshot=Files.readString(Path.of(args[0]));
    Function<String,String> evaluate=s->POLICY.evaluate(s,"spi.streamlining","2026-09-21T02:00:00.000000Z","2026-09-21T02:00:00.000000Z","production");
    SyntheticHost host=new SyntheticHost(snapshot,new BigInteger("800000000"),"release.one",evaluate);
    CyclicBarrier barrier=new CyclicBarrier(2);
    Runnable hook=()->{try{barrier.await(10,TimeUnit.SECONDS);}catch(Exception e){throw new IllegalStateException(e);}};
    ExecutorService pool=Executors.newFixedThreadPool(2);
    Future<Map<String,Object>> a=pool.submit(()->host.order("a","150000000",3,hook));
    Future<Map<String,Object>> b=pool.submit(()->host.order("b","150000000",3,hook));
    List<Object> concurrent=List.of(a.get(),b.get());pool.shutdown();
    SyntheticHost withdrawal=new SyntheticHost(snapshot,new BigInteger("800000000"),"release.one",evaluate);
    Map<String,Object> withdrawn=withdrawal.order("w","100",3,()->withdrawal.setConsent(false));
    SyntheticHost changed=new SyntheticHost(snapshot,new BigInteger("800000000"),"release.one",evaluate);
    Map<String,Object> replaced=changed.order("c","100",3,()->changed.replaceRelease("release.two",s->"{\\"status\\":\\"FALSE\\"}"));
    SyntheticHost exhausted=new SyntheticHost(snapshot,new BigInteger("800000000"),"release.one",evaluate);
    Map<String,Object> retry=exhausted.order("e","100",1,()->exhausted.setConsent(false));
    System.out.println(Json.write(Json.obj("concurrent",concurrent,"exposure",host.exposure(),
      "duplicate",host.order("a","150000000",3,null).equals(a.get()),
      "collision",host.order("a","150000001",3,null).get("status"),
      "withdrawn",withdrawn.get("status"),"changed",replaced.get("status"),"release",replaced.get("release_hash"),"retry",retry.get("status"))));
  }
}
'''.replace("POLICY", build["class_name"])
    path = tmp_path / "HostProbe.java"
    path.write_text(source)
    subprocess.run([str(jdk / "bin/javac"), "--release", "17", "-Xlint:all", "-Werror", "-cp", build["jar"], "-d", str(tmp_path), str(path)], check=True, capture_output=True)
    result = json.loads(subprocess.check_output([str(jdk / "bin/java"), "-cp", str(tmp_path) + ":" + build["jar"], "HostProbe", str(tmp_path / "snapshot.json")], text=True, timeout=30))
    assert sorted(x["status"] for x in result["concurrent"]) == ["DO_NOT_STREAMLINE", "RESERVED"]
    assert result["exposure"] == "950000000" and result["duplicate"]
    assert result["collision"] == "IDEMPOTENCY_CONFLICT"
    assert result["withdrawn"] == result["changed"] == "DO_NOT_STREAMLINE"
    assert result["release"] == "release.two" and result["retry"] == "RETRY_EXHAUSTED"
