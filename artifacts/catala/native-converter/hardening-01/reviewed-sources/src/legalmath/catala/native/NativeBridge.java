package catala.stdlib;

import catala.runtime.*;
import hk.legalmath.Json;
import java.io.IOException;
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Exact codecs and actual scope-output observations for the native profile. */
public final class NativeBridge {
    private NativeBridge() {}
    private static final List<Object> TRACE = new ArrayList<>();
    private static Set<String> scopes = Set.of();
    private static Map<String,Object> task;

    public static void capture(Object owner, String field, Object value) {
        String scope = owner.getClass().getSimpleName();
        if (scopes.contains(scope)) {
            if (TRACE.size() >= 100000) throw new IllegalArgumentException("Trace limit");
            TRACE.add(Json.obj("scope", scope, "field", field, "value", encode(value)));
        }
    }

    private static Object encode(Object v) {
        if (v instanceof CatalaInteger n) return n.asBigInteger().toString();
        if (v instanceof CatalaDecimal n) return Json.obj("numerator", n.getNumerator().toString(), "denominator", n.getDenominator().toString());
        if (v instanceof CatalaMoney n) return n.asBigIntegerCents().toString();
        if (v instanceof CatalaBool b) return b.asBoolean();
        if (v instanceof CatalaDate d) return String.format(Locale.ROOT, "%04d-%02d-%02d", d.date.year, d.date.month, d.date.day);
        if (v instanceof CatalaArray<?> a) {
            List<Object> result = new ArrayList<>();
            for (Object x : a.asArray()) result.add(encode(x));
            return result;
        }
        try {
            if (v instanceof CatalaEnum) return v.getClass().getField("kind").get(v).toString();
            if (v instanceof CatalaStruct) {
                Map<String,Object> result = new TreeMap<>();
                for (Field f : v.getClass().getDeclaredFields()) {
                    if (Modifier.isStatic(f.getModifiers())) continue;
                    f.setAccessible(true);
                    result.put(f.getName(), encode(f.get(v)));
                }
                return result;
            }
        } catch (ReflectiveOperationException e) {
            throw new IllegalArgumentException("Native result codec", e);
        }
        throw new IllegalArgumentException("Unsupported native output type");
    }

    private static Map<String,Object> definition(String name) {
        for (Object d : Json.list(task.get("types"))) {
            Map<String,Object> value = Json.map(d);
            if (name.equals(value.get("name"))) return value;
        }
        throw new IllegalArgumentException("Undeclared type");
    }

    private static CatalaValue<?> decode(String type, Object value) throws ReflectiveOperationException {
        switch (type) {
            case "integer": return new CatalaInteger(Json.str(value));
            case "decimal": {
                Map<String,Object> q = Json.map(value);
                return new CatalaDecimal(new CatalaInteger(Json.str(q.get("numerator"))), new CatalaInteger(Json.str(q.get("denominator"))));
            }
            case "money": return CatalaMoney.ofCents(Json.str(value));
            case "boolean": return ((Boolean)value) ? CatalaBool.TRUE : CatalaBool.FALSE;
            case "date": return CatalaDate.parse("|" + Json.str(value) + "|");
            default: break;
        }
        if (type.startsWith("list[") && type.endsWith("]")) {
            String element = type.substring(5, type.length()-1);
            List<Object> values = Json.list(value);
            if (values.size() > 10000) throw new IllegalArgumentException("List limit");
            CatalaValue<?>[] result = new CatalaValue<?>[values.size()];
            for (int i=0; i<values.size(); i++) result[i] = decode(element, values.get(i));
            return new CatalaArray<>(result);
        }
        Map<String,Object> d = definition(type);
        Class<?> cls = Class.forName("catala.stdlib.Native$" + type);
        if ("enum".equals(d.get("kind"))) {
            String name = Json.str(value);
            if (!Json.list(d.get("cases")).contains(name)) throw new IllegalArgumentException("Enum value");
            return (CatalaValue<?>)cls.getMethod("make" + name).invoke(null);
        }
        return construct(cls, Json.list(d.get("fields")), Json.map(value), false);
    }

    private static CatalaValue<?> construct(Class<?> cls, List<Object> fields, Map<String,Object> values, boolean scope) throws ReflectiveOperationException {
        Map<String,String> types = new TreeMap<>();
        for (Object field : fields) {
            Map<String,Object> f = Json.map(field);
            types.put(Json.str(f.get("name")) + (scope ? "_in" : ""), Json.str(f.get("type")));
        }
        if (values.size() != types.size()) throw new IllegalArgumentException("Unexpected inputs");
        Constructor<?> found = null;
        for (Constructor<?> c : cls.getDeclaredConstructors()) {
            Set<String> names = new TreeSet<>();
            for (Parameter p : c.getParameters()) names.add(p.getName());
            if (names.equals(types.keySet()) && c.getParameterCount()==types.size()) {
                if (found != null) throw new IllegalArgumentException("Ambiguous constructor");
                found = c;
            }
        }
        if (found == null) throw new IllegalArgumentException("Declared interface differs from compiled scope");
        Object[] args = new Object[found.getParameterCount()];
        int i=0;
        for (Parameter p : found.getParameters()) {
            String name = p.getName();
            args[i++] = decode(types.get(name), values.get(scope ? name.substring(0, name.length()-3) : name));
        }
        found.setAccessible(true);
        return (CatalaValue<?>)found.newInstance(args);
    }

    public static void main(String[] args) throws IOException, ReflectiveOperationException {
        try (var stream = NativeBridge.class.getResourceAsStream("/META-INF/legalmath/native-task.json")) {
            if (stream == null) throw new IOException("Missing task commitment");
            task = Json.map(Json.parse(new String(stream.readAllBytes(), StandardCharsets.UTF_8)));
        }
        try (var stream = NativeBridge.class.getResourceAsStream("/META-INF/legalmath/native-scopes.json")) {
            if (stream == null) throw new IOException("Missing scopes");
            Set<String> names = new TreeSet<>();
            for (Object name : Json.list(Json.parse(new String(stream.readAllBytes(), StandardCharsets.UTF_8)))) names.add(Json.str(name));
            scopes = names;
        }
        byte[] bytes = System.in.readNBytes(1000001);
        if (bytes.length > 1000000) throw new IllegalArgumentException("Request limit");
        Map<String,Object> inputs = Json.map(Json.parse(new String(bytes, StandardCharsets.UTF_8)));
        for (Object bound : Json.list(task.getOrDefault("bounds", List.of()))) {
            Map<String,Object> b = Json.map(bound);
            Object raw = inputs.get(Json.str(b.get("input")));
            CatalaDecimal number = raw instanceof Map<?,?>
                ? (CatalaDecimal)decode("decimal", raw) : CatalaDecimal.of(new CatalaInteger(Json.str(raw)));
            if ((b.get("minimum") != null && number.lessThan(CatalaDecimal.of(Json.str(b.get("minimum")))).asBoolean())
                    || (b.get("maximum") != null && number.greaterThan(CatalaDecimal.of(Json.str(b.get("maximum")))).asBoolean())) {
                throw new IllegalArgumentException("Input outside declared domain");
            }
        }
        Object result = construct(Class.forName("catala.stdlib.Native$" + Json.str(task.get("entry_scope"))), Json.list(task.get("inputs")), inputs, true);
        System.out.println(Json.write(Json.obj("value", encode(result), "trace", TRACE)));
    }
}
