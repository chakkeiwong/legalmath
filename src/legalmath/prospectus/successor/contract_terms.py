"""Selected-occurrence term admission; finance consumes P3's checked values."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from datetime import date
import re
from .anchors import fields, bind
from .contracts import digest
from .occurrences import uses
from .admissions import review
from .coupon_dates import anchored_date, lattice_index

REQUIRED = {"currency", "annual_rate", "day_count", "frequency", "eom", "adjustment", "rounding"}
EXTENDED = {'issue_principal','calculation_amount','fixed_coupon_amount','accrual_start','accrual_end',
            'due_date','maturity_date','references','stub'}
FIXED_PHASE = REQUIRED | {'issue_principal', 'accrual_start', 'accrual_end', 'due_date', 'coupon_anchor',
                          'fixed_phase_end', 'fixed_phase_boundary', 'note_form', 'references', 'stub'}


def admit(graph, assembly, packet):
    fields(packet, {"version", "assembly_sha256", "review", "terms"},
           {"version", "assembly_sha256", "review", "terms"})
    versions = {'selected-coupon-terms.v1':REQUIRED,
                'selected-coupon-terms.v2':REQUIRED | EXTENDED,
                'selected-coupon-terms.v3':REQUIRED | EXTENDED | {'coupon_anchor'},
                'selected-coupon-terms.v4':REQUIRED | EXTENDED | {'coupon_anchor', 'note_form', 'broken_coupon_amount'},
                'selected-coupon-terms.v5':FIXED_PHASE}
    if packet["version"] not in versions or packet["assembly_sha256"] != digest(assembly):
        raise ValueError("Contract term assembly changed")
    review(packet["review"])
    if set(packet["terms"]) != versions[packet['version']]:
        raise ValueError("Complete named coupon term set required")
    initial = packet['version'] == 'selected-coupon-terms.v4'
    amounts = {'issue_principal','calculation_amount','fixed_coupon_amount'} | ({'broken_coupon_amount'} if initial else set())
    terms = {}
    for name, row in packet["terms"].items():
        fields(row, {"value", "source", "use", "rule", "reason", "continuations"}, {"value", "source", "use", "rule", "reason"})
        matches = [m for m in uses(graph, assembly, row["source"]) if m["unit"] == row["use"]]
        if len(matches) != 1 or not row["reason"]:
            raise ValueError("Contract term requires an operative selected occurrence")
        text = row["source"]["quote"].strip()
        rule = row["rule"]
        previous = row['source']
        for continuation in row.get('continuations', []):
            fields(continuation, {'source', 'use'}, {'source', 'use'})
            current = continuation['source']
            bind(graph, previous)
            bind(graph, current)
            left = next(u for u in graph['units'] if u['id'] == previous['unit'])
            right = next(u for u in graph['units'] if u['id'] == current['unit'])
            if (rule != 'first-annual-date' or left['document'] != right['document'] or
                    left['page'] != right['page'] or right['order'] != left['order'] + 1 or
                    previous['end'] != len(left['raw']) or current['start'] != 0 or
                    len([m for m in uses(graph, assembly, current) if m['unit'] == continuation['use']]) != 1):
                raise ValueError('Term continuation requires adjacent selected source lines')
            text += ' ' + current['quote'].strip()
            previous = current
        try:
            if rule == "percent":
                matched=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*(?:%|per cent\.)',text)
                if not matched or name != "annual_rate":
                    raise ValueError("Percent rate quotation required")
                if Decimal(matched[1]) / 100 != Decimal(row["value"]):
                    raise ValueError("Rate differs from selected percentage")
            elif rule == 'amount':
                if initial:
                    from .coupon_amounts import quoted_amount
                    from ..semantics import exact
                    if name not in amounts or quoted_amount(text, packet['terms']['currency']['value']) != exact(row['value']):
                        raise ValueError('Amount differs from selected numeric quotation')
                else:
                    matched=re.fullmatch(r'(?:([A-Z]{3})\s+)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)',text)
                    if (name not in amounts or not matched or
                            matched[1] not in {None, packet['terms']['currency']['value']} or
                            Decimal(matched[2].replace(',','')) != Decimal(row['value'])):
                        raise ValueError('Amount differs from selected numeric quotation')
            elif rule == 'currency-label':
                labels = {'Pound Sterling ("£")': 'GBP'}
                if not initial or name != 'currency' or text not in labels or row['value'] != labels[text]:
                    raise ValueError('Currency differs from the supported selected label')
            elif rule == 'first-annual-date':
                matched = re.fullmatch(r'(\d{1,2}) ([A-Za-z]+) in each year, from \(and including\) \1 \2 (\d{4}) up to \(and including\) the Maturity', text)
                if name not in {'accrual_end', 'due_date'} or not matched:
                    raise ValueError('Explicit first annual coupon date required')
                months = 'January February March April May June July August September October November December'.split()
                if matched[2] not in months or date(int(matched[3]), months.index(matched[2])+1, int(matched[1])).isoformat() != row['value']:
                    raise ValueError('Date differs from selected annual payment clause')
            elif rule == 'english-date':
                months='January February March April May June July August September October November December'.split()
                tokens=text.split()
                if name not in {'accrual_start','accrual_end','due_date','maturity_date','coupon_anchor','fixed_phase_end'} or len(tokens)!=3 or tokens[1] not in months or date(int(tokens[2]),months.index(tokens[1])+1,int(tokens[0])).isoformat()!=row['value']:
                    raise ValueError('Date differs from selected quotation')
            elif rule == 'annual':
                if name != 'frequency' or type(row['value']) is not int or row['value']!=1 or text!='in each year':
                    raise ValueError('Annual frequency quotation required')
            elif rule == "literal":
                if row["value"] != text:
                    raise ValueError("Term differs from its literal quotation")
            elif rule == "integer":
                if type(row["value"]) is not int or str(row["value"]) != text:
                    raise ValueError("Integer term differs from its quotation")
            elif rule != "reviewed-convention" or name in ({"annual_rate", "currency", "frequency",'accrual_start','accrual_end','due_date','maturity_date','fixed_phase_end'} | amounts):
                raise ValueError("Unsupported deterministic term translation")
        except (InvalidOperation, TypeError) as exc:
            raise ValueError("Invalid term representation") from exc
        if name in amounts and rule != 'amount':
            raise ValueError('Amount terms require deterministic amount translation')
        if name in {'accrual_start', 'accrual_end', 'due_date', 'maturity_date', 'fixed_phase_end'} and rule not in {'english-date', 'first-annual-date'}:
            raise ValueError('Date terms require deterministic date translation')
        if name == 'coupon_anchor' and rule != 'english-date':
            raise ValueError('Coupon anchor requires deterministic English date translation')
        terms[name] = {**row, "selected_use": matches[0]}
    return {"version": ('admitted-coupon-terms.v4' if packet['version']=='selected-coupon-terms.v5' else 'admitted-coupon-terms.v3' if initial else 'admitted-coupon-terms.v2' if packet['version']=='selected-coupon-terms.v3' else 'admitted-coupon-terms.v1'),
            "assembly_sha256": digest(assembly),
            "graph_sha256": digest(graph), "terms": terms, "review": packet["review"],
            "qualification": "CONDITIONAL_ON_SUPPLIED_CONVENTION_INTERPRETATIONS"}


def scenario(admitted, calculation, graph, assembly):
    if calculation.get('version') == 'selected-fixed-maturity-calculation.v1':
        from .fixed_maturity import calculate
        return calculate(admitted, calculation, graph, assembly)
    if calculation.get('version') == 'selected-fixed-term-calculation.v1':
        from .fixed_term import calculate
        return calculate(admitted, calculation, graph, assembly)
    if admitted.get('version') == 'admitted-coupon-terms.v4':
        from .fixed_phase import calculate
        return calculate(admitted, calculation, graph, assembly)
    from .fixed_coupon import calculate
    fields(calculation, {"version", "terms_sha256", "premises"}, {"version", "terms_sha256", "premises"})
    if (calculation["version"] != "selected-coupon-calculation.v1" or calculation["terms_sha256"] != digest(admitted) or
            admitted["assembly_sha256"] != digest(assembly) or admitted["graph_sha256"] != digest(graph)):
        raise ValueError("Selected contract terms or calculation binding changed")
    value = deepcopy(calculation["premises"])
    profiles = {'admitted-coupon-terms.v1':'fixed-coupon.v1', 'admitted-coupon-terms.v2':'fixed-coupon.v2',
                'admitted-coupon-terms.v3':'fixed-coupon.v3'}
    if admitted.get('version') not in profiles or value.get('profile') != profiles[admitted['version']]:
        raise ValueError('Selected term version requires its matching calculation profile')
    if set(admitted['terms']) & set(value):
        raise ValueError("Calculation premises cannot replace selected contract terms")
    if value.get("premise_kind") != "HYPOTHETICAL":
        raise ValueError("Actual entitlement/event validation is not established by this calculation")
    full = EXTENDED <= set(admitted['terms'])
    for key, term in admitted["terms"].items():
        if key in {'issue_principal','maturity_date'}:
            continue
        value[key] = term["value"]
        value.setdefault("evidence", {})[key] = {"source": term["source"], "reason": term["reason"]}
    output = calculate(value, graph)
    schedule=None
    initial = admitted['version'] == 'admitted-coupon-terms.v3'
    if full:
        from fractions import Fraction
        principal=Fraction(admitted['terms']['issue_principal']['value'])
        if principal <= 0 or sum(Fraction(h['principal']) for h in value['holdings']) > principal:
            raise ValueError('Holdings exceed admitted issue principal')
        schedule=(initial_stub_schedule if initial else regular_schedule)(value['accrual_start'],value['accrual_end'],
            admitted['terms']['maturity_date']['value'],value['frequency'],value['eom'],value['stub'],
            coupon_anchor=value.get('coupon_anchor'))
        if value['due_date'] != value['accrual_end']:
            raise ValueError('Declared coupon date differs from admitted period')
    return {"calculation": output, "selected_terms_sha256": digest(admitted),
            **({'coupon_schedule':schedule, 'schedule_scope':'UNADJUSTED_DUE_DATES_ONLY'} if initial else {'regular_due_dates':schedule}),
            "contract_terms": admitted, "fact_scope": "HYPOTHETICAL_ENTITLEMENT_AND_EVENTS",
            "full_settlement_supported": False}


def regular_schedule(start, first, maturity, frequency, eom, stub, coupon_anchor=None):
    if stub != 'REGULAR' or type(frequency) is not int or frequency not in {1,2,3,4,6,12} or type(eom) is not bool:
        raise ValueError('Regular schedule requires explicit frequency/EOM and no stub')
    initial, finish = date.fromisoformat(start),date.fromisoformat(maturity)
    anchor = initial.isoformat() if coupon_anchor is None else coupon_anchor
    initial_index = 0 if coupon_anchor is None else lattice_index(start, anchor, frequency, eom)
    def advance(n):
        return anchored_date(anchor, (initial_index+n)*(12//frequency), eom)
    if advance(1).isoformat()!=first:
        raise ValueError('First coupon requires an undeclared stub or date convention')
    dates=[]
    for n in range(1,601):
        day=advance(n)
        if day > finish:
            raise ValueError('Maturity requires an undeclared final stub')
        dates.append(day.isoformat())
        if day==finish:
            return dates
    raise ValueError('Regular schedule exceeds 600 coupons')


def initial_stub_schedule(start, first, maturity, frequency, eom, stub, coupon_anchor=None):
    """One explicit first stub followed by regular anchored, unadjusted due dates."""
    if (stub not in {'SHORT_FIRST', 'LONG_FIRST'} or type(frequency) is not int
            or frequency not in {1, 2, 3, 4, 6, 12} or type(eom) is not bool or coupon_anchor is None):
        raise ValueError('Initial schedule requires an explicit first stub, frequency, EOM and anchor')
    first_index = lattice_index(first, coupon_anchor, frequency, eom)
    last_index = lattice_index(maturity, coupon_anchor, frequency, eom)
    initial = date.fromisoformat(start)
    previous = anchored_date(coupon_anchor, (first_index - 1) * (12 // frequency), eom)
    if (initial >= date.fromisoformat(first) or
            stub == 'SHORT_FIRST' and initial <= previous or
            stub == 'LONG_FIRST' and initial >= previous):
        raise ValueError('First schedule interval contradicts the declared stub')
    count = last_index - first_index + 1
    if not 1 <= count <= 600:
        raise ValueError('Initial schedule requires maturity at/after first coupon and at most 600 coupons')
    result, left = [], start
    for n in range(count):
        right = anchored_date(coupon_anchor, (first_index + n) * (12 // frequency), eom).isoformat()
        result.append({'accrual_start':left, 'accrual_end':right, 'due_date':right,
                       'stub':stub if n == 0 else 'REGULAR'})
        left = right
    return result
