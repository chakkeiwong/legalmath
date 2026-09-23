package hk.legalmath.spi;

import java.util.*;

/** Replay one complete client/category consent stream with authoritative sequence. */
public final class ConsentReplay {
    private ConsentReplay() {}
    public record Event(String id, String kind, String occurredAt, String recordedAt, long sequence) {
        public Event {
            if(!Set.of("GRANTED","WITHDRAWN").contains(kind))throw new IllegalArgumentException("E_EVENT_KIND");
            DecisionRuntime.timestamp(occurredAt);DecisionRuntime.timestamp(recordedAt);
            DecisionRuntime.identifier(id);
        }
    }
    public static String replay(List<Event> events, String validAt, String knownAt,
                                String completeThrough, String completenessRecordedAt) {
        DecisionRuntime.timestamp(validAt);DecisionRuntime.timestamp(knownAt);
        DecisionRuntime.timestamp(completeThrough);DecisionRuntime.timestamp(completenessRecordedAt);
        var unique=new HashMap<String,Event>();
        for(var e:events) if(e.recordedAt().compareTo(knownAt)<=0) {
            var old=unique.putIfAbsent(e.id(),e);
            if(old!=null&&!old.equals(e))return "CONFLICT";
        }
        if(completeThrough.compareTo(validAt)<0||completenessRecordedAt.compareTo(knownAt)>0
                ||completeThrough.compareTo(completenessRecordedAt)>0)return "UNKNOWN";
        var selected=unique.values().stream().filter(e->e.occurredAt().compareTo(validAt)<=0)
            .sorted(Comparator.comparing(Event::occurredAt).thenComparingLong(Event::sequence)).toList();
        for(int i=1;i<selected.size();i++)if(selected.get(i).occurredAt().equals(selected.get(i-1).occurredAt())&&selected.get(i).sequence()==selected.get(i-1).sequence())return "UNKNOWN";
        return !selected.isEmpty()&&selected.get(selected.size()-1).kind().equals("GRANTED")?"TRUE":"FALSE";
    }
}
