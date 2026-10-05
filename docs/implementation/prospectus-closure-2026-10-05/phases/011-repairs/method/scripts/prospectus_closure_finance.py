"""Conditional calculations from reviewed BES terms; no transaction authorization."""
from datetime import date,timedelta
from decimal import Decimal
from fractions import Fraction

def amount(value):
    if not isinstance(value,(str,Decimal,int)) or isinstance(value,bool):
        raise ValueError("Use an exact decimal amount, not binary floating point")
    value=Decimal(value)
    if not value.is_finite() or value<0:raise ValueError("Nonnegative finite amount required")
    return Fraction(value)

def euro_half_up(value):
    if value<0:raise ValueError("Negative coupon outside reviewed scope")
    units=value*100
    cents=(2*units.numerator+units.denominator)//(2*units.denominator)
    return format(Decimal(cents)/100,".2f")

def icma(start,end,periods,frequency):
    if type(frequency) is not int or frequency<1:raise ValueError("Positive annual frequency required")
    start,end=date.fromisoformat(start),date.fromisoformat(end)
    periods=[(date.fromisoformat(a),date.fromisoformat(b)) for a,b in periods]
    if start>=end or not 1<=len(periods)<=2:raise ValueError("One or two positive periods required")
    if any(a>=b for a,b in periods) or any(a[1]!=b[0] for a,b in zip(periods,periods[1:])):
        raise ValueError("Determination periods must be positive and contiguous")
    if not periods[0][0]<=start<periods[0][1] or not periods[-1][0]<end<=periods[-1][1]:
        raise ValueError("Accrual dates outside supplied determination periods")
    days=(end-start).days
    last=(periods[-1][1]-periods[-1][0]).days
    if days<=last:
        return Fraction(days,last*frequency)
    if len(periods)!=2:raise ValueError("Long period requires two determination periods")
    first=(periods[0][1]-periods[0][0]).days
    return Fraction((periods[0][1]-start).days,first*frequency)+Fraction((end-periods[1][0]).days,last*frequency)

def coupon(nominal,rate,start,end,periods,frequency,*,rounding):
    if rounding!="source_half_up":
        return {"status":"UNRESOLVED","amount":None,"reason":"Applicable rounding convention not established"}
    fraction=icma(start,end,periods,frequency)
    raw=amount(nominal)*amount(rate)*fraction
    return {"status":"CONDITIONAL","amount":euro_half_up(raw),"currency":"EUR",
        "exact_unrounded":[raw.numerator,raw.denominator],"day_count":[fraction.numerator,fraction.denominator],
        "basis":"Full nominal amount outstanding of Interbolsa Notes; printed half-up rule explicitly selected",
        "may_execute_transaction":False}

def deemed_notice(given,calendar):
    day=date.fromisoformat(given);business=0
    for _ in range(370):
        day+=timedelta(days=1);key=day.isoformat()
        value=calendar.get(key)
        if type(value) is not bool:
            return {"status":"UNRESOLVED","date":None,"missing_calendar_date":key}
        business+=value
        if business==2:return {"status":"CONDITIONAL","date":key,"may_execute_transaction":False}
    return {"status":"UNRESOLVED","date":None,"reason":"Supplied calendar does not yield two business days within bounded horizon"}

def tax_notice(delivered,redemption,*,legal_counting_confirmed):
    if legal_counting_confirmed is not True:
        return {"status":"UNRESOLVED","within_interval":None}
    days=(date.fromisoformat(redemption)-date.fromisoformat(delivered)).days
    return {"status":"CONDITIONAL","days":days,"within_interval":30<=days<=60,
        "tax_trigger_established":False,"may_execute_transaction":False}

def maturity_principal(nominal,*,purchased_and_cancelled,early_redeemed):
    for value in (purchased_and_cancelled,early_redeemed):
        if value is not None and type(value) is not bool:raise ValueError("Event facts must be Boolean or unknown")
    if purchased_and_cancelled is None or early_redeemed is None:
        return {"status":"UNRESOLVED","amount":None,"reason":"Purchase/cancellation or early redemption facts missing"}
    if purchased_and_cancelled or early_redeemed:
        return {"status":"UNRESOLVED","amount":None,"reason":"Separate cancellation/early-redemption provisions control"}
    return {"status":"CONDITIONAL","amount":euro_half_up(amount(nominal)),
        "basis":"100 percent nominal at maturity, subject to unresolved external law and full dossier",
        "may_execute_transaction":False}

def eurosystem_designation(text):
    normalized=" ".join(text.split())
    if not all(x in normalized for x in ("Yes.","does not necessarily mean","eligible collateral","eligibility criteria")):
        return {"status":"UNRESOLVED","intended_registration":None,"eligible_collateral":None}
    return {"status":"CONDITIONAL","intended_registration":True,"eligible_collateral":None,
        "reason":"Designation does not establish recognition; criteria and recognition require evidence"}

def select_section(rows,number):
    matches=[r for r in rows if r["number"]==number]
    return {"status":"UNRESOLVED" if len(matches)!=1 else "SINGLE_RECORD",
        "records":matches,"reason":"Resolve scope and amendments; duplicate numbers cannot overwrite content"}
