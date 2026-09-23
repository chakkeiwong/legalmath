package hk.legalmath.spi;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.function.Supplier;

/** Auditable support library for SPI-Demo1. No bank or network dependencies. */
public final class DecisionRuntime {
    private DecisionRuntime() {}

    public record Fact(String type, String status, Object value, List<String> evidenceIds,
                       String validFrom, String validUntil, String recordedAt, String reason) {
        public Fact {
            if (!Set.of("bool", "money_hkd", "integer").contains(type)) throw new IllegalArgumentException("E_TYPE");
            if (!Set.of("known", "unknown", "conflict").contains(status)) throw new IllegalArgumentException("E_STATUS");
            evidenceIds = List.copyOf(evidenceIds);
            evidenceIds.forEach(DecisionRuntime::identifier);
            if (status.equals("known")) {
                if (type.equals("bool") ? !(value instanceof Boolean) : !(value instanceof BigInteger))
                    throw new IllegalArgumentException("E_TYPE");
                if (evidenceIds.isEmpty()) throw new IllegalArgumentException("E_EVIDENCE");
                timestamp(validFrom); timestamp(recordedAt);
                if (validUntil != null && !timestamp(validUntil).isAfter(timestamp(validFrom)))
                    throw new IllegalArgumentException("E_INTERVAL");
            } else if (value != null) throw new IllegalArgumentException("E_UNKNOWN_VALUE");
            if (status.equals("conflict") && evidenceIds.size() < 2) throw new IllegalArgumentException("E_EVIDENCE");
            if (status.equals("unknown") && !Set.of("MISSING", "STALE", "UNREVIEWED_ASSESSMENT", "ORDER_UNRESOLVED").contains(reason))
                throw new IllegalArgumentException("E_REASON");
        }
        public static Fact known(String type, Object value, List<String> evidence, String from, String until, String recorded) {
            return new Fact(type, "known", value, evidence, from, until, recorded, null);
        }
        public static Fact unknown(String type, String reason) {
            return new Fact(type, "unknown", null, List.of(), null, null, null, reason);
        }
        public static Fact conflict(String type, List<String> evidence) {
            return new Fact(type, "conflict", null, evidence, null, null, null, null);
        }
        public Map<String,Object> json() {
            var m = new TreeMap<String,Object>(); m.put("type", type); m.put("status", status);
            if (status.equals("known")) {
                m.put("value", value instanceof BigInteger ? value.toString() : value);
                m.put("evidence_ids", evidenceIds); m.put("valid_from", validFrom);
                m.put("valid_until", validUntil); m.put("recorded_at", recordedAt);
            } else if (status.equals("unknown")) m.put("reason", reason);
            else m.put("evidence_ids", evidenceIds);
            return m;
        }
    }

    public record Snapshot(String subjectId, Map<String,Fact> facts) {
        public Snapshot { identifier(subjectId); facts = Map.copyOf(facts); }
        public Snapshot with(String name, Fact fact) { var m = new TreeMap<>(facts); m.put(name,fact); return new Snapshot(subjectId,m); }
        public String hash() {
            var fs = new TreeMap<String,Object>(); facts.forEach((k,v)->fs.put(k,v.json()));
            return sha256(json(Map.of("subject_id",subjectId,"facts",fs)));
        }
    }

    public record Value(Object value, Set<String> blockers) {
        public Value { blockers = Set.copyOf(blockers); }
        public static Value of(Object value) { return new Value(value,Set.of()); }
        public String status() { return value == null ? "UNKNOWN" : value.toString().toUpperCase(Locale.ROOT); }
    }

    public static final class Context {
        final Snapshot snapshot;
        final String validAt, knownAt, bundleHash;
        final Map<String,Value> memo = new HashMap<>();
        final List<Map<String,Object>> trace = new ArrayList<>();
        final Set<String> encountered = new TreeSet<>();
        public Context(Snapshot snapshot, String validAt, String knownAt, String bundleHash, Map<String,String> declarations) {
            timestamp(validAt); timestamp(knownAt);
            this.snapshot=snapshot; this.validAt=validAt; this.knownAt=knownAt; this.bundleHash=bundleHash;
            if (!declarations.keySet().equals(snapshot.facts().keySet())) throw new IllegalArgumentException("E_FACT_SET");
            declarations.forEach((n,t)->{ if (!t.equals(snapshot.facts().get(n).type())) throw new IllegalArgumentException("E_TYPE:"+n); });
        }
        public Value fact(String name) {
            var f=snapshot.facts().get(name);
            if (!f.status().equals("known") || validAt.compareTo(f.validFrom())<0
                    || (f.validUntil()!=null && validAt.compareTo(f.validUntil())>=0)
                    || knownAt.compareTo(f.recordedAt())<0) {
                encountered.add(name); return new Value(null,Set.of(name));
            }
            return Value.of(f.value());
        }
        public Value rule(String name, List<String> sources, Supplier<Value> body) {
            if (memo.containsKey(name)) return memo.get(name);
            var v=body.get(); memo.put(name,v);
            trace.add(Map.of("rule_id",name,"status",v.status(),"source_span_ids",sources,
                             "blocking_inputs",new TreeSet<>(v.blockers())));
            return v;
        }
        public Set<String> conflicts() {
            var names=new TreeSet<String>(); snapshot.facts().forEach((n,f)->{if(f.status().equals("conflict"))names.add(n);});
            return names;
        }
        public Result finish(String status, Set<String> blockers) {
            String disposition=switch(status) {case "TRUE"->"STREAMLINING_CONDITIONS_MET"; case "FALSE"->"STANDARD_PROCESS_REQUIRED"; case "OUT_OF_SCOPE"->"OUTSIDE_PROFILE"; default->"REVIEW_REQUIRED";};
            var m=new TreeMap<String,Object>();
            m.put("profile","SPI-Demo1");m.put("status",status);m.put("disposition",disposition);
            m.put("blocking_inputs",new TreeSet<>(blockers));m.put("missing_inputs",new TreeSet<>(encountered));
            m.put("trace",List.copyOf(trace));m.put("bundle_hash",bundleHash);m.put("snapshot_hash",snapshot.hash());
            m.put("valid_at",validAt);m.put("known_at",knownAt);m.put("authority","DEMONSTRATION_ONLY");
            m.put("result_hash",sha256(json(m)));
            return new Result(status,disposition,json(m));
        }
    }
    public record Result(String status, String disposition, String json) {}

    public static Value all(Value... args) { return booleanGroup(false,args); }
    public static Value any(Value... args) { return booleanGroup(true,args); }
    private static Value booleanGroup(boolean decisive, Value[] args) {
        var blockers=new TreeSet<String>(); boolean unknown=false;
        for(var v:args) {
            if(Boolean.valueOf(decisive).equals(v.value()))return Value.of(decisive);
            if(v.value()==null){unknown=true;blockers.addAll(v.blockers());}
        }
        return unknown ? new Value(null,blockers) : Value.of(!decisive);
    }
    public static Value not(Value v) { return v.value()==null?v:Value.of(!((Boolean)v.value())); }
    public static Value compare(String op, Value a, Value b) {
        if(a.value()==null||b.value()==null) {var bs=new TreeSet<>(a.blockers());bs.addAll(b.blockers());return new Value(null,bs);}
        int cmp=((BigInteger)a.value()).compareTo((BigInteger)b.value());
        return Value.of(switch(op){case "ge"->cmp>=0;case "gt"->cmp>0;case "eq"->cmp==0;default->throw new IllegalArgumentException("E_COMPARE");});
    }
    public static Instant timestamp(String s) {
        if(s==null||!s.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{6}Z")||s.startsWith("0000")||s.substring(17,19).equals("60"))
            throw new IllegalArgumentException("E_TIME");
        return Instant.parse(s);
    }
    public static void identifier(String s) {
        if(s==null||!s.matches("[a-z][a-z0-9_.-]*"))throw new IllegalArgumentException("E_IDENTIFIER");
    }
    public static String sha256(String s) {
        try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));}
        catch(java.security.NoSuchAlgorithmException e){throw new IllegalStateException(e);}
    }
    public static String json(Object x) {
        if(x==null)return "null";
        if(x instanceof String s) {
            var out=new StringBuilder("\"");
            for(int i=0;i<s.length();i++){char c=s.charAt(i);switch(c){case '"'->out.append("\\\"");case '\\'->out.append("\\\\");case '\n'->out.append("\\n");case '\r'->out.append("\\r");case '\t'->out.append("\\t");case '\b'->out.append("\\b");case '\f'->out.append("\\f");default->{if(c<32)out.append(String.format("\\u%04x",(int)c));else out.append(c);}}}
            return out.append('"').toString();
        }
        if(x instanceof Boolean)return x.toString();
        if(x instanceof Map<?,?> map){var parts=new ArrayList<String>();var sorted=new TreeMap<String,Object>();map.forEach((k,v)->sorted.put((String)k,v));sorted.forEach((k,v)->parts.add(json(k)+":"+json(v)));return "{"+String.join(",",parts)+"}";}
        if(x instanceof Collection<?> list){var parts=new ArrayList<String>();list.forEach(v->parts.add(json(v)));return "["+String.join(",",parts)+"]";}
        throw new IllegalArgumentException("E_JSON_TYPE");
    }
}
