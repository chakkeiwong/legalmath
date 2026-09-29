package hk.legalmath;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
public final class Percent_be20389318966a7aa1a1 {
    private Percent_be20389318966a7aa1a1() {}
    public static String evaluate(String request) {
        return ExactPercentageBoundary.evaluate(request, Policy_32827abbc5dc09c0006d::evaluate);
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 0) throw new IllegalArgumentException("No raw-policy parameters accepted");
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) System.out.println(evaluate(line));
    }
}
