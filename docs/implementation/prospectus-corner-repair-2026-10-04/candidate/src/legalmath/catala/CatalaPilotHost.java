import catala.runtime.CatalaBool;
import catala.runtime.CatalaInteger;
import catala.runtime.CatalaStruct;
import catala.stdlib.Pilots;
import hk.legalmath.Json;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.reflect.Constructor;
import java.lang.reflect.Parameter;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/** Typed calculation boundary. Raw fact/time/provenance validation is external. */
public final class CatalaPilotHost {
    private CatalaPilotHost() {}

    public static String evaluate(String requestText) throws ReflectiveOperationException {
        Map<String, Object> request = Json.map(Json.parse(requestText));
        if (!request.keySet().equals(Set.of("scope", "inputs"))) {
            throw new IllegalArgumentException("scope and inputs required");
        }
        String scope = Json.str(request.get("scope"));
        Class<? extends CatalaStruct> type = switch (scope) {
            case "Financial" -> Pilots.Financial.class;
            case "Exceptions" -> Pilots.Exceptions.class;
            default -> throw new IllegalArgumentException("Unsupported Catala scope");
        };
        Map<String, Object> input = Json.map(request.get("inputs"));
        Constructor<?> constructor = scope.equals("Financial")
            ? type.getDeclaredConstructor(CatalaBool.class, CatalaInteger.class, CatalaBool.class, CatalaInteger.class)
            : type.getDeclaredConstructor(CatalaBool.class, CatalaBool.class, CatalaBool.class, CatalaBool.class);
        constructor.setAccessible(true);
        Parameter[] parameters = constructor.getParameters();
        Object[] values = new Object[parameters.length];
        Set<String> consumed = new HashSet<>();
        for (int i = 0; i < parameters.length; i++) {
            Parameter parameter = parameters[i];
            if (!parameter.isNamePresent()) throw new IllegalStateException("Compile with -parameters");
            String name = parameter.getName().replaceFirst("_in$", "");
            if (!input.containsKey(name) || !consumed.add(name)) {
                throw new IllegalArgumentException("Missing or duplicate Catala input: " + name);
            }
            Object value = input.get(name);
            if (parameter.getType() == CatalaBool.class && value instanceof Boolean bool) {
                values[i] = CatalaBool.of(bool);
            } else if (parameter.getType() == CatalaInteger.class && value instanceof String integer
                       && integer.matches("0|-?[1-9][0-9]*")) {
                values[i] = new CatalaInteger(integer);
            } else {
                throw new IllegalArgumentException("Invalid Catala input: " + name);
            }
        }
        if (!input.keySet().equals(consumed)) throw new IllegalArgumentException("Unexpected inputs");
        CatalaStruct result = (CatalaStruct) constructor.newInstance(values);
        return Json.write(Json.parse(result.toJSONString()));
    }

    public static void main(String[] args) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) System.out.println(evaluate(line));
    }
}
