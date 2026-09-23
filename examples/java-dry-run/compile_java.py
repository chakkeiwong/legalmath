"""Deterministic RuleIR subset -> Java source. Reject rather than approximate."""
import json
from pathlib import Path
import sys

from reference import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_spec_pack import semantic_structure, validator  # noqa: E402


def java_string(s):
    # Node/fact/source identifiers are constrained to ASCII by the schema.
    return json.dumps(s, ensure_ascii=True)


def compile_bundle(bundle):
    validator("rule-bundle").validate(bundle)
    semantic_structure(bundle)
    if bundle["spec_version"] != "0.1":
        raise ValueError("E_VERSION")
    rules = {r["id"]: r for r in bundle["rules"]}
    names = {ident:f"r{i}" for i,ident in enumerate(rules)}
    if "spi.streamlining" not in rules:
        raise ValueError("E_ROOT")
    if any(r["type"] != "bool" for r in rules.values()):
        raise ValueError("E_UNSUPPORTED_RESULT_TYPE")
    used_facts = set()
    def dependencies(n):
        if n["op"] == "fact":
            used_facts.add(n["name"])
        if n["op"] == "rule":
            dependencies(rules[n["name"]]["body"])
        for value in n.values():
            if isinstance(value, dict) and "op" in value: dependencies(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "op" in item: dependencies(item)
    dependencies(rules["spi.streamlining"]["scope"])
    dependencies(rules["spi.streamlining"]["body"])
    if used_facts != {f["name"] for f in bundle["facts"]}:
        raise ValueError("E_DEMO_UNUSED_FACT")
    for f in bundle["facts"]:
        if f["type"] not in ("bool", "integer", "money_hkd"):
            raise ValueError("E_UNSUPPORTED_TYPE")

    def expression(n):
        op = n["op"]
        if op == "literal":
            if n["type"] == "bool":
                return "Value.of(" + str(n["value"]).lower() + ")"
            if n["type"] not in ("money_hkd", "integer"):
                raise ValueError("E_UNSUPPORTED_TYPE")
            return "Value.of(new BigInteger(" + java_string(n["value"]) + "))"
        if op == "fact":
            return "c.fact(" + java_string(n["name"]) + ")"
        if op == "rule":
            return names[n["name"]] + "(c)"
        if op in ("all", "any"):
            return op + "(" + ", ".join(expression(a) for a in n["args"]) + ")"
        if op == "not":
            return "not(" + expression(n["arg"]) + ")"
        if op == "compare":
            return "compare(" + java_string(n["cmp"]) + ", " + expression(n["left"]) + ", " + expression(n["right"]) + ")"
        raise ValueError("E_UNSUPPORTED: " + op)

    entries = ",\n        ".join("Map.entry(" + java_string(f["name"]) + ", " + java_string(f["type"]) + ")" for f in bundle["facts"])
    lines = ["// Generated from spi-control.bundle.json; edit the reviewed specification, not this file.",
             "package hk.legalmath.spi;", "import java.math.BigInteger;", "import java.util.*;",
             "import static hk.legalmath.spi.DecisionRuntime.*;", "public final class GeneratedSpi {",
             "    private GeneratedSpi() {}", "    public static final String BUNDLE_HASH = " + java_string(digest(bundle)) + ";",
             "    public static final Map<String,String> INPUT_TYPES = Map.ofEntries(\n        " + entries + ");"]
    for ident,r in rules.items():
        if ident != "spi.streamlining" and not (r["scope"]["op"] == "literal" and r["scope"].get("value") is True):
            raise ValueError("E_SCOPED_REFERENCE")
        sources = ",".join(java_string(s) for s in r["source_span_ids"])
        lines += ["    private static Value " + names[ident] + "(Context c) {",
                  "        return c.rule("+java_string(ident)+", List.of("+sources+"), () ->",
                  "            "+expression(r["body"])+");", "    }"]
    until = bundle["valid_until"]
    outside = "validAt.compareTo("+java_string(bundle["valid_from"])+") < 0"
    if until:
        outside += " || validAt.compareTo("+java_string(until)+") >= 0"
    lines += ["    public static Result evaluate(Snapshot snapshot, String validAt, String knownAt) {",
              "        var c = new Context(snapshot, validAt, knownAt, BUNDLE_HASH, INPUT_TYPES);",
              "        if ("+outside+") throw new IllegalArgumentException(\"E_BUNDLE_INTERVAL\");",
              "        var conflicts = c.conflicts();",
              "        if (!conflicts.isEmpty()) return c.finish(\"CONFLICT\", conflicts);",
              "        var scope = "+expression(rules["spi.streamlining"]["scope"])+";",
              "        if (scope.value()==null) return c.finish(\"UNKNOWN\", scope.blockers());",
              "        if (Boolean.FALSE.equals(scope.value())) return c.finish(\"OUT_OF_SCOPE\", Set.of());",
              "        var result = "+names["spi.streamlining"]+"(c);",
              "        return c.finish(result.status(), result.blockers());", "    }", "}"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    bundle = json.loads((HERE / "spec/spi-control.bundle.json").read_text())
    (HERE / "generated/GeneratedSpi.java").write_text(compile_bundle(bundle))
