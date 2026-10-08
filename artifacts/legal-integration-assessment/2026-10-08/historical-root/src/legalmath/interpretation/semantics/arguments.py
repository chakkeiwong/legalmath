"""Finite acyclic rule-tree fragment with explicit contrary and preference premises.

This is a local checked profile, not an implementation claim for all ASPIC+.
Unproved warrants are defeasible. Exhaustive preferred semantics stops at eight
abstract arguments. Bounds never turn an unexplored frontier into acceptance.
"""
from dataclasses import dataclass
from itertools import product
import time
from .records import Settings
from ...canonical import digest

@dataclass(frozen=True)
class Rule:
    id: str
    antecedents: tuple[str, ...]
    conclusion: str
    kind: str
    warrant: str

@dataclass(frozen=True)
class Argument:
    id: str
    conclusion: str
    children: tuple[str, ...] = ()
    rule_id: str | None = None
    kind: str = "ordinary"
    rules: tuple[str, ...] = ()
    last_rules: tuple[str, ...] = ()

@dataclass(frozen=True)
class Attack:
    source: str
    target: str
    kind: str
    on: str

@dataclass(frozen=True)
class Theory:
    arguments: tuple[Argument, ...]
    attacks: tuple[Attack, ...]
    completion: str = "complete"
    frontier: tuple[str, ...] = ()

    def graph(self):
        return {(a.source,a.target,a.kind,a.on) for a in self.attacks}

@dataclass(frozen=True)
class Evaluation:
    semantics: str
    completion: str
    extensions: tuple[tuple[str, ...], ...]
    frontier: tuple[str, ...] = ()
    reason: str | None = None

def _preferences(settings, vocabulary):
    edges={}
    if len(settings.priorities)>500: raise ValueError("Priority profile limit")
    for p in settings.priorities:
        if p.premise.status != "declared" or p.stronger not in vocabulary or p.weaker not in vocabulary:
            raise ValueError("Priority needs declared premise and known identities")
        edges.setdefault(p.stronger,set()).add(p.weaker)
    pairs=set()
    for origin in edges:
        seen=set();pending=list(edges[origin])
        while pending:
            item=pending.pop()
            if item==origin: raise ValueError("Cyclic preference")
            if item in seen: continue
            seen.add(item);pending.extend(edges.get(item,()))
        pairs.update((origin,item) for item in seen)
    return pairs

def construct(premises, rules, contraries, settings):
    """premises maps IDs to (literal, ordinary|axiom); contraries are directional."""
    if not isinstance(settings,Settings): raise TypeError("Explicit Settings required")
    rules=tuple(rules)
    if len(rules)>500 or len(premises)>500 or len(contraries)>5000 or any(len(r.antecedents)>16 for r in rules):
        return Theory((),(),"incomplete",("input-profile-limit",))
    if len({r.id for r in rules})!=len(rules) or set(premises)&{r.id for r in rules}:
        raise ValueError("Duplicate premise/rule identity")
    if any(r.kind not in ("strict","defeasible") or not r.warrant for r in rules):
        raise ValueError("Rules require explicit kind and warrant")
    if any(kind not in ("ordinary","axiom") for literal,kind in premises.values()):
        raise ValueError("Unknown premise kind")
    pairs=_preferences(settings,set(premises)|{r.id for r in rules})
    started=time.monotonic()
    args={}; frontier=[]
    def add(a):
        if a.id in args: return
        if len(args)>=settings.max_arguments or time.monotonic()-started>=settings.timeout_seconds:
            frontier.append(a.id)
        else: args[a.id]=a
    for identity,(literal,kind) in sorted(premises.items()):
        add(Argument(identity,literal,kind=kind))
    # Explicit acyclic fragment: reject a cycle in the literal dependency graph.
    edges={}
    for r in rules:
        edges.setdefault(r.conclusion,set()).update(r.antecedents)
    pending={node:set(children) for node,children in edges.items()}
    ready={node for node,children in pending.items() if not children}
    # Antecedents with no defining rule are leaves, including missing premises.
    leaves={child for children in pending.values() for child in children}-set(pending)
    ready.update(leaves);visited=set()
    while ready:
        node=ready.pop();visited.add(node)
        for parent,children in pending.items():
            if node in children:
                children.remove(node)
                if not children and parent not in visited: ready.add(parent)
    recursion=any(pending.values())
    if recursion:
        frontier.extend("recursive-rule:"+r.id for r in rules)
    else:
        changed=True
        while changed and not frontier:
            changed=False
            for r in rules:
                choices=[[a for a in args.values() if a.conclusion==literal] for literal in r.antecedents]
                for children in product(*choices):
                    if time.monotonic()-started>=settings.timeout_seconds:
                        frontier.append("generation:"+r.id);break
                    identity=r.id+"("+",".join(a.id for a in children)+")"
                    if len(identity)>256:
                        identity="argument."+digest({"rule":r.id,"children":[a.id for a in children]})
                    if identity in args: continue
                    rule_ids=tuple(sorted({x for a in children for x in a.rules}|({r.id} if r.kind=="defeasible" else set())))
                    last=(r.id,) if r.kind=="defeasible" else tuple(sorted({x for a in children for x in a.last_rules}))
                    before=len(args)
                    add(Argument(identity,r.conclusion,tuple(a.id for a in children),r.id,r.kind,rule_ids,last))
                    changed |= len(args)>before
                    if frontier: break
                if frontier: break
    attacks=[]
    subtree={}
    for a in args.values():
        subtree[a.id]={a.id}
        for child in a.children: subtree[a.id].update(subtree[child])
    def subarguments(a):
        return subtree[a.id]
    def weaker(a,b):
        if settings.ordering=="none": return False
        aa=(a.id,) if a.kind=="ordinary" else (a.last_rules if settings.ordering=="last-link" else a.rules)
        bb=(b.id,) if b.kind=="ordinary" else (b.last_rules if settings.ordering=="last-link" else b.rules)
        # Deliberately explicit all-pairs strict domination, no implicit tie-break.
        return bool(aa and bb) and all((y,x) in pairs for x in aa for y in bb)
    for a in args.values():
        for b in args.values():
            for sid in sorted(subarguments(b)):
                if time.monotonic()-started>=settings.timeout_seconds:
                    return Theory(tuple(args.values()),tuple(attacks),"incomplete",
                                  tuple(sorted(set(frontier)|{"attack-frontier:"+a.id+":"+b.id})))
                sub=args[sid]
                if sub.kind=="defeasible" and (a.conclusion,"rule:"+sub.rule_id) in contraries:
                    attacks.append(Attack(a.id,b.id,"undercut",sid))
                if (a.conclusion,sub.conclusion) in contraries and sub.kind in ("ordinary","defeasible") and not weaker(a,sub):
                    attacks.append(Attack(a.id,b.id,"premise" if sub.kind=="ordinary" else "rebuttal",sid))
    return Theory(tuple(args.values()),tuple(sorted(set(attacks),key=lambda a:(a.source,a.target,a.kind,a.on))),
                  "incomplete" if frontier else "complete",tuple(sorted(set(frontier))))

def evaluate(theory, semantics, max_arguments=500, max_extensions=4096, timeout_seconds=5):
    if semantics not in ("grounded","preferred"): raise ValueError("Unknown semantics")
    ids=tuple(a.id for a in theory.arguments)
    if len(set(ids))!=len(ids) or any(a.source not in ids or a.target not in ids for a in theory.attacks):
        raise ValueError("Invalid graph")
    if theory.completion!="complete" or len(ids)>max_arguments:
        return Evaluation(semantics,"incomplete",(),theory.frontier or ids,"construction-incomplete")
    if semantics=="preferred" and len(ids)>8:
        return Evaluation(semantics,"incomplete",(),ids,"reference-subset-limit")
    started=time.monotonic()
    incoming={i:{a.source for a in theory.attacks if a.target==i} for i in ids}
    outgoing={i:{a.target for a in theory.attacks if a.source==i} for i in ids}
    def defended(chosen):
        defeated=set().union(*(outgoing[i] for i in chosen)) if chosen else set()
        return {i for i in ids if incoming[i]<=defeated}
    if semantics=="grounded":
        chosen=set()
        while True:
            if time.monotonic()-started>timeout_seconds:
                return Evaluation(semantics,"incomplete",(),ids,"time-limit")
            nxt=defended(chosen)
            if nxt==chosen: break
            chosen=nxt
        ext=(tuple(sorted(chosen)),)
    else:
        acceptable=[]
        for mask in range(1<<len(ids)):
            if time.monotonic()-started>timeout_seconds:
                return Evaluation(semantics,"incomplete",(),ids,"time-limit")
            chosen={ids[i] for i in range(len(ids)) if mask & (1<<i)}
            if any(outgoing[i]&chosen for i in chosen): continue
            if chosen<=defended(chosen): acceptable.append(chosen)
        ext=tuple(sorted(tuple(sorted(s)) for s in acceptable if not any(s<t for t in acceptable)))
    if len(ext)>max_extensions:
        return Evaluation(semantics,"incomplete",ext[:max_extensions],ids,"extension-limit")
    return Evaluation(semantics,"complete",ext)

def from_inventory(inventory):
    import json
    from .records import Branch
    branches=[Branch.model_validate_json(json.dumps(b)) for b in inventory["branches"]]
    if not branches or len({b.settings.identity() for b in branches})!=1:
        raise ValueError("Use one explicit setting per theory")
    rules=tuple(Rule(b.proposal_id,("retained-source",),b.proposal_id,"defeasible",
                     "Conditional warrant: "+b.assumptions[0].statement) for b in branches)
    # B/C make opposite trigger proposals for the specified no-request query.
    # A leaves the footnote relation disputed, so no general contrary is imposed.
    contraries={("demonstration.B","demonstration.C"),("demonstration.C","demonstration.B")}
    return construct({"source":("retained-source","axiom")},rules,contraries,branches[0].settings)
