package hk.legalmath;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/** NDJSON conformance caller. Real hosts use their generated policy class. */
public final class Runner {
    private Runner() {}
    public static void main(String[] args) throws Exception {
        BufferedReader reader=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));
        String line;
        while((line=reader.readLine())!=null){
            Map<String,Object> request=Json.map(Json.parse(line));
            if(request.containsKey("event_request")){
                System.out.println(Json.write(EventReplay.replay(Json.map(request.get("event_request")))));
                continue;
            }
            String snapshot=Json.write(request.get("snapshot")), rule=Json.str(request.get("rule_id"));
            String at=Json.str(request.get("valid_at")), cutoff=Json.str(request.get("known_at"));
            String mode=request.containsKey("mode")?Json.str(request.get("mode")):"draft";
            if(args.length==1){
                if(!args[0].matches("hk\\.legalmath\\.Policy_[0-9a-f]{20}"))throw new IllegalArgumentException("Generated policy class required");
                System.out.println(Class.forName(args[0]).getMethod("evaluate",String.class,String.class,String.class,String.class,String.class).invoke(null,snapshot,rule,at,cutoff,mode));
            }else{
                Policy p=new Policy(Json.write(request.get("bundle")));
                System.out.println(p.evaluate(snapshot,rule,at,cutoff,mode));
            }
        }
    }
}
