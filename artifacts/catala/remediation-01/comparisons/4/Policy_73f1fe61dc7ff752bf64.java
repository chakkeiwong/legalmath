package hk.legalmath;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;

/** Generated RuleIR 0.1 policy. Authority is supplied by an external release record. */
public final class Policy_73f1fe61dc7ff752bf64 {
    private Policy_73f1fe61dc7ff752bf64() {}
    public static final String BUNDLE_HASH = "73f1fe61dc7ff752bf645c5d883231cf66f53db8f52bf2a86e38946d4c0b7f6b";
    private static final Policy POLICY = new Policy(new String(Base64.getDecoder().decode(String.join("", new String[]{
"eyJidW5kbGVfaWQiOiJsb2dpYy5leGNsdWRlZF9taWRkbGUiLCJmYWN0cyI6W3siZGVzY3JpcHRpb24iOiJhIiwibmFtZSI6ImEiLCJ0eXBlIjoiYm9vbCJ9XSwiaW50ZXJwcmV0YXRpb25zIjpbeyJiYXNpcyI6InN5bnRoZXRpY190ZXN0IiwiaWQiOiJtZWFuaW5nLm1haW4iLCJpc3N1ZV9pZHMiOltdLCJzb3VyY2Vfc3Bhbl9pZHMiOlsic3BpLmFubmV4MS4zLjEiXSwic3RhdGVtZW50IjoiU3ludGhldGljIGxhbmd1YWdlIGNvbmZvcm1hbmNlIGV4YW1wbGU7IG5vdCBhbiBhZGRpdGlvbmFsIFNGQyBydWxlLiJ9XSwicnVsZXMiOlt7ImJvZHkiOnsiYXJncyI6W3sibmFtZSI6ImEiLCJub2RlX2lkIjoiYS5yZWYiLCJvcCI6ImZhY3QifSx7ImFyZyI6eyJuYW1lIjoiYSIsIm5vZGVfaWQiOiJhLnJlZjIiLCJvcCI6ImZhY3QifSwibm9kZV9pZCI6Im5lZyIsIm9wIjoibm90In1dLCJub2RlX2lkIjoib3IiLCJvcCI6ImFueSJ9LCJpZCI6ImxvZ2ljLmV4Y2x1ZGVkX21pZGRsZSIsImludGVycHJldGF0aW9uX2lkIjoibWVhbmluZy5tYWluIiwic2NvcGUiOnsibm9kZV9pZCI6InNjb3BlLnRydWUiLCJvcCI6ImxpdGVyYWwiLCJ0eXBlIjoiYm9vbCIsInZhbHVlIjp0cnVlfSwic291cmNlX3NwYW5faWRzIjpbInNwaS5hbm5leDEuMy4xIl0sInR5cGUiOiJib29sIn1dLCJzb3VyY2Vfc3BhbnMiOlt7ImVuZCI6MjEwNywiaWQiOiJzcGkuYW5uZXgxLjMuMSIsInBhZ2UiOjEsInF1b3RlX3NoYTI1NiI6IjEyZTU1ZDM2ODQ4OTI3ZmFhZDgyYzUxOWI4YjNmNzViN2E3MTYyY2M3OWVmYTdjM2QwY2ZmZWFhODliYWFkZWQiLCJyYXdfc2hhMjU2IjoiZjgzNzE5OTgxZDc0ZWQwNmJiNjJjY2YxMjFiZDcyMDRmODBhMTE0NmFlNTA0MGY0YzRhYWI5MDVkZjUxMGM0YSIsInNvdXJjZV9pZCI6IjIzRUMzNS9hbm5leDEiLCJzdGFydCI6MTg1OSwidGV4dF9zaGEyNTYiOiI2NzgwNjAwNjAwZTc3ZDJmYmZmNWY0YTE0YjRkYjIzN2M0YzM5NDM3NjRhODQ4NDRhYWQ4YWQ5Y2QzNDZlNTg5In1dLCJzcGVjX3ZlcnNpb24iOiIwLjEiLCJ2YWxpZF9mcm9tIjoiMjAyMy0wNy0yOFQwMDowMDowMC4wMDAwMDBaIiwidmFsaWRfdW50aWwiOm51bGx9"
    })), StandardCharsets.UTF_8), new catala.stdlib.RuleIRBackend(), "legalmath-catala-java/0.2.0");
    public static String evaluate(String snapshot, String ruleId, String validAt, String knownAt, String mode) {
        return POLICY.evaluate(snapshot, ruleId, validAt, knownAt, mode);
    }
    public static Map<String,Object> evaluate(Map<String,Object> snapshot, String ruleId, String validAt, String knownAt, String mode) {
        return POLICY.evaluate(snapshot, ruleId, validAt, knownAt, mode);
    }
}
