package catala.runtime;

import hk.legalmath.Json;
import java.util.*;

/** Compiler-position observations; each tested expression is evaluated once. */
public final class NativeTrace {
    private static final List<Object> EVENTS = new ArrayList<>();
    private NativeTrace() {}
    private static void record(String kind, String file, int sl, int sc, int el, int ec, Object value) {
        if (EVENTS.size() >= 100000) throw new IllegalArgumentException("Decision trace limit");
        EVENTS.add(Json.obj("kind", kind, "file", file, "start_line", sl, "start_column", sc,
            "end_line", el, "end_column", ec, "value", value));
    }
    public static CatalaBool condition(String f, int sl, int sc, int el, int ec, CatalaBool v) {
        record("condition",f,sl,sc,el,ec,v.asBoolean()); return v;
    }
    public static CatalaBool branch(String f, int sl, int sc, int el, int ec, CatalaBool v) {
        record("branch",f,sl,sc,el,ec,v.asBoolean()); return v;
    }
    public static boolean option(String f, int sl, int sc, int el, int ec, boolean absent) {
        record("option",f,sl,sc,el,ec,absent ? "Absent" : "Present"); return absent;
    }
    public static void caseTaken(String f, int sl, int sc, int el, int ec, String selected) {
        record("enum",f,sl,sc,el,ec,selected);
    }
    public static List<Object> events() { return List.copyOf(EVENTS); }
}
