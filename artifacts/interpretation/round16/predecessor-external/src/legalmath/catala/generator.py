"""Deterministic RuleIR 0.1 expression lowering; no evaluation oracle or profiles.

Fact admissibility, rule traversal and provenance belong to the shared Java host.
Catala calculates literals/operators and selects lazy branches. All scalar payloads
use exact integers (dates are days since 1970-01-01, money is HKD minor units).
"""
from datetime import date
import json

from ..canonical import digest
from ..errors import LegalMathError
from ..ir.graph import children, walk
from ..ir.typecheck import validate_bundle

ENGINE = "legalmath-catala-java/0.2.0"
CALCULATIONS = {"literal", "all", "any", "not", "compare", "add", "sub", "scale"}
SELECTORS = {"if", "default"}
STATUSES = {"UNKNOWN": 0, "TRUE": 1, "FALSE": 2, "VALUE": 3, "CONFLICT": 4, "ERROR": 5}


def _integer(value):
    return f"({value})" if str(value).startswith("-") else str(value)


def _exists(code):
    return f"(exists x among operands such that x.code = {code})"


def _scope(name, node):
    op = node["op"]
    internal = {}
    selected, value = "(-1)", "0"
    if op == "literal":
        typ, raw = node["type"], node["value"]
        state = "1" if typ == "bool" and raw else "2" if typ == "bool" else "3"
        if typ == "bool":
            raw = int(raw)
        elif typ == "date":
            raw = (date.fromisoformat(raw) - date(1970, 1, 1)).days
        value = _integer(raw)
    elif op in SELECTORS:
        state = "0"  # selection has no value; the host visits only the chosen branch
        if op == "if":
            selected = f"if {_exists(1)} then 1 else if {_exists(2)} then 2 else (-1)"
        else:
            internal["trueCount"] = "sum integer of (map each x among operands to (if x.code = 1 then 1 else 0))"
            internal["trueSlot"] = "sum integer of (map each x among operands to (if x.code = 1 then x.slot + 1 else 0))"
            selected = f"if {_exists(5)} or {_exists(4)} then (-1) else if trueCount > 1 then (-2) else if {_exists(0)} then (-1) else trueSlot"
    else:
        if op in ("all", "any"):
            decisive, neutral = (2, 1) if op == "all" else (1, 2)
            state = f"if {_exists(decisive)} then {decisive} else if {_exists(0)} then 0 else {neutral}"
        elif op == "not":
            state = f"if {_exists(0)} then 0 else if {_exists(1)} then 2 else 1"
        else:
            internal["leftValue"] = "sum integer of (map each x among operands to (if x.slot = 0 then x.payload else 0))"
            if op != "scale":
                internal["rightValue"] = "sum integer of (map each x among operands to (if x.slot = 1 then x.payload else 0))"
            if op == "compare":
                cmp = {"eq": "=", "ge": ">=", "gt": ">"}[node["cmp"]]
                state = f"if {_exists(0)} then 0 else if leftValue {cmp} rightValue then 1 else 2"
            elif op in ("add", "sub"):
                value = f"leftValue {'+' if op == 'add' else '-'} rightValue"
                state = f"if {_exists(0)} then 0 else 3"
            elif op == "scale":
                num, den = _integer(node["numerator"]), _integer(node["denominator"])
                internal["quotient"] = f"integer of ((leftValue * {num}) / {den})"
                value = "quotient"
                state = f"if {_exists(0)} then 0 else if quotient * {den} = leftValue * {num} then 3 else 5"
            else:
                raise LegalMathError("E_UNSUPPORTED_PROFILE", details=op)
        state = f"if {_exists(5)} then 5 else if {_exists(4)} then 4 else ({state})"
        if op in ("all", "any", "not", "compare"):
            value = "if resultStatus = 1 then 1 else 0"
    lines = [f"declaration scope {name}:", "  input operands content list of Operand",
             "  output resultStatus content integer", "  output resultValue content integer",
             "  output selected content integer"]
    lines += [f"  internal {key} content integer" for key in internal]
    lines += [f"scope {name}:"]
    lines += [f"  definition {key} equals {expression}" for key, expression in internal.items()]
    lines += [f"  definition resultStatus equals {state}", f"  definition resultValue equals {value}",
              f"  definition selected equals {selected}"]
    return "\n".join(lines)


def generate(bundle):
    """Return Catala source, typed Java dispatch, and its source map."""
    errors = validate_bundle(bundle)
    if errors:
        raise LegalMathError(errors[0]["code"], errors[0]["pointer"])
    fact_types = {f["name"]: f["type"] for f in bundle["facts"]}
    rule_types = {r["id"]: r["type"] for r in bundle["rules"]}
    types = {}

    def infer(n):
        parts = [infer(c) for _, c in children(n)]
        op = n["op"]
        typ = (n["type"] if op == "literal" else fact_types[n["name"]] if op == "fact"
               else rule_types[n["name"]] if op == "rule" else "bool" if op in ("all", "any", "not", "compare")
               else parts[1] if op == "if" else parts[0])
        types[n["node_id"]] = typ
        return typ

    for r in bundle["rules"]:
        for field in ("scope", "body"):
            infer(r[field])
    lines = ["# Generated RuleIR calculations", "", f"Bundle SHA-256: {digest(bundle)}.", "",
             "Statuses: UNKNOWN=0, TRUE=1, FALSE=2, VALUE=3, CONFLICT=4, ERROR=5.",
             "Selectors: -1 unresolved, -2 multiple exceptions; otherwise branch index.", "",
             "```catala", "declaration structure Operand:", "  data slot content integer",
             "  data code content integer", "  data payload content integer", ""]
    mappings, calculations, selectors = [], [], []
    for ri, rule in enumerate(bundle["rules"]):
        for field in ("scope", "body"):
            for n, pointer in walk(rule[field], f"/bundle/rules/{ri}/{field}"):
                op = n["op"]
                entry = {"node_id": n["node_id"], "op": op, "type": types[n["node_id"]],
                         "pointer": pointer, "rule_id": rule["id"], "source_span_ids": sorted(rule["source_span_ids"])}
                if op in CALCULATIONS | SELECTORS:
                    name = f"N{len(mappings)}"
                    block = _scope(name, n).splitlines()
                    entry.update(scope=name, line_start=len(lines) + 1, line_end=len(lines) + len(block), layer="catala")
                    lines.extend(block + [""])
                    ident = json.dumps(n["node_id"])
                    if op in CALCULATIONS:
                        calculations.append(f'            case {ident}: {{ var r = new Lowered.{name}(operands); return scalar("{types[n["node_id"]]}", r.resultStatus, r.resultValue); }}')
                    else:
                        selectors.append(f'            case {ident}: return new Lowered.{name}(operands).selected.asInt();')
                elif op in ("fact", "rule"):
                    entry["layer"] = "shared-java"
                else:
                    raise LegalMathError("E_UNSUPPORTED_PROFILE", details=op)
                mappings.append(entry)
    lines += ["```", ""]
    bridge = '''package catala.stdlib;

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
CALCULATIONS
            default: throw new IllegalArgumentException("Missing Catala calculation: " + node);
        }
    }
    @Override public int select(String node, List<Policy.Scalar> args) {
        var operands = inputs(args);
        switch(node) {
SELECTORS
            default: throw new IllegalArgumentException("Missing Catala selector: " + node);
        }
    }
}
'''.replace("CALCULATIONS", "\n".join(calculations)).replace("SELECTORS", "\n".join(selectors))
    return {"source": "\n".join(lines), "bridge": bridge,
            "source_map": {"bundle_hash": digest(bundle), "engine": ENGINE, "nodes": mappings,
                           "shared_host": ["input-validation", "fact-admissibility", "static-conflict-check", "rule-traversal", "provenance", "result-hashing"]}}
