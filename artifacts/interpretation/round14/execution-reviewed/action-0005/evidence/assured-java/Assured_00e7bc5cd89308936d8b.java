package hk.legalmath;
import java.util.Map;
import java.util.LinkedHashMap;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
/** Conditional on every retained hypothesis; this API grants no release authority. */
public final class Assured_00e7bc5cd89308936d8b {
    private Assured_00e7bc5cd89308936d8b() {}
    public static final String SET_HASH = "00e7bc5cd89308936d8b071dd46f62033e0d0f61a07bd2a513e3e0da79f8e139";
    public static final String SOURCE_HASH = "d3361338269bbc2933990223447b2f0092f6969c008e892103a552ac14926fdf";
    private static Map<String,Object> project(Map<String,Object> result) {
        Map<String,Object> p = new LinkedHashMap<>();
        for (String key : new String[]{"status","type","value"})
            if (result.containsKey(key)) p.put(key,result.get(key));
        return p;
    }
    public static String evaluate(String snapshot, String sourceHash, String at, String knownAt) {
        return Json.write(evaluate(Json.map(Json.parse(snapshot)),sourceHash,at,knownAt));
    }
    public static Map<String,Object> evaluate(Map<String,Object> snapshot, String sourceHash, String at, String knownAt) {
        Map<String,Object> outcomes = new LinkedHashMap<>();
        String status = "SOURCE_CHANGED"; Object value = null;
        if (SOURCE_HASH.equals(sourceHash)) {
            outcomes.put("controlled-language.0", project(Policy_05c085e1ca5dc839554b.evaluate(snapshot, "selected.control", at, knownAt, "draft")));
            outcomes.put("normative.0", project(Policy_d6fa3b45b9374e9c86a4.evaluate(snapshot, "selected.control", at, knownAt, "draft")));
            boolean unencoded=false, unknown=false, allNA=true, same=true;
            Map<String,Object> first=null;
            for (Object item : outcomes.values()) {
                if (item==null) { unencoded=true; continue; }
                Map<String,Object> row=Json.map(item);
                String s=Json.str(row.get("status"));
                allNA=allNA && s.equals("OUT_OF_SCOPE");
                unknown=unknown || !(s.equals("TRUE") || s.equals("FALSE") || s.equals("OUT_OF_SCOPE"));
                if (first==null) first=row; else same=same && first.equals(row);
            }
            if (unencoded) status="UNENCODED_ALTERNATIVE";
            else if (allNA) status="INVARIANT_NOT_APPLICABLE";
            else if (unknown) status="UNKNOWN_OR_CONFLICT";
            else if (!same) status="INTERPRETATION_DISAGREEMENT";
            else if (first!=null && first.get("value") instanceof Boolean) {
                status="INVARIANT_KNOWN"; value=first.get("value");
            } else status="UNKNOWN_OR_CONFLICT";
        }
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("status",status); result.put("value",value); result.put("outcomes",outcomes);
        result.put("question_hash","8e8583d66b310c67072bf12eeb2162fd684215be250da772bc85aefacdf56432"); result.put("set_hash",SET_HASH);
        result.put("source_packet_hash",sourceHash); result.put("snapshot_hash",Json.hash(snapshot));
        result.put("conditional_on_retained_hypotheses",true); result.put("release_eligible",false);
        return result;
    }
    public static void main(String[] args) throws Exception {
        BufferedReader in=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));
        String line;
        while ((line=in.readLine())!=null) {
            Map<String,Object> r=Json.map(Json.parse(line));
            System.out.println(Json.write(evaluate(Json.map(r.get("snapshot")),Json.str(r.get("source_packet_hash")),
                Json.str(r.get("valid_at")),Json.str(r.get("known_at")))));
        }
    }
}
