package hk.legalmath;

import java.math.BigInteger;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

/** In-process synthetic transaction protocol; this is not a bank connector. */
public final class SyntheticHost {
    private BigInteger exposure;
    private boolean consent=true;
    private long exposureVersion=1,consentVersion=1,releaseVersion=1;
    private String release;
    private Function<String,String> evaluator;
    private final String template;
    private final Map<String,Map<String,Object>> orders=new HashMap<>();
    private final Map<String,String> payloads=new HashMap<>();
    public SyntheticHost(String snapshot,BigInteger initialExposure,String releasedHash,Function<String,String> evaluate){
        template=Json.write(Json.parse(snapshot));exposure=initialExposure;release=releasedHash;evaluator=evaluate;
    }
    public synchronized void setConsent(boolean active){consent=active;consentVersion++;}
    public synchronized void replaceRelease(String hash,Function<String,String> evaluate){release=hash;evaluator=evaluate;releaseVersion++;}
    public synchronized String exposure(){return exposure.toString();}
    public synchronized int committedOrders(){return orders.size();}
    private record Read(BigInteger exposure,boolean consent,long ev,long cv,long rv,String release,Function<String,String> evaluator) {}
    public Map<String,Object> order(String id,String cents,int maxRetries,Runnable afterFirstRead){
        BigInteger amount=new BigInteger(cents);
        if(!cents.matches("0|[1-9][0-9]*")||maxRetries<1)throw new IllegalArgumentException("Invalid order");
        String payload=Json.hash(Json.obj("id",id,"amount_cents",cents));
        for(int attempt=0;attempt<maxRetries;attempt++){
            Read read;
            synchronized(this){
                if(payloads.containsKey(id)){
                    if(!payloads.get(id).equals(payload))return Json.map(Json.freeze(Json.obj("status","IDEMPOTENCY_CONFLICT")));
                    return orders.get(id);
                }
                read=new Read(exposure,consent,exposureVersion,consentVersion,releaseVersion,release,evaluator);
            }
            if(attempt==0&&afterFirstRead!=null)afterFirstRead.run();
            Map<String,Object> snapshot=Json.map(Json.parse(template)),facts=Json.map(snapshot.get("facts"));
            set(facts,"projected_gross_exposure",read.exposure().add(amount).toString());
            set(facts,"active_consent",read.consent());
            Map<String,Object> decision=Json.map(Json.parse(read.evaluator().apply(Json.write(snapshot))));
            synchronized(this){
                if(exposureVersion!=read.ev()||consentVersion!=read.cv()||releaseVersion!=read.rv())continue;
                if(payloads.containsKey(id)){
                    if(!payloads.get(id).equals(payload))return Json.map(Json.freeze(Json.obj("status","IDEMPOTENCY_CONFLICT")));
                    return orders.get(id);
                }
                boolean accept="TRUE".equals(decision.get("status"));
                Map<String,Object> result=Json.map(Json.freeze(Json.obj("status",accept?"RESERVED":"DO_NOT_STREAMLINE","decision",decision,
                    "release_hash",read.release(),"consent_version",read.cv(),"exposure_version",read.ev(),"order_id",id,"amount_cents",cents)));
                // Reservation and its evidence become visible at this one commit point.
                if(accept){exposure=exposure.add(amount);exposureVersion++;}
                payloads.put(id,payload);orders.put(id,result);return result;
            }
        }
        return Json.map(Json.freeze(Json.obj("status","RETRY_EXHAUSTED")));
    }
    private static void set(Map<String,Object> facts,String name,Object value){
        Map<String,Object> old=Json.map(facts.get(name));
        if(!"known".equals(old.get("status")))throw new IllegalArgumentException("Synthetic host requires declared known host facts");
        old.put("value",value);
    }
}
