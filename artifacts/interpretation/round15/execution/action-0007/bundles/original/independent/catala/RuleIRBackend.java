package catala.stdlib;

import java.time.LocalDate;
import java.util.List;
import catala.runtime.CatalaArray;
import catala.runtime.CatalaInteger;
import hk.legalmath.Policy;

/** Generated typed dispatch: missing nodes and unexpected statuses fail closed. */
public final class RuleIRBackend implements Policy.NodeEngine {
    private static CatalaArray<Lowered.Operand> inputs(List<Policy.Scalar> args) {
        var rows = new java.util.ArrayList<Lowered.Operand>();
        for (int i=0; i<args.size(); i++) {
            var a = args.get(i);
            int state = switch(a.status()) {
                case "UNKNOWN" -> 0; case "TRUE" -> 1; case "FALSE" -> 2;
                case "VALUE" -> 3; case "CONFLICT" -> 4; case "ERROR" -> 5;
                default -> throw new IllegalArgumentException("Invalid operand status");
            };
            String value = "0";
            if (state==1 || state==2) value = state==1 ? "1" : "0";
            else if (state==3) value = a.type().equals("date")
                ? Long.toString(LocalDate.parse((String)a.value()).toEpochDay()) : (String)a.value();
            rows.add(new Lowered.Operand(new CatalaInteger(i), new CatalaInteger(state), new CatalaInteger(value)));
        }
        return new CatalaArray<Lowered.Operand>(rows.stream());
    }
    private static Policy.Scalar scalar(String type, CatalaInteger state, CatalaInteger amount) {
        String status = switch(state.asInt()) {
            case 0 -> "UNKNOWN"; case 1 -> "TRUE"; case 2 -> "FALSE";
            case 3 -> "VALUE"; case 4 -> "CONFLICT"; case 5 -> "ERROR";
            default -> throw new IllegalArgumentException("Invalid Catala status");
        };
        Object value = switch(status) {
            case "TRUE" -> true; case "FALSE" -> false;
            case "VALUE" -> type.equals("date") ? LocalDate.ofEpochDay(amount.asLong()).toString() : amount.asBigInteger().toString();
            default -> null;
        };
        return new Policy.Scalar(type, status, value);
    }
    @Override public Policy.Scalar calculate(String node, List<Policy.Scalar> args) {
        var operands = inputs(args);
        switch(node) {
            case "body.1": { var r = new Lowered.N1(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "body.3": { var r = new Lowered.N3(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "body.5": { var r = new Lowered.N5(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "body.7": { var r = new Lowered.N7(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            default: throw new IllegalArgumentException("Missing Catala calculation: " + node);
        }
    }
    @Override public int select(String node, List<Policy.Scalar> args) {
        var operands = inputs(args);
        switch(node) {

            default: throw new IllegalArgumentException("Missing Catala selector: " + node);
        }
    }
}
