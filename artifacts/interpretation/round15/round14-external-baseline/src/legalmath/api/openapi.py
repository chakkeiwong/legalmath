"""Embed the same domain contracts used by runtime validation in OpenAPI 3.1."""
from copy import deepcopy
from importlib.resources import files
import json


def install_contracts(app):
    original = app.openapi

    def contract_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        spec = original()
        schemas = spec["components"]["schemas"]
        for path in sorted(files("legalmath").joinpath("schemas").iterdir(), key=lambda p: p.name):
            if not path.name.endswith(".schema.json"):
                continue
            name = path.name.removesuffix(".schema.json")
            raw = json.loads(path.read_text())
            definitions = raw.pop("$defs", {})
            raw.pop("$id", None)
            raw.pop("$schema", None)

            def rewrite(value):
                if isinstance(value, list): return [rewrite(x) for x in value]
                if not isinstance(value, dict): return value
                return {k: "#/components/schemas/" + name + "." + v[8:] if k == "$ref" and v.startswith("#/$defs/") else rewrite(v) for k, v in value.items()}

            schemas[name] = rewrite(raw)
            for key, definition in definitions.items():
                schemas[name + "." + key] = rewrite(definition)

        def ref(name): return {"$ref": "#/components/schemas/" + name}

        for path, name in {"/v1/bundles": "rule-bundle", "/v1/applicability": "applicability", "/v1/fact-records": "fact-record", "/v1/event-streams": "stream-header"}.items():
            spec["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"] = ref(name)
        schemas["Evaluation"]["properties"]["snapshot"] = ref("fact-snapshot")
        schemas["EventAppend"]["properties"]["event"] = ref("event")
        schemas["Replay"]["properties"]["completeness"] = {"anyOf": [ref("completeness"), {"type": "null"}]}
        spec["paths"]["/v1/evaluations"]["post"]["responses"]["200"]["content"]["application/json"]["schema"] = ref("evaluation")
        schemas["ServiceError"] = {"type": "object", "required": ["error", "diagnostics"], "additionalProperties": False,
            "properties": {"error": {"type": "string"}, "diagnostics": deepcopy(schemas["boundary-error"]["properties"]["diagnostics"])}}
        for operations in spec["paths"].values():
            for operation in operations.values():
                if not isinstance(operation, dict) or "responses" not in operation: continue
                for status, description in {"403": "Caller lacks the required role", "404": "Record not found", "409": "Revision, idempotency or release conflict", "413": "Resource budget exceeded", "422": "Invalid request or domain record"}.items():
                    operation["responses"][status] = {"description": description, "content": {"application/json": {"schema": ref("ServiceError")}}}
        app.openapi_schema = spec
        return spec

    app.openapi = contract_openapi
