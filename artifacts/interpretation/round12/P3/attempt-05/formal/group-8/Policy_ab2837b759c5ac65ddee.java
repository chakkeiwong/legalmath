package hk.legalmath;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;

/** Generated RuleIR 0.1 policy. Authority is supplied by an external release record. */
public final class Policy_ab2837b759c5ac65ddee {
    private Policy_ab2837b759c5ac65ddee() {}
    public static final String BUNDLE_HASH = "ab2837b759c5ac65ddeed48e87daea891125dc834d3214a31c346ad5fbb17e40";
    private static final Policy POLICY = new Policy(new String(Base64.getDecoder().decode(String.join("", new String[]{
"eyJidW5kbGVfaWQiOiJtb25leS5zY2FsZSIsImZhY3RzIjpbXSwiaW50ZXJwcmV0YXRpb25zIjpbeyJiYXNpcyI6InN5bnRoZXRpY190ZXN0IiwiaWQiOiJtZWFuaW5nLm1haW4iLCJpc3N1ZV9pZHMiOltdLCJzb3VyY2Vfc3Bhbl9pZHMiOlsic3BpLmFubmV4MS4zLjEiXSwic3RhdGVtZW50IjoiU3ludGhldGljIGxhbmd1YWdlIGNvbmZvcm1hbmNlIGV4YW1wbGU7IG5vdCBhbiBhZGRpdGlvbmFsIFNGQyBydWxlLiJ9XSwicnVsZXMiOlt7ImJvZHkiOnsiYXJnIjp7Im5vZGVfaWQiOiJhbW91bnQiLCJvcCI6ImxpdGVyYWwiLCJ0eXBlIjoibW9uZXlfaGtkIiwidmFsdWUiOiIxMDEifSwiZGVub21pbmF0b3IiOiIyIiwibm9kZV9pZCI6InNjYWxlIiwibnVtZXJhdG9yIjoiMSIsIm9wIjoic2NhbGUifSwiaWQiOiJtb25leS5zY2FsZSIsImludGVycHJldGF0aW9uX2lkIjoibWVhbmluZy5tYWluIiwic2NvcGUiOnsibm9kZV9pZCI6InNjb3BlLnRydWUiLCJvcCI6ImxpdGVyYWwiLCJ0eXBlIjoiYm9vbCIsInZhbHVlIjp0cnVlfSwic291cmNlX3NwYW5faWRzIjpbInNwaS5hbm5leDEuMy4xIl0sInR5cGUiOiJtb25leV9oa2QifV0sInNvdXJjZV9zcGFucyI6W3siZW5kIjoyMTA3LCJpZCI6InNwaS5hbm5leDEuMy4xIiwicGFnZSI6MSwicXVvdGVfc2hhMjU2IjoiMTJlNTVkMzY4NDg5MjdmYWFkODJjNTE5YjhiM2Y3NWI3YTcxNjJjYzc5ZWZhN2MzZDBjZmZlYWE4OWJhYWRlZCIsInJhd19zaGEyNTYiOiJmODM3MTk5ODFkNzRlZDA2YmI2MmNjZjEyMWJkNzIwNGY4MGExMTQ2YWU1MDQwZjRjNGFhYjkwNWRmNTEwYzRhIiwic291cmNlX2lkIjoiMjNFQzM1L2FubmV4MSIsInN0YXJ0IjoxODU5LCJ0ZXh0X3NoYTI1NiI6IjY3ODA2MDA2MDBlNzdkMmZiZmY1ZjRhMTRiNGRiMjM3YzRjMzk0Mzc2NGE4NDg0NGFhZDhhZDljZDM0NmU1ODkifV0sInNwZWNfdmVyc2lvbiI6IjAuMSIsInZhbGlkX2Zyb20iOiIyMDIzLTA3LTI4VDAwOjAwOjAwLjAwMDAwMFoiLCJ2YWxpZF91bnRpbCI6bnVsbH0="
    })), StandardCharsets.UTF_8));
    public static String evaluate(String snapshot, String ruleId, String validAt, String knownAt, String mode) {
        return POLICY.evaluate(snapshot, ruleId, validAt, knownAt, mode);
    }
    public static Map<String,Object> evaluate(Map<String,Object> snapshot, String ruleId, String validAt, String knownAt, String mode) {
        return POLICY.evaluate(snapshot, ruleId, validAt, knownAt, mode);
    }
}
