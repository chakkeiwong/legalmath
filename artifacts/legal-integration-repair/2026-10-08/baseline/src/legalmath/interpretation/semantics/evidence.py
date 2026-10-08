"""Narrow observation derivations with actor, provider and bitemporal scope."""
from typing import Literal
from .records import Record,Text,Hash,Interval,Scope,Support,Premise
from pydantic import model_validator

class Observation(Record):
    id: Text
    entity: Text
    provider: Text
    product: Text
    component: Text
    activity: Text
    kind: Literal["appointment","supervision","discrepancy","ownership-assertion","incident","remediation","replacement","termination","migration","correction"]
    positive: bool
    event: Interval
    validity: Interval
    known_on: str | None
    evidence_hash: Hash
    completeness: Premise | None = None
    relates_to: tuple[Text,...] = ()
    @model_validator(mode="after")
    def date(self):
        Interval(start=self.known_on,end=self.known_on)
        return self

PREDICATES={"appointment":"appointment_recorded","supervision":"supervision_event_recorded",
            "discrepancy":"record_discrepancy_recorded","ownership-assertion":"ownership_assertion_recorded",
            "incident":"incident_recorded","remediation":"remediation_recorded","replacement":"replacement_recorded",
            "termination":"termination_recorded","migration":"migration_recorded","correction":"correction_recorded"}

def applicability(observation,scope,provider,known_by):
    Interval(start=known_by,end=known_by)
    if known_by is None: return "unknown",("unknown-knowledge-cutoff",)
    reasons=[]
    for actual,expected in ((observation.entity,scope.actor),(observation.provider,provider),
        (observation.product,scope.product),(observation.component,scope.component),(observation.activity,scope.activity)):
        if expected is None: reasons.append("unknown-identity")
        elif actual!=expected: return "out-of-scope",("different-identity",)
    if observation.known_on is None: reasons.append("unknown-knowledge-date")
    elif observation.known_on>known_by: return "out-of-scope",("learned-after-cutoff",)
    for interval in (observation.event,observation.validity):
        if None in (interval.start,interval.end,scope.interval.start,scope.interval.end):
            reasons.append("unknown-interval")
        elif interval.end<scope.interval.start or interval.start>scope.interval.end:
            return "out-of-scope",("disjoint-interval",)
    intervals=(observation.event,observation.validity,scope.interval)
    if all(i.start is not None and i.end is not None for i in intervals):
        if max(i.start for i in intervals)>min(i.end for i in intervals):
            return "out-of-scope",("event-outside-validity",)
    return ("unknown",tuple(sorted(set(reasons)))) if reasons else ("declared",())

def derive(observations,predicate,scope,provider,known_by):
    if len({o.id for o in observations})!=len(observations): raise ValueError("Duplicate observation")
    positive=[];negative=[];retained=[];unresolved=[]
    for o in observations:
        status,reasons=applicability(o,scope,provider,known_by)
        selected=PREDICATES[o.kind]==predicate
        if selected and status=="declared":
            if not o.positive and (o.completeness is None or o.completeness.status!="declared"):
                reasons=("missing-completeness-premise",);status="unknown"
            else:
                (positive if o.positive else negative).append(o.id)
        if selected and status=="unknown": unresolved.extend(reasons)
        retained.append({"observation":o.model_dump(mode="json"),"applicability":status,
                         "reasons":list(reasons),"matches_predicate":selected})
    if predicate not in PREDICATES.values(): unresolved.append("missing-evaluative-rule")
    support=Support(positive=tuple(sorted(positive)),negative=tuple(sorted(negative)))
    return {"predicate":predicate,"support":support.model_dump(mode="json"),"state":support.state,
            "unresolved":sorted(set(unresolved)),"observations":retained,
            "classification":"recorded-observation-only","legal_consequences":"NOT_ESTABLISHED"}

def declared_fixture():
    """Synthetic lifecycle evidence; no labels asserting legal adequacy."""
    common=dict(entity="issuer",provider="operator-1",product="fund",component="register",activity="tokenisation",
                positive=True,validity=Interval(start="2026-01-01",end="2026-12-31"),known_on="2026-02-10",evidence_hash="a"*64)
    rows=[Observation(id="event."+kind,kind=kind,event=Interval(start=day,end=day),**common)
          for kind,day in (("appointment","2026-01-01"),("supervision","2026-02-01"),("incident","2026-02-02"),
                          ("remediation","2026-02-03"),("ownership-assertion","2026-02-03"))]
    return rows,Scope(actor="issuer",product="fund",component="register",activity="tokenisation",
                      interval=Interval(start="2026-01-01",end="2026-12-31"))
