package hk.legalmath;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Exact signed decimal representation; no financial-domain or legal approval. */
public final class ExactPercentageBoundary {
    private ExactPercentageBoundary() {}
    @FunctionalInterface
    public interface Evaluator {
        Map<String,Object> apply(Map<String,Object> snapshot, String rule, String at, String known, String mode);
    }
    private static final String PROFILE = "signed-exact-percent-v1";
    private static void require(boolean condition) { if (!condition) throw new Json.Invalid(); }
    public static String evaluate(String input, Evaluator evaluator) {
        try {
            Map<String,Object> request = Json.map(Json.parse(input));
            require(request.keySet().equals(Set.of("profile", "subject_id", "facts", "valid_at", "known_at", "mode")));
            require(PROFILE.equals(request.get("profile")) && "draft".equals(request.get("mode")));
            Map<String,Object> facts = Json.map(request.get("facts")), converted = Json.obj();
            require(Set.of("fund_manager", "va_objective", "intended_va_percent").containsAll(facts.keySet()));
            for (String name : List.of("fund_manager", "va_objective", "intended_va_percent")) {
                String type = name.equals("intended_va_percent") ? "decimal_percent" : "bool";
                Map<String,Object> f = Json.map(facts.getOrDefault(name, Json.obj("type", type, "status", "unknown", "reason", "MISSING")));
                require(type.equals(f.get("type")));
                String status = Json.str(f.get("status"));
                Set<String> keys = switch(status) {
                    case "known" -> Set.of("type", "status", "value", "evidence_ids", "valid_from", "valid_until", "recorded_at");
                    case "unknown" -> Set.of("type", "status", "reason");
                    case "conflict" -> Set.of("type", "status", "evidence_ids");
                    default -> throw new Json.Invalid();
                };
                require(f.keySet().equals(keys));
                if (!name.equals("intended_va_percent")) { converted.put(name, f); continue; }
                String[] ratio = {null, null};
                if (status.equals("known")) {
                    String value = Json.str(f.get("value"));
                    require(value.length() <= 64 && value.matches("-?(0|[1-9][0-9]*)(\\.[0-9]+)?"));
                    BigDecimal decimal = new BigDecimal(value);
                    BigInteger numerator = decimal.unscaledValue().multiply(BigInteger.valueOf(100));
                    BigInteger denominator = BigInteger.TEN.pow(decimal.scale());
                    BigInteger gcd = numerator.gcd(denominator);
                    numerator = numerator.divide(gcd); denominator = denominator.divide(gcd);
                    require(denominator.signum() > 0);
                    ratio[0] = numerator.toString(); ratio[1] = denominator.toString();
                }
                String[] names = {"va_bps_numerator", "va_bps_denominator"};
                for (int i = 0; i < names.length; i++) {
                    Map<String,Object> field = Json.map(Json.parse(Json.write(f)));
                    field.put("type", "integer");
                    if (ratio[i] != null) field.put("value", ratio[i]);
                    converted.put(names[i], field);
                }
            }
            Map<String,Object> snapshot = Json.obj("subject_id", request.get("subject_id"), "facts", converted);
            Map<String,Object> result = evaluator.apply(snapshot, "selected.control", Json.str(request.get("valid_at")), Json.str(request.get("known_at")), "draft");
            require(!"ERROR".equals(result.get("status")) || List.of("E_VERSION_TIME").equals(result.get("reason_codes")));
            return Json.write(Json.obj("boundary_status", "ACCEPTED", "profile", PROFILE, "snapshot", snapshot, "result", result, "release_eligible", false));
        } catch (IllegalArgumentException e) {
            return Json.write(Json.obj("boundary_status", "REJECTED", "error", "E_SCHEMA", "release_eligible", false));
        }
    }
}
