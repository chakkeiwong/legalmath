package hk.legalmath;
import org.junit.Test;
import static org.junit.Assert.*;
import java.nio.file.*;
import java.util.*;
public class RuntimeAssuranceTest {
 @Test public void intervalBoundaries() {
   String a="2026-01-01T00:00:00.000000Z", b="2026-01-02T00:00:00.000000Z";
   assertTrue(Policy.eligible(a,b,a));
   assertFalse(Policy.eligible(a,b,b));
   assertFalse(Policy.eligible(b,null,a));
   assertTrue(Policy.eligible(a,null,b));
 }
 @Test public void compiledAndDynamicConformance() throws Exception {
   for(String line:Files.readAllLines(Path.of("/home/chakwong/python/legalmath/artifacts/interpretation/round12/P3/attempt-04/mutations/pit-runtime/cases.ndjson"))) {
     Map<String,Object> c=Json.map(Json.parse(line));
     String snapshot=Json.write(c.get("snapshot")), rule=Json.str(c.get("rule_id"));
     String at=Json.str(c.get("valid_at")), cutoff=Json.str(c.get("known_at"));
     String answer=Boolean.TRUE.equals(c.get("use_generated")) ? Policy_ef31b8f9366cc0dcaab8.evaluate(snapshot,rule,at,cutoff,"draft")
       : new Policy(Json.write(c.get("bundle"))).evaluate(snapshot,rule,at,cutoff,"draft");
     Map<String,Object> actual=Json.map(Json.parse(answer));
     actual.remove("engine_version"); actual.remove("result_hash");
     assertEquals(Json.str(c.get("id")),Json.write(c.get("expected_result")),Json.write(actual));
   }
 }
}