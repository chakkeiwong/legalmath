"""Generated classes contain only a validated, immutable policy and a Java API."""
import base64
from importlib.resources import files

from ..canonical import canonical, digest
from ..errors import LegalMathError
from ..ir.typecheck import validate_bundle


def emit(bundle):
    errors = validate_bundle(bundle)
    if errors:
        raise LegalMathError(errors[0]["code"], errors[0]["pointer"])
    name = "Policy_" + digest(bundle)[:20]
    encoded = base64.b64encode(canonical(bundle)).decode()
    chunks = ",\n".join('"' + encoded[i:i + 12000] + '"' for i in range(0, len(encoded), 12000))
    source = f'''package hk.legalmath;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;

/** Generated RuleIR 0.1 policy. Authority is supplied by an external release record. */
public final class {name} {{
    private {name}() {{}}
    public static final String BUNDLE_HASH = "{digest(bundle)}";
    private static final Policy POLICY = new Policy(new String(Base64.getDecoder().decode(String.join("", new String[]{{
{chunks}
    }})), StandardCharsets.UTF_8));
    public static String evaluate(String snapshot, String ruleId, String validAt, String knownAt, String mode) {{
        return POLICY.evaluate(snapshot, ruleId, validAt, knownAt, mode);
    }}
    public static Map<String,Object> evaluate(Map<String,Object> snapshot, String ruleId, String validAt, String knownAt, String mode) {{
        return POLICY.evaluate(snapshot, ruleId, validAt, knownAt, mode);
    }}
}}
'''
    return name, source


def runtime_sources():
    root = files("legalmath").joinpath("java/runtime")
    return {p.name: p.read_text() for p in sorted(root.iterdir(), key=lambda p: p.name) if p.name.endswith(".java")}
