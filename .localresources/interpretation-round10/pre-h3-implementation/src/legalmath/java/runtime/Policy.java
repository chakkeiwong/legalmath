package hk.legalmath;

import java.math.BigInteger;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/** Immutable compiled policy; each call creates an isolated evaluation context. */
public final class Policy {
    public static final String ENGINE="legalmath-java/0.1.0";
    private final Map<String,Object> bundle;
    private final Map<String,Map<String,Object>> rules=new HashMap<>();
    private final Map<String,String> types=new HashMap<>(), pointers=new HashMap<>(), factTypes=new HashMap<>();
    Policy(String compiledBundle) {
        bundle=Json.map(Json.freeze(Json.parse(compiledBundle)));
        for(Object f:Json.list(bundle.get("facts")))factTypes.put(s(m(f),"name"),s(m(f),"type"));
        for(Object r:Json.list(bundle.get("rules")))rules.put(s(m(r),"id"),m(r));
        int i=0;for(Object r:Json.list(bundle.get("rules"))){for(String f:List.of("scope","body"))infer(m(m(r).get(f)),"/bundle/rules/"+i+"/"+f);i++;}
    }
    static Map<String,Object> m(Object v){return Json.map(v);}
    static String s(Map<String,Object> v,String k){return Json.str(v.get(k));}
    static List<String> strings(Object v){List<String> out=new ArrayList<>();for(Object x:Json.list(v))out.add(Json.str(x));return out;}
    static Map<String,Object> diag(String code,String ptr){
        String text=switch(code){
            case "E_SCHEMA" -> "Input does not conform to the schema.";
            case "E_REFERENCE" -> "Reference does not resolve.";
            case "E_TYPE" -> "Types do not satisfy the operator contract.";
            case "E_DUPLICATE_ID" -> "Identifier is not unique.";
            case "E_TIME" -> "Timestamp or interval is invalid.";
            case "E_VERSION_TIME" -> "Assessment time is outside the bundle interval.";
            case "E_INEXACT_SCALE" -> "Scaling would require a fractional result.";
            default -> throw new IllegalArgumentException(code);
        };
        return Json.obj("code",code,"pointer",ptr,"message",text);
    }
    public static void time(String t){
        if(!t.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{6}Z") || t.startsWith("0000"))throw new Json.Invalid();
        try{OffsetDateTime.parse(t);}catch(DateTimeParseException e){throw new Json.Invalid();}
    }
    static boolean eligible(String start,Object end,String at){return start.compareTo(at)<=0 && (end==null||at.compareTo((String)end)<0);}
    static boolean scalar(String type,Object value){
        if(type.equals("bool"))return value instanceof Boolean;
        if(!(value instanceof String))return false;
        if(type.equals("integer")||type.equals("money_hkd"))return ((String)value).matches("0|-?[1-9][0-9]*");
        if(type.equals("date")&&((String)value).matches("[0-9]{4}-[0-9]{2}-[0-9]{2}")&&!((String)value).startsWith("0000")){
            try{LocalDate.parse((String)value);return true;}catch(DateTimeParseException e){return false;}
        }return false;
    }
    static List<Map<String,Object>> children(Map<String,Object> n){
        List<Map<String,Object>> out=new ArrayList<>();
        switch(s(n,"op")){
            case "all":case "any":for(Object x:Json.list(n.get("args")))out.add(m(x));break;
            case "not":case "scale":out.add(m(n.get("arg")));break;
            case "add":case "sub":case "compare":out.add(m(n.get("left")));out.add(m(n.get("right")));break;
            case "if":for(String k:List.of("condition","then","else"))out.add(m(n.get(k)));break;
            case "default":out.add(m(n.get("base")));for(Object x:Json.list(n.get("exceptions"))){out.add(m(m(x).get("guard")));out.add(m(m(x).get("value")));}break;
            default:break;
        }return out;
    }
    private String infer(Map<String,Object> n,String ptr){
        String op=s(n,"op");List<String> parts=new ArrayList<>();
        switch(op){
            case "all":case "any":for(int i=0;i<Json.list(n.get("args")).size();i++)parts.add("args/"+i);break;
            case "not":case "scale":parts.add("arg");break;
            case "add":case "sub":case "compare":parts.addAll(List.of("left","right"));break;
            case "if":parts.addAll(List.of("condition","then","else"));break;
            case "default":parts.add("base");for(int i=0;i<Json.list(n.get("exceptions")).size();i++){parts.add("exceptions/"+i+"/guard");parts.add("exceptions/"+i+"/value");}break;
            default:break;
        }
        List<String> ct=new ArrayList<>();List<Map<String,Object>> cs=children(n);
        for(int i=0;i<cs.size();i++)ct.add(infer(cs.get(i),ptr+"/"+parts.get(i)));
        String type=switch(op){
            case "literal" -> s(n,"type");case "fact" -> factTypes.get(s(n,"name"));case "rule" -> s(rules.get(s(n,"name")),"type");
            case "all","any","not","compare" -> "bool";case "if" -> ct.get(1);default -> ct.get(0);
        };
        types.put(s(n,"node_id"),type);pointers.put(s(n,"node_id"),ptr);return type;
    }
    public String evaluate(String snapshotJson,String ruleId,String validAt,String knownAt,String mode){
        Object value=Json.parse(snapshotJson);
        if(!(value instanceof Map<?,?>))return Json.write(malformedSnapshot(value,ruleId,validAt,knownAt,mode));
        return Json.write(evaluate(Json.map(value),ruleId,validAt,knownAt,mode));
    }
    private Map<String,Object> malformedSnapshot(Object snapshot,String ruleId,String validAt,String knownAt,String mode){
        time(validAt);time(knownAt);if(!List.of("draft","production","replay").contains(mode))throw new Json.Invalid();
        Map<String,Object> result=Json.obj("status","ERROR","type",null,"mode",mode,"diagnostics",List.of(diag("E_SCHEMA","/snapshot")),
            "reason_codes",List.of("E_SCHEMA"),"missing_inputs",List.of(),"blocking_inputs",List.of(),"trace",List.of(),
            "bundle_hash",Json.hash(bundle),"snapshot_hash",Json.hash(snapshot),"engine_version",ENGINE,"valid_at",validAt,"known_at",knownAt);
        result.put("result_hash",executionHash(result,ruleId));return m(Json.freeze(result));
    }
    public Map<String,Object> evaluate(Map<String,Object> input,String ruleId,String validAt,String knownAt,String mode){
        if(input==null)return malformedSnapshot(null,ruleId,validAt,knownAt,mode);
        Map<String,Object> snapshot=m(Json.freeze(Json.parse(Json.write(input))));
        time(validAt);time(knownAt);if(!List.of("draft","production","replay").contains(mode))throw new Json.Invalid();
        List<Map<String,Object>> errors=validateSnapshot(snapshot);String type=rules.containsKey(ruleId)?s(rules.get(ruleId),"type"):null;
        List<Object> trace=new ArrayList<>();List<String> blocking=null;V value;
        if(errors.isEmpty()&&!rules.containsKey(ruleId))errors.add(diag("E_REFERENCE","/rule_id"));
        if(!errors.isEmpty()){
            value=new V(null,"ERROR",null);value.diags.addAll(errors);for(Map<String,Object> e:errors)value.reasons.add(s(e,"code"));
        }else if(!eligible(s(bundle,"valid_from"),bundle.get("valid_until"),validAt)){
            value=new V(type,"ERROR",null);value.reasons.add("E_VERSION_TIME");value.diags.add(diag("E_VERSION_TIME","/valid_at"));
        }else{
            Set<String> closure=new TreeSet<>();closure(ruleId,new HashSet<>(),closure);List<String> conflict=new ArrayList<>();
            Map<String,Object> facts=m(snapshot.get("facts"));for(String name:closure)if(s(m(facts.get(name)),"status").equals("conflict"))conflict.add(name);
            if(!conflict.isEmpty()){value=new V(type,"CONFLICT",null);value.reasons.add("INPUT_CONFLICT");blocking=conflict;}
            else{Context c=new Context(facts,validAt,knownAt);value=c.rule(ruleId);trace=c.trace;}
        }
        if(blocking==null)blocking=List.of("TRUE","FALSE","VALUE","OUT_OF_SCOPE").contains(value.status)?new ArrayList<>():new ArrayList<>(value.missing);
        Map<String,Object> result=Json.obj("status",value.status,"type",value.type,"mode",mode,"diagnostics",value.diags,"reason_codes",new ArrayList<>(value.reasons),
            "missing_inputs",new ArrayList<>(value.missing),"blocking_inputs",blocking,"trace",trace,"bundle_hash",Json.hash(bundle),"snapshot_hash",Json.hash(snapshot),
            "engine_version",ENGINE,"valid_at",validAt,"known_at",knownAt);
        if(value.known())result.put("value",value.value);
        result.put("result_hash",executionHash(result,ruleId));return m(Json.freeze(result));
    }
    public static String executionHash(Map<String,Object> result,String ruleId){
        Map<String,Object> request=Json.obj("rule_id",ruleId),semantic=Json.obj();
        for(String k:List.of("bundle_hash","snapshot_hash","mode","valid_at","known_at","engine_version"))request.put(k,result.get(k));
        for(String k:List.of("status","type","mode","diagnostics","value","reason_codes","missing_inputs","blocking_inputs","trace"))if(result.containsKey(k))semantic.put(k,result.get(k));
        return Json.hash(Json.obj("request",request,"result",semantic));
    }
    private List<Map<String,Object>> validateSnapshot(Map<String,Object> snap){
        List<Map<String,Object>> errors=new ArrayList<>();
        if(!snap.keySet().equals(Set.of("subject_id","facts")))errors.add(diag("E_SCHEMA","/snapshot"));
        if(snap.containsKey("subject_id")&&(!(snap.get("subject_id") instanceof String)||!s(snap,"subject_id").matches("[a-z][a-z0-9_.-]*")))errors.add(diag("E_SCHEMA","/snapshot/subject_id"));
        if(snap.containsKey("facts")&&!(snap.get("facts") instanceof Map<?,?>))errors.add(diag("E_SCHEMA","/snapshot/facts"));
        Map<String,Object> facts=snap.get("facts") instanceof Map<?,?>?m(snap.get("facts")):Json.obj();
        for(String name:new TreeSet<>(facts.keySet())){
            if(!name.matches("[a-z][a-z0-9_.-]*"))errors.add(diag("E_SCHEMA","/snapshot/facts"));
            String ptr="/snapshot/facts/"+name;Object raw=facts.get(name);
            if(!(raw instanceof Map<?,?>)){errors.add(diag("E_SCHEMA",ptr));continue;}
            Map<String,Object> f=m(raw);String status=f.get("status") instanceof String?s(f,"status"):"";
            Set<String> keys=switch(status){
                case "known" -> Set.of("status","type","value","evidence_ids","valid_from","valid_until","recorded_at");
                case "unknown" -> Set.of("status","type","reason");case "conflict" -> Set.of("status","type","evidence_ids");default -> Set.of();
            };
            boolean ok=f.keySet().equals(keys)&&f.get("type") instanceof String&&List.of("bool","integer","money_hkd","date").contains(f.get("type"));
            if(ok&&status.equals("known")){
                ok=scalar(s(f,"type"),f.get("value"));
                try{time(s(f,"valid_from"));time(s(f,"recorded_at"));if(f.get("valid_until")!=null)time(s(f,"valid_until"));}catch(IllegalArgumentException e){ok=false;}
            }
            if(ok&&status.equals("unknown"))ok=List.of("MISSING","STALE","UNREVIEWED_ASSESSMENT","ORDER_UNRESOLVED").contains(f.get("reason"));
            if(ok&&!status.equals("unknown")){
                try{List<String> ids=strings(f.get("evidence_ids"));ok=ids.size()>=(status.equals("conflict")?2:1)&&ids.stream().allMatch(x->x.matches("[a-z][a-z0-9_.-]*"));}catch(IllegalArgumentException e){ok=false;}
            }
            if(!ok)errors.add(diag("E_SCHEMA",ptr));
        }
        if(!errors.isEmpty())return orderedErrors(errors);
        Set<String> names=new TreeSet<>(facts.keySet());names.addAll(factTypes.keySet());
        for(String name:names){
            String ptr="/snapshot/facts/"+name;
            if(!factTypes.containsKey(name)||!facts.containsKey(name)){errors.add(diag("E_REFERENCE",ptr));continue;}
            Map<String,Object> f=m(facts.get(name));
            if(!factTypes.get(name).equals(f.get("type")))errors.add(diag("E_TYPE",ptr));
            if(s(f,"status").equals("known")&&f.get("valid_until")!=null&&s(f,"valid_until").compareTo(s(f,"valid_from"))<=0)errors.add(diag("E_TIME",ptr));
            if(f.containsKey("evidence_ids")&&new HashSet<>(strings(f.get("evidence_ids"))).size()!=Json.list(f.get("evidence_ids")).size())errors.add(diag("E_DUPLICATE_ID",ptr+"/evidence_ids"));
        }
        if(!errors.isEmpty()){
            int first=errors.stream().mapToInt(e->stage(s(e,"code"))).min().orElse(0);
            errors.removeIf(e->stage(s(e,"code"))!=first);
            errors.sort(java.util.Comparator.comparing((Map<String,Object> e)->s(e,"pointer")).thenComparing(e->s(e,"code")));
        }
        return orderedErrors(errors);
    }
    private static List<Map<String,Object>> orderedErrors(List<Map<String,Object>> errors){
        Map<String,Map<String,Object>> unique=new java.util.TreeMap<>();
        for(Map<String,Object> e:errors)unique.put(s(e,"pointer")+"\u0000"+s(e,"code"),e);
        return new ArrayList<>(unique.values());
    }
    private static int stage(String code){return switch(code){case "E_REFERENCE","E_DUPLICATE_ID" -> 1;case "E_TYPE" -> 2;case "E_TIME" -> 4;default -> 0;};}
    private void closure(String name,Set<String> seen,Set<String> facts){if(!seen.add(name))return;for(String f:List.of("scope","body"))scan(m(rules.get(name).get(f)),seen,facts);}
    private void scan(Map<String,Object> node,Set<String> seen,Set<String> facts){String op=s(node,"op");if(op.equals("fact"))facts.add(s(node,"name"));if(op.equals("rule"))closure(s(node,"name"),seen,facts);for(Map<String,Object> n:children(node))scan(n,seen,facts);}
    private static final class V {
        final String type,status;final Object value;
        final TreeSet<String> reasons=new TreeSet<>(),missing=new TreeSet<>(),evidence=new TreeSet<>();
        final List<Map<String,Object>> diags=new ArrayList<>();
        V(String t,String s,Object v){type=t;status=s;value=v;}
        boolean known(){return List.of("TRUE","FALSE","VALUE").contains(status);}
    }
    private static V known(String t,Object v){return new V(t,t.equals("bool")?((Boolean)v?"TRUE":"FALSE"):"VALUE",v);}
    private static V combine(String t,List<V> values,String status,Object value){
        V bad=null;for(V v:values)if(v.status.equals("ERROR")){bad=v;break;}if(bad==null)for(V v:values)if(v.status.equals("CONFLICT")){bad=v;break;}
        V out=new V(t,bad==null?status:bad.status,bad==null?value:null);
        for(V v:values){out.reasons.addAll(v.reasons);out.missing.addAll(v.missing);out.evidence.addAll(v.evidence);}
        if(bad!=null){out.reasons.clear();out.reasons.addAll(bad.reasons);out.diags.addAll(bad.diags);}return out;
    }
    private final class Context {
        final Map<String,Object> facts;final String at,cutoff;final List<Object> trace=new ArrayList<>();
        final Map<String,V> memo=new HashMap<>(),ruleMemo=new HashMap<>();
        Context(Map<String,Object> f,String a,String k){facts=f;at=a;cutoff=k;}
        V add(Map<String,Object> n,Map<String,Object> rule,V v,List<String> kids){
            Map<String,Object> t=Json.obj("node_id",s(n,"node_id"),"op",s(n,"op"),"children",kids,"type",v.type,"status",v.status,
                "evidence_ids",new ArrayList<>(v.evidence),"source_span_ids",new ArrayList<>(new TreeSet<>(strings(rule.get("source_span_ids")))));
            if(v.known())t.put("value",v.value);trace.add(t);memo.put(s(n,"node_id"),v);return v;
        }
        void skip(Map<String,Object> n,Map<String,Object> r){if(!memo.containsKey(s(n,"node_id")))add(n,r,new V(types.get(s(n,"node_id")),"SKIPPED",null),List.of());}
        V rule(String name){
            if(ruleMemo.containsKey(name))return ruleMemo.get(name);Map<String,Object> r=rules.get(name);V scope=node(m(r.get("scope")),r),out;
            if(scope.status.equals("TRUE")){V body=node(m(r.get("body")),r);out=combine(s(r,"type"),List.of(scope,body),body.status,body.value);}
            else{skip(m(r.get("body")),r);out=combine(s(r,"type"),List.of(scope),scope.status.equals("FALSE")?"OUT_OF_SCOPE":"UNKNOWN",null);if(scope.status.equals("UNKNOWN"))out.reasons.add("SCOPE_UNKNOWN");}
            ruleMemo.put(name,out);return out;
        }
        V node(Map<String,Object> n,Map<String,Object> r){
            String id=s(n,"node_id"),op=s(n,"op"),type=types.get(id);if(memo.containsKey(id))return memo.get(id);
            List<String> kids=new ArrayList<>();for(Map<String,Object> c:children(n))kids.add(s(c,"node_id"));V out;
            switch(op){
                case "literal":out=known(type,n.get("value"));break;
                case "fact":{
                    Map<String,Object> f=m(facts.get(s(n,"name")));
                    if(s(f,"status").equals("known")&&eligible(s(f,"valid_from"),f.get("valid_until"),at)&&s(f,"recorded_at").compareTo(cutoff)<=0){out=known(type,f.get("value"));out.evidence.addAll(strings(f.get("evidence_ids")));}
                    else{out=new V(type,"UNKNOWN",null);out.missing.add(s(n,"name"));out.reasons.add(f.containsKey("reason")?s(f,"reason"):s(f,"recorded_at").compareTo(cutoff)<=0?"STALE":"MISSING");}break;
                }
                case "rule":out=rule(s(n,"name"));kids.clear();for(String f:List.of("scope","body"))kids.add(s(m(rules.get(s(n,"name")).get(f)),"node_id"));break;
                case "if":{
                    V c=node(m(n.get("condition")),r);String chosen=c.status.equals("TRUE")?"then":c.status.equals("FALSE")?"else":"";List<V> values=new ArrayList<>();values.add(c);
                    for(String f:List.of("then","else")){if(f.equals(chosen))values.add(node(m(n.get(f)),r));else skip(m(n.get(f)),r);}
                    V last=values.get(values.size()-1);out=combine(type,values,chosen.isEmpty()?"UNKNOWN":last.status,chosen.isEmpty()?null:last.value);break;
                }
                case "default":{
                    List<V> gs=new ArrayList<>();List<Object> exceptions=Json.list(n.get("exceptions"));for(Object e:exceptions)gs.add(node(m(m(e).get("guard")),r));
                    Map<String,Object> selected=null;String state=null;
                    if(gs.stream().anyMatch(v->v.status.equals("ERROR")||v.status.equals("CONFLICT")))state="UNKNOWN";
                    else if(gs.stream().filter(v->v.status.equals("TRUE")).count()>1)state="CONFLICT";
                    else if(gs.stream().anyMatch(v->v.status.equals("UNKNOWN")))state="UNKNOWN";
                    else{selected=m(n.get("base"));for(int i=0;i<gs.size();i++)if(gs.get(i).status.equals("TRUE"))selected=m(m(exceptions.get(i)).get("value"));}
                    List<V> values=new ArrayList<>(gs);List<Map<String,Object>> choices=new ArrayList<>();choices.add(m(n.get("base")));for(Object e:exceptions)choices.add(m(m(e).get("value")));
                    for(Map<String,Object> c:choices){if(c==selected)values.add(node(c,r));else skip(c,r);}
                    V last=values.isEmpty()?null:values.get(values.size()-1);out=combine(type,values,state==null?last.status:state,selected==null?null:last.value);if("CONFLICT".equals(state))out.reasons.add("MULTIPLE_EXCEPTIONS");break;
                }
                default:{
                    List<V> vs=new ArrayList<>();for(Map<String,Object> c:children(n))vs.add(node(c,r));out=combine(type,vs,"UNKNOWN",null);
                    if(out.status.equals("ERROR")||out.status.equals("CONFLICT"))break;
                    if(op.equals("all")||op.equals("any")){
                        String target=op.equals("all")?"FALSE":"TRUE",other=op.equals("all")?"TRUE":"FALSE";
                        String status=vs.stream().anyMatch(v->v.status.equals(target))?target:vs.stream().anyMatch(v->v.status.equals("UNKNOWN"))?"UNKNOWN":other;
                        out=combine(type,vs,status,status.equals("UNKNOWN")?null:status.equals("TRUE"));
                    }else if(vs.stream().allMatch(v->!v.status.equals("UNKNOWN"))){
                        Object answer;
                        if(op.equals("not"))answer=!(Boolean)vs.get(0).value;
                        else if(op.equals("compare")){
                            int cmp=vs.get(0).type.equals("date")?((String)vs.get(0).value).compareTo((String)vs.get(1).value):new BigInteger((String)vs.get(0).value).compareTo(new BigInteger((String)vs.get(1).value));
                            answer=s(n,"cmp").equals("eq")?cmp==0:s(n,"cmp").equals("ge")?cmp>=0:cmp>0;
                        }else if(op.equals("add")||op.equals("sub")){
                            BigInteger a=new BigInteger((String)vs.get(0).value),b=new BigInteger((String)vs.get(1).value);answer=(op.equals("add")?a.add(b):a.subtract(b)).toString();
                        }else{
                            BigInteger[] q=new BigInteger((String)vs.get(0).value).multiply(new BigInteger(s(n,"numerator"))).divideAndRemainder(new BigInteger(s(n,"denominator")));
                            if(q[1].signum()!=0){out=combine(type,vs,"ERROR",null);out.reasons.clear();out.reasons.add("E_INEXACT_SCALE");out.diags.add(diag("E_INEXACT_SCALE",pointers.get(id)));return add(n,r,out,kids);}answer=q[0].toString();
                        }
                        out=combine(type,vs,type.equals("bool")?((Boolean)answer?"TRUE":"FALSE"):"VALUE",answer);
                    }break;
                }
            }return add(n,r,out,kids);
        }
    }
}
