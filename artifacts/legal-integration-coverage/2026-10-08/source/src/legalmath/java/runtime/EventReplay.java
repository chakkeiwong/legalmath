package hk.legalmath;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/** Finite attributed replay, independent of the decision evaluator. */
public final class EventReplay {
    public static final String ENGINE="legalmath-java-events/0.1.0";
    private EventReplay() {}
    private static final class Invalid extends RuntimeException {
        private static final long serialVersionUID=1L;
        final String code;
        Invalid(String code){this.code=code;}
    }
    private static Map<String,Object> m(Object x){return Json.map(x);}
    private static String s(Map<String,Object> m,String key){return Json.str(m.get(key));}
    private static boolean le(String a,String b){return a.compareTo(b)<=0;}
    private static long num(Object x){if(!(x instanceof Number))throw new Invalid("E_SCHEMA");return ((Number)x).longValue();}
    private static void check(boolean yes,String code){if(!yes)throw new Invalid(code);}
    private static void time(Object value){try{Policy.time(Json.str(value));}catch(IllegalArgumentException e){throw new Invalid("E_TIME");}}
    private static List<Map<String,Object>> validate(Map<String,Object> h,List<Object> events){
        check(h.keySet().equals(Set.of("stream_id","profile","inception","subject","category","actor","action","obligation_id","profile_version","ordering_authority","initial_snapshot")),"E_SCHEMA");
        check(List.of("consent","achievement").contains(h.get("profile"))&&"0.1".equals(h.get("profile_version")),"E_SCHEMA");
        for(String k:List.of("stream_id","subject","category","actor","action"))check(s(h,k).matches("[a-z][a-z0-9_.-]*"),"E_SCHEMA");
        time(h.get("inception"));
        boolean consent="consent".equals(h.get("profile"));
        check(consent||h.get("obligation_id")!=null,"E_EVENT_ATTRIBUTION");
        if(h.get("initial_snapshot")!=null){
            Map<String,Object> init=m(h.get("initial_snapshot"));
            check(init.keySet().equals(Set.of("as_of","state","generation","reviewer_id","evidence_id","recorded_at")),"E_SCHEMA");
            time(init.get("as_of"));time(init.get("recorded_at"));
            check(consent&&le(s(h,"inception"),s(init,"as_of"))&&le(s(init,"as_of"),s(init,"recorded_at")),"E_TIME");
            check(List.of("ACTIVE","WITHDRAWN","NOT_ESTABLISHED").contains(init.get("state"))&&num(init.get("generation"))>=0,"E_SCHEMA");
        }
        Map<String,Map<String,Object>> ids=new HashMap<>();Set<Long> seq=new HashSet<>();
        Set<String> required=Set.of("id","stream_id","sequence","kind","occurred_at","recorded_at","actor","action","subject","category","evidence_id","obligation_id");
        Set<String> allowed=new HashSet<>(required);allowed.addAll(List.of("activation","deadline","source_bundle_hash","complete_from","complete_through"));
        for(Object raw:events){
            Map<String,Object> e=m(raw);check(e.keySet().containsAll(required)&&allowed.containsAll(e.keySet()),"E_SCHEMA");
            time(e.get("occurred_at"));time(e.get("recorded_at"));
            for(String k:List.of("id","stream_id","actor","action","subject","category","evidence_id"))check(s(e,k).matches("[a-z][a-z0-9_.-]*"),"E_SCHEMA");
            for(String k:List.of("stream_id","subject","category","actor","action"))check(e.get(k).equals(h.get(k)),"E_EVENT_ATTRIBUTION");
            if(!consent)check(java.util.Objects.equals(e.get("obligation_id"),h.get("obligation_id")),"E_EVENT_ATTRIBUTION");
            List<String> kinds=consent?List.of("consent.granted","consent.withdrawn","transaction.observed"):List.of("obligation.opened","obligation.performed","watermark");
            check(kinds.contains(e.get("kind")),"E_UNSUPPORTED_PROFILE");
            String id=s(e,"id");long sequence=num(e.get("sequence"));check(sequence>0,"E_SCHEMA");
            if(ids.containsKey(id)){check(Json.hash(ids.get(id)).equals(Json.hash(e)),"E_EVENT_ID_COLLISION");continue;}
            check(seq.add(sequence),"E_SEQUENCE_COLLISION");ids.put(id,e);
            if("obligation.opened".equals(e.get("kind"))){
                check(e.keySet().containsAll(List.of("activation","deadline","source_bundle_hash")),"E_SCHEMA");
                check(s(e,"source_bundle_hash").matches("[0-9a-f]{64}"),"E_SCHEMA");time(e.get("activation"));
                if(e.get("deadline")!=null){time(e.get("deadline"));check(s(e,"activation").compareTo(s(e,"deadline"))<0,"E_TIME");}
            }
            if("watermark".equals(e.get("kind"))){check(e.containsKey("complete_from")&&e.containsKey("complete_through"),"E_SCHEMA");time(e.get("complete_from"));time(e.get("complete_through"));}
        }
        return new ArrayList<>(ids.values());
    }
    public static Map<String,Object> replay(Map<String,Object> request){
        Json.write(request);Map<String,Object> h=m(request.get("header"));String at=s(request,"valid_at"),cutoff=s(request,"known_at");Policy.time(at);Policy.time(cutoff);
        Map<String,Object> out=Json.obj("profile",h.get("profile"),"status","UNKNOWN","reason_codes",new ArrayList<>(),"event_ids",new ArrayList<>(),"evidence_ids",new ArrayList<>(),"valid_at",at,"known_at",cutoff,"source_bundle_hash",null);
        try{
            List<Map<String,Object>> events=validate(h,Json.list(request.get("events"))),selected=new ArrayList<>();Set<String> times=new HashSet<>();boolean tie=false;
            for(Map<String,Object> e:events)if(le(s(e,"occurred_at"),at)&&le(s(e,"recorded_at"),cutoff)){selected.add(e);if(!times.add(s(e,"occurred_at")))tie=true;}
            check(h.get("ordering_authority")!=null||!tie,"E_ORDER_UNRESOLVED");
            selected.sort(Comparator.comparing((Map<String,Object> e)->s(e,"occurred_at")).thenComparingLong(e->num(e.get("sequence"))));
            List<String> eventIds=new ArrayList<>();Set<String> evidence=new TreeSet<>();for(Map<String,Object> e:selected){eventIds.add(s(e,"id"));evidence.add(s(e,"evidence_id"));}out.put("event_ids",eventIds);
            if("consent".equals(h.get("profile"))){
                String state="NOT_ESTABLISHED",start=s(h,"inception");long generation=0;Map<String,Object> init=h.get("initial_snapshot")==null?null:m(h.get("initial_snapshot"));
                if(init!=null&&le(s(init,"recorded_at"),cutoff)&&le(s(init,"as_of"),at)){state=s(init,"state");generation=num(init.get("generation"));start=s(init,"as_of");evidence.add(s(init,"evidence_id"));}
                boolean complete=false;
                if(request.get("completeness")!=null){
                    Map<String,Object> seal=m(request.get("completeness"));check(seal.keySet().equals(Set.of("complete_from","complete_through","recorded_at","evidence_id")),"E_SCHEMA");
                    for(String k:List.of("complete_from","complete_through","recorded_at"))time(seal.get(k));
                    complete=le(s(seal,"complete_from"),start)&&le(start,at)&&le(at,s(seal,"complete_through"))&&le(s(seal,"complete_through"),s(seal,"recorded_at"))&&le(s(seal,"recorded_at"),cutoff);evidence.add(s(seal,"evidence_id"));
                }
                Set<String> grants=new HashSet<>();List<String> violations=new ArrayList<>();
                if(init!=null&&start.equals(init.get("as_of"))&&state.equals("ACTIVE"))grants.add(s(init,"evidence_id"));
                for(Map<String,Object> e:selected){
                    if(s(e,"occurred_at").compareTo(start)<0||(init!=null&&start.equals(init.get("as_of"))&&s(e,"occurred_at").equals(start)))continue;
                    switch(s(e,"kind")){
                        case "consent.granted":check(grants.add(s(e,"evidence_id")),"E_EVENT_ID_COLLISION");state="ACTIVE";generation++;break;
                        case "consent.withdrawn":state="WITHDRAWN";break;
                        case "transaction.observed":if(!state.equals("ACTIVE"))violations.add(s(e,"id"));break;
                        default:break;
                    }
                }
                out.put("state",complete?state:"UNKNOWN");out.put("generation",generation);out.put("violation_candidates",violations);out.put("status",complete?"RESOLVED":"UNKNOWN");out.put("reason_codes",complete?List.of():List.of("HISTORY_INCOMPLETE"));
            }else{
                List<Map<String,Object>> openings=new ArrayList<>();for(Map<String,Object> e:selected)if(s(e,"kind").equals("obligation.opened"))openings.add(e);
                check(openings.size()<=1,"E_EVENT_ID_COLLISION");out.put("breached",false);out.put("breach_id",null);out.put("performance_event_id",null);
                if(openings.isEmpty())out.put("reason_codes",List.of("ACTIVATION_UNKNOWN"));
                else{
                    Map<String,Object> opening=openings.get(0);String activation=s(opening,"activation"),deadline=(String)opening.get("deadline");out.put("source_bundle_hash",opening.get("source_bundle_hash"));
                    List<Map<String,Object>> performances=new ArrayList<>(),timely=new ArrayList<>();boolean complete=false;
                    for(Map<String,Object> e:selected){
                        if(s(e,"kind").equals("obligation.performed")&&le(activation,s(e,"occurred_at"))){performances.add(e);if(deadline==null||s(e,"occurred_at").compareTo(deadline)<0)timely.add(e);}
                        if(s(e,"kind").equals("watermark")&&deadline!=null&&le(s(e,"complete_from"),activation)&&le(deadline,s(e,"complete_through"))&&le(s(e,"complete_through"),s(e,"recorded_at"))&&le(s(e,"complete_through"),at))complete=true;
                    }
                    if(!timely.isEmpty()){out.put("status","SATISFIED_ON_TIME");out.put("performance_event_id",timely.get(0).get("id"));}
                    else if(deadline!=null&&le(deadline,at)&&complete){out.put("status",performances.isEmpty()?"BREACHED":"PERFORMED_LATE");out.put("breached",true);out.put("breach_id",Json.hash(Json.obj("opening_id",opening.get("id"),"deadline",deadline)));if(!performances.isEmpty())out.put("performance_event_id",performances.get(0).get("id"));}
                    else{out.put("status","OPEN");if(!performances.isEmpty())out.put("performance_event_id",performances.get(0).get("id"));}
                }
            }
            out.put("evidence_ids",new ArrayList<>(evidence));
        }catch(Invalid e){out.put("status","ERROR");out.put("reason_codes",List.of(e.code));}
        catch(Json.Invalid e){out.put("status","ERROR");out.put("reason_codes",List.of("E_SCHEMA"));}
        out.put("engine_version",ENGINE);String hash=Json.hash(Json.obj("request",request,"result",out));out.put("result_hash",hash);return Json.map(Json.freeze(out));
    }
}
