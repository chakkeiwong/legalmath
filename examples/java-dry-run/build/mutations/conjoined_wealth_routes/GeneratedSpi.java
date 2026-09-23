// Generated from spi-control.bundle.json; edit the reviewed specification, not this file.
package hk.legalmath.spi;
import java.math.BigInteger;
import java.util.*;
import static hk.legalmath.spi.DecisionRuntime.*;
public final class GeneratedSpi {
    private GeneratedSpi() {}
    public static final String BUNDLE_HASH = "153623e5d3103b84427448553de0e53082220037d61691a0ec81f82b2865f04c";
    public static final Map<String,String> INPUT_TYPES = Map.ofEntries(
        Map.entry("active_consent", "bool"),
        Map.entry("annual_review_current", "bool"),
        Map.entry("category_explanation_resolved", "bool"),
        Map.entry("category_information_delivered", "bool"),
        Map.entry("category_selected", "bool"),
        Map.entry("category_transactions_3y", "integer"),
        Map.entry("current_offering_documents_delivered", "bool"),
        Map.entry("explanation_delivered", "bool"),
        Map.entry("explanation_requested_or_material_query", "bool"),
        Map.entry("individual_pi", "bool"),
        Map.entry("material_warning_delivered", "bool"),
        Map.entry("net_assets_ex_home", "money_hkd"),
        Map.entry("non_conservative_objectives", "bool"),
        Map.entry("outsize_or_material_transaction", "bool"),
        Map.entry("portfolio", "money_hkd"),
        Map.entry("prior_written_acknowledgment_complete", "bool"),
        Map.entry("professional_qualification", "bool"),
        Map.entry("profile_execution_monitoring", "bool"),
        Map.entry("profile_individual", "bool"),
        Map.entry("profile_solicited", "bool"),
        Map.entry("projected_gross_exposure", "money_hkd"),
        Map.entry("reasonable_sophistication_assessment", "bool"),
        Map.entry("relevant_degree", "bool"),
        Map.entry("relevant_year_of_work", "bool"),
        Map.entry("streamlining_threshold", "money_hkd"),
        Map.entry("threshold_rationale_retained", "bool"),
        Map.entry("transaction_materiality_assessed", "bool"),
        Map.entry("written_assessment_retained", "bool"));
    private static Value r0(Context c) {
        return c.rule("spi.financial", List.of("spi.annex1.3.1","spi.annex1.3.2","spi.annex1.3.3","spi.annex1.3.4"), () ->
            all(compare("ge", c.fact("portfolio"), Value.of(new BigInteger("4000000000"))), compare("ge", c.fact("net_assets_ex_home"), Value.of(new BigInteger("8000000000")))));
    }
    private static Value r1(Context c) {
        return c.rule("spi.category_qualification", List.of("spi.annex1.4.1","spi.annex1.7.3","spi.annex2.2","spi.annex2.3"), () ->
            any(c.fact("relevant_degree"), c.fact("professional_qualification"), c.fact("relevant_year_of_work"), compare("ge", c.fact("category_transactions_3y"), Value.of(new BigInteger("5")))));
    }
    private static Value r2(Context c) {
        return c.rule("spi.assessment", List.of("spi.annex1.1","spi.annex1.4.1","spi.annex1.5.1","spi.annex1.12.1","spi.annex1.12.2","spi.annex2.1"), () ->
            all(c.fact("individual_pi"), r0(c), r1(c), c.fact("reasonable_sophistication_assessment"), c.fact("non_conservative_objectives"), c.fact("written_assessment_retained")));
    }
    private static Value r3(Context c) {
        return c.rule("spi.threshold", List.of("spi.annex1.6","spi.annex1.8.1","spi.annex1.8.3","spi.annex2.6","spi.annex2.7"), () ->
            compare("ge", c.fact("streamlining_threshold"), c.fact("projected_gross_exposure")));
    }
    private static Value r4(Context c) {
        return c.rule("spi.explanation", List.of("spi.annex1.10.3"), () ->
            any(not(c.fact("explanation_requested_or_material_query")), c.fact("explanation_delivered")));
    }
    private static Value r5(Context c) {
        return c.rule("spi.warning", List.of("spi.annex1.8.4"), () ->
            all(c.fact("transaction_materiality_assessed"), any(not(c.fact("outsize_or_material_transaction")), c.fact("material_warning_delivered"))));
    }
    private static Value r6(Context c) {
        return c.rule("spi.retained_information", List.of("spi.annex1.8.4","spi.annex1.10.3"), () ->
            all(c.fact("current_offering_documents_delivered"), r4(c), r5(c)));
    }
    private static Value r7(Context c) {
        return c.rule("spi.review_policy", List.of("spi.annex1.8.5","spi.annex1.14.1","spi.annex1.14.2"), () ->
            c.fact("annual_review_current"));
    }
    private static Value r8(Context c) {
        return c.rule("spi.arrangement", List.of("spi.annex1.7.2","spi.annex1.8.2","spi.annex1.8.5","spi.annex1.12.3","spi.annex1.13.1","spi.annex1.13.2","spi.annex1.14.1","spi.annex1.14.2","spi.annex2.4","spi.annex2.5"), () ->
            all(c.fact("category_selected"), c.fact("category_information_delivered"), c.fact("category_explanation_resolved"), c.fact("prior_written_acknowledgment_complete"), c.fact("active_consent"), c.fact("threshold_rationale_retained"), r7(c)));
    }
    private static Value r9(Context c) {
        return c.rule("spi.streamlining", List.of("spi.annex1.1","spi.annex1.6","spi.annex1.9","spi.annex1.10.1","spi.annex1.10.2","spi.annex1.10.3","spi.annex1.10.4"), () ->
            all(r2(c), r8(c), r3(c), r6(c)));
    }
    public static Result evaluate(Snapshot snapshot, String validAt, String knownAt) {
        var c = new Context(snapshot, validAt, knownAt, BUNDLE_HASH, INPUT_TYPES);
        if (validAt.compareTo("2026-09-01T00:00:00.000000Z") < 0 || validAt.compareTo("2026-10-01T00:00:00.000000Z") >= 0) throw new IllegalArgumentException("E_BUNDLE_INTERVAL");
        var conflicts = c.conflicts();
        if (!conflicts.isEmpty()) return c.finish("CONFLICT", conflicts);
        var scope = all(c.fact("profile_individual"), c.fact("profile_solicited"), c.fact("profile_execution_monitoring"));
        if (scope.value()==null) return c.finish("UNKNOWN", scope.blockers());
        if (Boolean.FALSE.equals(scope.value())) return c.finish("OUT_OF_SCOPE", Set.of());
        var result = r9(c);
        return c.finish(result.status(), result.blockers());
    }
}
