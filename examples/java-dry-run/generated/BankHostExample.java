package hk.legalmath.spi;
import java.util.*;
import java.math.BigInteger;
import static hk.legalmath.spi.DecisionRuntime.*;

public final class BankHostExample {
public static void main(String[] args) {
var snapshot = new Snapshot("client.synthetic.lee", Map.ofEntries(
Map.entry("active_consent", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("annual_review_current", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("category_explanation_resolved", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("category_information_delivered", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("category_selected", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("category_transactions_3y", Fact.known("integer", new BigInteger("5"), List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("current_offering_documents_delivered", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("explanation_delivered", Fact.known("bool", false, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("explanation_requested_or_material_query", Fact.known("bool", false, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("individual_pi", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("material_warning_delivered", Fact.known("bool", false, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("net_assets_ex_home", Fact.known("money_hkd", new BigInteger("7500000000"), List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("non_conservative_objectives", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("outsize_or_material_transaction", Fact.known("bool", false, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("portfolio", Fact.known("money_hkd", new BigInteger("4000000000"), List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("prior_written_acknowledgment_complete", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("professional_qualification", Fact.known("bool", false, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("profile_execution_monitoring", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("profile_individual", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("profile_solicited", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("projected_gross_exposure", Fact.known("money_hkd", new BigInteger("1000000000"), List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("reasonable_sophistication_assessment", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("relevant_degree", Fact.known("bool", false, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("relevant_year_of_work", Fact.known("bool", false, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("streamlining_threshold", Fact.known("money_hkd", new BigInteger("1000000000"), List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("threshold_rationale_retained", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("transaction_materiality_assessed", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z")),
Map.entry("written_assessment_retained", Fact.known("bool", true, List.of("synthetic.case"), "2026-09-01T00:00:00.000000Z", "2026-10-01T00:00:00.000000Z", "2026-09-01T00:00:00.000000Z"))));
var before = GeneratedSpi.evaluate(snapshot,"2026-09-21T02:00:00.000000Z","2026-09-21T02:00:00.000000Z");
System.out.println("BEFORE_WITHDRAWAL " + before.disposition());
var consent = ConsentReplay.replay(List.of(new ConsentReplay.Event("consent.grant.1","GRANTED","2026-09-01T00:00:00.000000Z","2026-09-01T00:00:00.000000Z",1),new ConsentReplay.Event("consent.withdraw.1","WITHDRAWN","2026-09-21T02:05:00.000000Z","2026-09-21T02:06:00.000000Z",2)), "2026-09-21T02:10:00.000000Z", "2026-09-21T02:10:00.000000Z", "2026-09-21T02:10:00.000000Z", "2026-09-21T02:10:00.000000Z");
if (!consent.equals("FALSE")) throw new AssertionError("withdrawal replay");
snapshot = snapshot.with("active_consent", Fact.known("bool", false, List.of("consent.withdraw.1"), "2026-09-21T02:05:00.000000Z", null, "2026-09-21T02:06:00.000000Z"));
var after = GeneratedSpi.evaluate(snapshot,"2026-09-21T02:10:00.000000Z","2026-09-21T02:10:00.000000Z");
System.out.println("AFTER_WITHDRAWAL " + after.disposition());
if (!after.status().equals("FALSE")) throw new AssertionError("consent omitted");
System.out.println("RESULT_AUTHORITY DEMONSTRATION_ONLY");
}
}
