package hk.legalmath;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Fixed-evidence positive Horn agenda. Not defeasible or negative-head logic. */
public final class ConditionalHorn {
    private static void keys(Map<String,Object> m, String... expected) {
        if (!m.keySet().equals(Set.of(expected))) throw new Json.Invalid();
    }
    private static int integer(Object value, int max) {
        if (!(value instanceof Long)) throw new Json.Invalid();
        long n=(Long)value;
        if(n<0 || n>max) throw new Json.Invalid();
        return (int)n;
    }
    private static List<Object> bounded(Object value,int max) {
        List<Object> xs=Json.list(value);
        if(xs.size()>max) throw new Json.Invalid();
        return xs;
    }
    private static void ids(List<Object> xs) {
        Set<String> seen=new HashSet<>();
        for(Object x:xs) {
            String s=Json.str(x);
            if(s.isEmpty() || s.codePointCount(0,s.length())>20000 || !seen.add(s)) throw new Json.Invalid();
        }
    }
    private static int[] indices(Object value,int bound) {
        List<Object> xs=bounded(value,32);
        int[] out=new int[xs.size()]; Set<Integer> seen=new HashSet<>();
        for(int i=0;i<out.length;i++) {
            out[i]=integer(xs.get(i),bound-1);
            if(!seen.add(out[i]))throw new Json.Invalid();
        }
        return out;
    }
    public static Object evaluate(Object value) {
        Map<String,Object> p=Json.map(value);
        keys(p,"profile","context_hash","fact_ids","codes","heads","rules");
        if(!"legalmath.conditional-horn.v1".equals(p.get("profile"))) throw new Json.Invalid();
        if(!Json.str(p.get("context_hash")).matches("[0-9a-f]{64}"))throw new Json.Invalid();
        List<Object> facts=bounded(p.get("fact_ids"),1024), codes=bounded(p.get("codes"),1024);
        List<Object> heads=bounded(p.get("heads"),64), rules=bounded(p.get("rules"),64);
        if(heads.isEmpty() || facts.size()!=codes.size())throw new Json.Invalid();
        ids(facts);ids(heads);
        int[] states=new int[codes.size()];
        for(int i=0;i<states.length;i++)states[i]=integer(codes.get(i),3);
        int n=rules.size();int[] targets=new int[n],remaining=new int[n];
        boolean[] eligible=new boolean[n],reached=new boolean[heads.size()];
        List<List<Integer>> waiting=new ArrayList<>();
        for(int i=0;i<heads.size();i++)waiting.add(new ArrayList<>());
        Set<String> names=new HashSet<>();
        ArrayDeque<Integer> agenda=new ArrayDeque<>();
        for(int i=0;i<n;i++) {
            Map<String,Object> r=Json.map(rules.get(i));
            keys(r,"id","head","facts","parents");
            String id=Json.str(r.get("id"));
            if(id.isEmpty() || id.codePointCount(0,id.length())>20000 || !names.add(id))throw new Json.Invalid();
            targets[i]=integer(r.get("head"),heads.size()-1);
            int[] fs=indices(r.get("facts"),facts.size()), ps=indices(r.get("parents"),heads.size());
            eligible[i]=true;
            for(int f:fs)if(states[f]!=1)eligible[i]=false;
            remaining[i]=ps.length;
            if(eligible[i]) {
                for(int parent:ps)waiting.get(parent).add(i);
                if(ps.length==0)agenda.add(targets[i]);
            }
        }
        while(!agenda.isEmpty()) {
            int head=agenda.remove();
            if(reached[head])continue;
            reached[head]=true;
            for(int rule:waiting.get(head)) {
                remaining[rule]--;
                if(remaining[rule]==0)agenda.add(targets[rule]);
            }
        }
        List<Object> result=new ArrayList<>();
        for(int i=0;i<reached.length;i++)if(reached[i])result.add((long)i);
        return Json.obj("status","OK","decoded",p,"program_hash",Json.hash(p),"derived",result);
    }
    public static void main(String[] args) throws Exception {
        BufferedReader reader=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));
        String line;
        while((line=reader.readLine())!=null) {
            try { System.out.println(Json.write(evaluate(Json.parse(line)))); }
            catch(IllegalArgumentException error) {
                System.out.println(Json.write(Json.obj("status","REJECTED","reason","INVALID_CONDITIONAL_IR")));
            }
        }
    }
}
