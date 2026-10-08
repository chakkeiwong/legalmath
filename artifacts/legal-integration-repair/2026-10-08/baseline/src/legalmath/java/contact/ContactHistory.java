package hk.legalmath;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Fixed attributed contact profile. Source applicability remains conditional. */
public final class CONTACT_ENTRY {
    private CONTACT_ENTRY() {}
    private static final Map<String,Object> POLICY = Json.map(Json.parse(POLICY_STRING));
    private static void require(boolean v) { if (!v) throw new Json.Invalid(); }
    private static void keys(Map<String,Object> v, String... names) { require(v.keySet().equals(Set.of(names))); }
    private static String id(Object v) { String s=Json.str(v);require(s.matches("[a-z][a-z0-9_.:-]{0,127}"));return s; }
    private static String time(Object v) {
        String s=Json.str(v);require(s.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{6}Z"));
        Instant.parse(s);return s;
    }
    private static void evidence(Object v) {
        List<Object> values=Json.list(v);require(!values.isEmpty() && values.size()<=32);
        Set<String> unique=new HashSet<>();for(Object x:values)require(unique.add(id(x)));
    }
    private static Set<String> channels(Object v) {
        List<Object> values=Json.list(v);require(!values.isEmpty() && values.size()<=4);
        Set<String> result=new HashSet<>();for(Object x:values) {
            String s=Json.str(x);require(Set.of("EMAIL","PHONE","FAX","OTHER").contains(s));require(result.add(s));
        }return result;
    }
    private static String state(Object v) {
        String s=Json.str(v);require(Set.of("TRUE","FALSE","UNKNOWN","CONFLICT").contains(s));return s;
    }
    private static Map<String,Object> fact(String s,String at) {
        if(s.equals("UNKNOWN"))return Json.obj("type","bool","status","unknown","reason","MISSING");
        if(s.equals("CONFLICT"))return Json.obj("type","bool","status","conflict","evidence_ids",List.of("first","second"));
        return Json.obj("type","bool","status","known","value",s.equals("TRUE"),"valid_from",POLICY.get("from_inclusive"),
            "valid_until",POLICY.get("until_exclusive"),"recorded_at",at,"evidence_ids",List.of("attributed.input"));
    }
    public static String evaluate(String input) {
        try {
            Map<String,Object> r=Json.map(Json.parse(input));
            keys(r,"profile","actor_id","str_id","assessment_at","known_at","licensed","urgent","contacts","coverage");
            require("attributed-contact-history-v1".equals(r.get("profile")));
            String actor=id(r.get("actor_id")), report=id(r.get("str_id"));
            String at=time(r.get("assessment_at")),known=time(r.get("known_at")), start=time(POLICY.get("from_inclusive")),end=time(POLICY.get("until_exclusive"));
            String licensed=state(r.get("licensed")),urgent=state(r.get("urgent"));
            String recipient=id(POLICY.get("counterparty_id"));Set<String> permitted=channels(POLICY.get("channels"));
            boolean inWindow=at.compareTo(start)>=0 && at.compareTo(end)<0;
            boolean observed=false, conflict=false, complete=false;
            List<Object> contacts=Json.list(r.get("contacts")), coverage=Json.list(r.get("coverage"));
            require(contacts.size()<=2000 && coverage.size()<=100);
            Map<String,String> identities=new HashMap<>();
            for(Object raw:contacts) {
                Map<String,Object> c=Json.map(raw);keys(c,"event","actor_id","counterparty_id","channel");
                String ca=id(c.get("actor_id")),cp=id(c.get("counterparty_id")),channel=Json.str(c.get("channel"));
                require(Set.of("EMAIL","PHONE","FAX","OTHER").contains(channel));
                Map<String,Object> e=Json.map(c.get("event"));
                keys(e,"event_id","str_id","kind","related_event_id","occurred_at","recorded_at","status","evidence_ids");
                String eid=id(e.get("event_id")),sr=id(e.get("str_id"));
                require("CONTACT".equals(e.get("kind")) && e.get("related_event_id")==null);
                String occurred=time(e.get("occurred_at")),recorded=time(e.get("recorded_at"));
                require(recorded.compareTo(occurred)>=0);evidence(e.get("evidence_ids"));
                String status=Json.str(e.get("status"));require(Set.of("CONFIRMED","DISPUTED").contains(status));
                String original=identities.putIfAbsent(eid,Json.write(c));require(original==null || original.equals(Json.write(c)));
                boolean relevant=ca.equals(actor) && cp.equals(recipient) && sr.equals(report) && permitted.contains(channel)
                    && occurred.compareTo(start)>=0 && occurred.compareTo(at)<=0 && recorded.compareTo(known)<=0;
                if(relevant) { observed=true;conflict|=status.equals("DISPUTED"); }
            }
            for(Object raw:coverage) {
                Map<String,Object> c=Json.map(raw);keys(c,"coverage","actor_id","counterparty_id","channels");
                String ca=id(c.get("actor_id")),cp=id(c.get("counterparty_id"));Set<String> ch=channels(c.get("channels"));
                Map<String,Object> v=Json.map(c.get("coverage"));
                keys(v,"str_id","kinds","from_inclusive","through_inclusive","recorded_at","evidence_ids");
                String sr=id(v.get("str_id")),from=time(v.get("from_inclusive")),through=time(v.get("through_inclusive")),recorded=time(v.get("recorded_at"));
                require(from.compareTo(through)<=0 && recorded.compareTo(through)>=0);evidence(v.get("evidence_ids"));
                List<Object> kinds=Json.list(v.get("kinds"));require(!kinds.isEmpty() && kinds.size()<=5);
                Set<String> ks=new HashSet<>();for(Object k:kinds) { String s=Json.str(k);
                    require(Set.of("CONTACT","ORIGINAL_SUBMISSION","RESUBMISSION","SCHEMA_VALIDATION","LIAISON").contains(s));require(ks.add(s)); }
                complete|=ca.equals(actor) && cp.equals(recipient) && sr.equals(report) && ch.containsAll(permitted)
                    && ks.contains("CONTACT") && from.compareTo(start)<=0 && through.compareTo(at)>=0 && recorded.compareTo(known)<=0;
            }
            String projected=!inWindow?"OUT_OF_SCOPE":conflict?"CONFLICT":observed?"TRUE":complete?"FALSE":"UNKNOWN";
            Map<String,Object> tf=Json.obj("licensed",fact(licensed,at),"urgent",fact(urgent,at),"in_window",fact(inWindow?"TRUE":"FALSE",at));
            Map<String,Object> trigger=TRIGGER_POLICY.evaluate(Json.obj("subject_id",report,"facts",tf),"selected.control",at,known,"draft");
            Map<String,Object> performance=inWindow?PERFORMANCE_POLICY.evaluate(Json.obj("subject_id",report,"facts",Json.obj("contact_observed",fact(projected,at))),
                "selected.control",at,known,"draft"):Json.obj("status","OUT_OF_SCOPE");
            return Json.write(Json.obj("boundary_status","ACCEPTED","profile","attributed-contact-history-v1","policy_hash",Json.hash(POLICY),
                "projected_status",projected,"trigger",trigger,"performance",performance,"overall_compliance","NOT_ESTABLISHED",
                "deadline_violation_established",false,"release_eligible",false));
        } catch(IllegalArgumentException | java.time.DateTimeException e) {
            return Json.write(Json.obj("boundary_status","REJECTED","error","E_SCHEMA","release_eligible",false));
        }
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=0)throw new IllegalArgumentException("No policy override accepted");
        BufferedReader reader=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));
        String line;while((line=reader.readLine())!=null)System.out.println(evaluate(line));
    }
}
