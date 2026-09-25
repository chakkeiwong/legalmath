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
            case "node.9": { var r = new Lowered.N0(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.4": { var r = new Lowered.N2(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.5": { var r = new Lowered.N4(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.6": { var r = new Lowered.N6(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.7": { var r = new Lowered.N8(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.15": { var r = new Lowered.N9(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.11": { var r = new Lowered.N12(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.13": { var r = new Lowered.N13(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.12": { var r = new Lowered.N14(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.21": { var r = new Lowered.N15(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.19": { var r = new Lowered.N17(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.18": { var r = new Lowered.N19(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.17": { var r = new Lowered.N20(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.33": { var r = new Lowered.N21(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.28": { var r = new Lowered.N23(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.22": { var r = new Lowered.N24(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.29": { var r = new Lowered.N25(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.23": { var r = new Lowered.N26(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.30": { var r = new Lowered.N27(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.27": { var r = new Lowered.N28(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.25": { var r = new Lowered.N29(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.24": { var r = new Lowered.N30(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.26": { var r = new Lowered.N31(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.31": { var r = new Lowered.N32(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.45": { var r = new Lowered.N33(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.41": { var r = new Lowered.N35(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.36": { var r = new Lowered.N37(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.34": { var r = new Lowered.N38(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.37": { var r = new Lowered.N39(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.35": { var r = new Lowered.N40(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.38": { var r = new Lowered.N41(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.42": { var r = new Lowered.N42(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.43": { var r = new Lowered.N44(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.50": { var r = new Lowered.N45(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.49": { var r = new Lowered.N46(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.55": { var r = new Lowered.N50(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.54": { var r = new Lowered.N51(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.62": { var r = new Lowered.N55(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.61": { var r = new Lowered.N56(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.56": { var r = new Lowered.N57(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.60": { var r = new Lowered.N58(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.58": { var r = new Lowered.N59(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.57": { var r = new Lowered.N60(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.59": { var r = new Lowered.N61(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.71": { var r = new Lowered.N62(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.70": { var r = new Lowered.N63(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.63": { var r = new Lowered.N64(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.66": { var r = new Lowered.N66(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.64": { var r = new Lowered.N67(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.67": { var r = new Lowered.N68(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.65": { var r = new Lowered.N69(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.68": { var r = new Lowered.N70(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.75": { var r = new Lowered.N71(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.74": { var r = new Lowered.N72(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.350": { var r = new Lowered.N75(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.77": { var r = new Lowered.N76(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.76": { var r = new Lowered.N77(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.351": { var r = new Lowered.N78(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.80": { var r = new Lowered.N79(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.78": { var r = new Lowered.N80(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.79": { var r = new Lowered.N81(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.352": { var r = new Lowered.N82(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.81": { var r = new Lowered.N83(operands); return scalar("date", r.resultStatus, r.resultValue); }
            case "node.353": { var r = new Lowered.N84(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.82": { var r = new Lowered.N85(operands); return scalar("date", r.resultStatus, r.resultValue); }
            case "node.354": { var r = new Lowered.N86(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.85": { var r = new Lowered.N87(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.83": { var r = new Lowered.N88(operands); return scalar("date", r.resultStatus, r.resultValue); }
            case "node.84": { var r = new Lowered.N89(operands); return scalar("date", r.resultStatus, r.resultValue); }
            case "node.355": { var r = new Lowered.N90(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.86": { var r = new Lowered.N92(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.356": { var r = new Lowered.N93(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.218": { var r = new Lowered.N95(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.88": { var r = new Lowered.N96(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.219": { var r = new Lowered.N97(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.89": { var r = new Lowered.N98(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.220": { var r = new Lowered.N99(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.90": { var r = new Lowered.N100(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.221": { var r = new Lowered.N101(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.91": { var r = new Lowered.N102(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.222": { var r = new Lowered.N103(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.92": { var r = new Lowered.N104(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.223": { var r = new Lowered.N105(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.93": { var r = new Lowered.N106(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.224": { var r = new Lowered.N107(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.94": { var r = new Lowered.N108(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.225": { var r = new Lowered.N109(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.95": { var r = new Lowered.N110(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.226": { var r = new Lowered.N111(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.96": { var r = new Lowered.N112(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.227": { var r = new Lowered.N113(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.97": { var r = new Lowered.N114(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.228": { var r = new Lowered.N115(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.98": { var r = new Lowered.N116(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.229": { var r = new Lowered.N117(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.99": { var r = new Lowered.N118(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.230": { var r = new Lowered.N119(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.100": { var r = new Lowered.N120(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.231": { var r = new Lowered.N121(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.101": { var r = new Lowered.N122(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.232": { var r = new Lowered.N123(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.102": { var r = new Lowered.N124(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.233": { var r = new Lowered.N125(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.103": { var r = new Lowered.N126(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.234": { var r = new Lowered.N127(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.104": { var r = new Lowered.N128(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.235": { var r = new Lowered.N129(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.105": { var r = new Lowered.N130(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.236": { var r = new Lowered.N131(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.106": { var r = new Lowered.N132(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.237": { var r = new Lowered.N133(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.107": { var r = new Lowered.N134(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.238": { var r = new Lowered.N135(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.108": { var r = new Lowered.N136(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.239": { var r = new Lowered.N137(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.109": { var r = new Lowered.N138(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.240": { var r = new Lowered.N139(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.110": { var r = new Lowered.N140(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.241": { var r = new Lowered.N141(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.111": { var r = new Lowered.N142(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.242": { var r = new Lowered.N143(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.112": { var r = new Lowered.N144(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.243": { var r = new Lowered.N145(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.113": { var r = new Lowered.N146(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.244": { var r = new Lowered.N147(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.114": { var r = new Lowered.N148(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.245": { var r = new Lowered.N149(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.115": { var r = new Lowered.N150(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.246": { var r = new Lowered.N151(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.116": { var r = new Lowered.N152(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.247": { var r = new Lowered.N153(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.117": { var r = new Lowered.N154(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.248": { var r = new Lowered.N155(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.118": { var r = new Lowered.N156(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.249": { var r = new Lowered.N157(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.119": { var r = new Lowered.N158(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.250": { var r = new Lowered.N159(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.120": { var r = new Lowered.N160(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.251": { var r = new Lowered.N161(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.121": { var r = new Lowered.N162(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.252": { var r = new Lowered.N163(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.122": { var r = new Lowered.N164(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.253": { var r = new Lowered.N165(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.123": { var r = new Lowered.N166(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.254": { var r = new Lowered.N167(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.124": { var r = new Lowered.N168(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.255": { var r = new Lowered.N169(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.125": { var r = new Lowered.N170(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.256": { var r = new Lowered.N171(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.126": { var r = new Lowered.N172(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.257": { var r = new Lowered.N173(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.127": { var r = new Lowered.N174(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.258": { var r = new Lowered.N175(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.128": { var r = new Lowered.N176(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.259": { var r = new Lowered.N177(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.129": { var r = new Lowered.N178(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.260": { var r = new Lowered.N179(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.130": { var r = new Lowered.N180(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.261": { var r = new Lowered.N181(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.131": { var r = new Lowered.N182(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.262": { var r = new Lowered.N183(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.132": { var r = new Lowered.N184(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.263": { var r = new Lowered.N185(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.133": { var r = new Lowered.N186(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.264": { var r = new Lowered.N187(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.134": { var r = new Lowered.N188(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.265": { var r = new Lowered.N189(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.135": { var r = new Lowered.N190(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.266": { var r = new Lowered.N191(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.136": { var r = new Lowered.N192(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.267": { var r = new Lowered.N193(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.137": { var r = new Lowered.N194(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.268": { var r = new Lowered.N195(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.138": { var r = new Lowered.N196(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.269": { var r = new Lowered.N197(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.139": { var r = new Lowered.N198(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.270": { var r = new Lowered.N199(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.140": { var r = new Lowered.N200(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.271": { var r = new Lowered.N201(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.141": { var r = new Lowered.N202(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.272": { var r = new Lowered.N203(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.142": { var r = new Lowered.N204(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.273": { var r = new Lowered.N205(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.143": { var r = new Lowered.N206(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.274": { var r = new Lowered.N207(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.144": { var r = new Lowered.N208(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.275": { var r = new Lowered.N209(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.145": { var r = new Lowered.N210(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.276": { var r = new Lowered.N211(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.146": { var r = new Lowered.N212(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.277": { var r = new Lowered.N213(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.147": { var r = new Lowered.N214(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.278": { var r = new Lowered.N215(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.148": { var r = new Lowered.N216(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.279": { var r = new Lowered.N217(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.149": { var r = new Lowered.N218(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.280": { var r = new Lowered.N219(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.150": { var r = new Lowered.N220(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.281": { var r = new Lowered.N221(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.151": { var r = new Lowered.N222(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.282": { var r = new Lowered.N223(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.152": { var r = new Lowered.N224(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.283": { var r = new Lowered.N225(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.153": { var r = new Lowered.N226(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.284": { var r = new Lowered.N227(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.154": { var r = new Lowered.N228(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.285": { var r = new Lowered.N229(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.155": { var r = new Lowered.N230(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.286": { var r = new Lowered.N231(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.156": { var r = new Lowered.N232(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.287": { var r = new Lowered.N233(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.157": { var r = new Lowered.N234(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.288": { var r = new Lowered.N235(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.158": { var r = new Lowered.N236(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.289": { var r = new Lowered.N237(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.159": { var r = new Lowered.N238(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.290": { var r = new Lowered.N239(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.160": { var r = new Lowered.N240(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.291": { var r = new Lowered.N241(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.161": { var r = new Lowered.N242(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.292": { var r = new Lowered.N243(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.162": { var r = new Lowered.N244(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.293": { var r = new Lowered.N245(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.163": { var r = new Lowered.N246(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.294": { var r = new Lowered.N247(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.164": { var r = new Lowered.N248(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.295": { var r = new Lowered.N249(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.165": { var r = new Lowered.N250(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.296": { var r = new Lowered.N251(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.166": { var r = new Lowered.N252(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.297": { var r = new Lowered.N253(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.167": { var r = new Lowered.N254(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.298": { var r = new Lowered.N255(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.168": { var r = new Lowered.N256(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.299": { var r = new Lowered.N257(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.169": { var r = new Lowered.N258(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.300": { var r = new Lowered.N259(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.170": { var r = new Lowered.N260(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.301": { var r = new Lowered.N261(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.171": { var r = new Lowered.N262(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.302": { var r = new Lowered.N263(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.172": { var r = new Lowered.N264(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.303": { var r = new Lowered.N265(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.173": { var r = new Lowered.N266(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.304": { var r = new Lowered.N267(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.174": { var r = new Lowered.N268(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.305": { var r = new Lowered.N269(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.175": { var r = new Lowered.N270(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.306": { var r = new Lowered.N271(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.176": { var r = new Lowered.N272(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.307": { var r = new Lowered.N273(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.177": { var r = new Lowered.N274(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.308": { var r = new Lowered.N275(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.178": { var r = new Lowered.N276(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.309": { var r = new Lowered.N277(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.179": { var r = new Lowered.N278(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.310": { var r = new Lowered.N279(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.180": { var r = new Lowered.N280(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.311": { var r = new Lowered.N281(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.181": { var r = new Lowered.N282(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.312": { var r = new Lowered.N283(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.182": { var r = new Lowered.N284(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.313": { var r = new Lowered.N285(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.183": { var r = new Lowered.N286(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.314": { var r = new Lowered.N287(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.184": { var r = new Lowered.N288(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.315": { var r = new Lowered.N289(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.185": { var r = new Lowered.N290(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.316": { var r = new Lowered.N291(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.186": { var r = new Lowered.N292(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.317": { var r = new Lowered.N293(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.187": { var r = new Lowered.N294(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.318": { var r = new Lowered.N295(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.188": { var r = new Lowered.N296(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.319": { var r = new Lowered.N297(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.189": { var r = new Lowered.N298(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.320": { var r = new Lowered.N299(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.190": { var r = new Lowered.N300(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.321": { var r = new Lowered.N301(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.191": { var r = new Lowered.N302(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.322": { var r = new Lowered.N303(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.192": { var r = new Lowered.N304(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.323": { var r = new Lowered.N305(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.193": { var r = new Lowered.N306(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.324": { var r = new Lowered.N307(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.194": { var r = new Lowered.N308(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.325": { var r = new Lowered.N309(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.195": { var r = new Lowered.N310(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.326": { var r = new Lowered.N311(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.196": { var r = new Lowered.N312(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.327": { var r = new Lowered.N313(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.197": { var r = new Lowered.N314(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.328": { var r = new Lowered.N315(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.198": { var r = new Lowered.N316(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.329": { var r = new Lowered.N317(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.199": { var r = new Lowered.N318(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.330": { var r = new Lowered.N319(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.200": { var r = new Lowered.N320(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.331": { var r = new Lowered.N321(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.201": { var r = new Lowered.N322(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.332": { var r = new Lowered.N323(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.202": { var r = new Lowered.N324(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.333": { var r = new Lowered.N325(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.203": { var r = new Lowered.N326(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.334": { var r = new Lowered.N327(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.204": { var r = new Lowered.N328(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.335": { var r = new Lowered.N329(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.205": { var r = new Lowered.N330(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.336": { var r = new Lowered.N331(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.206": { var r = new Lowered.N332(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.337": { var r = new Lowered.N333(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.207": { var r = new Lowered.N334(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.338": { var r = new Lowered.N335(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.208": { var r = new Lowered.N336(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.339": { var r = new Lowered.N337(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.209": { var r = new Lowered.N338(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.340": { var r = new Lowered.N339(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.210": { var r = new Lowered.N340(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.341": { var r = new Lowered.N341(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.211": { var r = new Lowered.N342(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.342": { var r = new Lowered.N343(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.212": { var r = new Lowered.N344(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.343": { var r = new Lowered.N345(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.213": { var r = new Lowered.N346(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.344": { var r = new Lowered.N347(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.214": { var r = new Lowered.N348(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.345": { var r = new Lowered.N349(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.215": { var r = new Lowered.N350(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.346": { var r = new Lowered.N351(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.216": { var r = new Lowered.N352(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.347": { var r = new Lowered.N353(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            case "node.217": { var r = new Lowered.N354(operands); return scalar("bool", r.resultStatus, r.resultValue); }
            case "node.348": { var r = new Lowered.N355(operands); return scalar("integer", r.resultStatus, r.resultValue); }
            default: throw new IllegalArgumentException("Missing Catala calculation: " + node);
        }
    }
    @Override public int select(String node, List<Policy.Scalar> args) {
        var operands = inputs(args);
        switch(node) {
            case "node.8": return new Lowered.N1(operands).selected.asInt();
            case "node.14": return new Lowered.N10(operands).selected.asInt();
            case "node.20": return new Lowered.N16(operands).selected.asInt();
            case "node.32": return new Lowered.N22(operands).selected.asInt();
            case "node.44": return new Lowered.N34(operands).selected.asInt();
            case "node.39": return new Lowered.N36(operands).selected.asInt();
            case "node.69": return new Lowered.N65(operands).selected.asInt();
            case "node.87": return new Lowered.N91(operands).selected.asInt();
            case "node.349": return new Lowered.N94(operands).selected.asInt();
            default: throw new IllegalArgumentException("Missing Catala selector: " + node);
        }
    }
}
