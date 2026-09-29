"""Necessary structural checks before sending strict output schemas.

Based on the official Structured Outputs guide (checked 2026-09-28). This is
an early rejection check, not a guarantee of provider acceptance or legal truth.
"""
from ...errors import LegalMathError


def validate_output_schema(schema):
    errors=[]
    if not isinstance(schema,dict) or schema.get('type')!='object' or 'anyOf' in schema:
        raise LegalMathError('E_SCHEMA',details='Output schema root must be an object')
    def visit(node,path):
        if not isinstance(node,dict):return
        forbidden={'allOf','not','dependentRequired','dependentSchemas','if','then','else'}&set(node)
        if forbidden:errors.append({'path':path,'unsupported_keywords':sorted(forbidden)})
        if node.get('type')=='object' or 'properties' in node:
            props=node.get('properties',{});required=node.get('required',[])
            if node.get('additionalProperties') is not False:
                errors.append({'path':path,'reason':'Object must be closed; open dictionaries require explicit typed fields'})
            if not isinstance(props,dict) or not isinstance(required,list) or set(required)!=set(props) or len(required)!=len(set(required)):
                errors.append({'path':path,'reason':'Every property must be required exactly once'})
        for key in ('properties','$defs','definitions'):
            for name,child in node.get(key,{}).items():visit(child,path+'/'+key+'/'+name)
        if isinstance(node.get('items'),dict):visit(node['items'],path+'/items')
        for index,child in enumerate(node.get('anyOf',[])):visit(child,path+'/anyOf/'+str(index))
    visit(schema,'#')
    if errors:raise LegalMathError('E_SCHEMA',details={'stage':'OUTPUT_SCHEMA_PREFLIGHT','errors':errors})
    return {'status':'NECESSARY_SCHEMA_CHECKS_PASSED','provider_acceptance_not_guaranteed':True}
