"""Offline validation with the retained OASIS LegalRuleML schema."""
from pathlib import Path
RES=Path(__file__).resolve().parents[1]/".localresources/legal-tool-comparison"

def schema(data):
    from lxml import etree
    base=RES/"legalruleml-source"
    class Resolver(etree.Resolver):
        def resolve(self,url,pubid,context):
            if url in ("http://www.w3.org/2009/01/xml.xsd","https://www.w3.org/2009/01/xml.xsd"):
                return self.resolve_filename(str(RES/"xml.xsd"),context)
    parser=etree.XMLParser(no_network=True,resolve_entities=False)
    parser.resolvers.add(Resolver())
    xsd=etree.XMLSchema(etree.parse(str(base/"xsd-schema/compact/lrml-compact.xsd"),parser))
    rows=[]
    for name in ("ex2-references-compact.lrml","ex3-deontic-compact.lrml","ex9-alternatives-compact.lrml"):
        tree=etree.parse(str(base/"examples/compactified"/name),parser)
        valid=xsd.validate(tree)
        rows.append({"example":name,"valid":valid,"errors":[str(e) for e in xsd.error_log]})
    negative=etree.fromstring(b'<lrml:LegalRuleML xmlns:lrml="http://docs.oasis-open.org/legalruleml/ns/v1.0/"><lrml:InventedElement/></lrml:LegalRuleML>',parser)
    rejected=not xsd.validate(negative)
    return {"status":"PASS" if all(r["valid"] for r in rows) and rejected else "FAILED_CONTROLS",
        "decision":"ADAPT_INTERCHANGE_VALIDATION","examples":rows,"invalid_control_rejected":rejected,
        "invalid_control_errors":[str(e) for e in xsd.error_log],
        "scope":"Official compact schema and reference/deontic/alternative examples. No product roundtrip or source-to-rule equivalence established."}
