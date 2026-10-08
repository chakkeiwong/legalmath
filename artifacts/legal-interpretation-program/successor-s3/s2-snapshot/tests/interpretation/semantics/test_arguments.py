import pytest
from legalmath.interpretation.semantics.arguments import Argument, Attack, Rule, Theory, construct, evaluate, from_inventory
from legalmath.interpretation.semantics.records import Settings,Priority,Premise

def settings(**kw):
    return Settings(**{"semantics":"grounded","ordering":"none","priorities":(),"max_arguments":8,"max_extensions":256,"timeout_seconds":5,**kw})

def test_mutual_attack_and_empty():
    t=Theory((Argument("A","p"),Argument("B","q")),(Attack("A","B","rebuttal","B"),Attack("B","A","rebuttal","A")))
    assert evaluate(t,"grounded").extensions==((),)
    assert evaluate(t,"preferred").extensions==(("A",),("B",))
    assert evaluate(Theory((),()),"grounded").extensions==((),)

def test_independent_argument_tree_and_attacks():
    # Directly derive trees from p -> q -> s. A contrary attacks ordinary p,
    # contrary(q) rebuts only the defeasible subargument, and !r undercuts r.
    rules=(Rule("r",("p",),"q","defeasible","declared specification"),Rule("s",("q",),"s","strict","declared specification"))
    t=construct({"P":("p","ordinary"),"N":("not-p","axiom"),"Q":("not-q","axiom"),"U":("!r","axiom")},
                rules,{("not-p","p"),("not-q","q"),("!r","rule:r")},settings())
    trees={a.id:(a.conclusion,a.children) for a in t.arguments}
    assert trees=={"P":("p",()),"N":("not-p",()),"Q":("not-q",()),"U":("!r",()),
                   "r(P)":("q",("P",)),"s(r(P))":("s",("r(P)",))}
    expected={("N",b,"premise","P") for b in ("P","r(P)","s(r(P))")}
    expected|={(x,b,k,"r(P)") for x,k in (("Q","rebuttal"),("U","undercut")) for b in ("r(P)","s(r(P))")}
    assert t.graph()==expected
    assert not any(a.source=="P" for a in t.attacks)

def test_priorities_require_warrants_and_change_rebuttals():
    rules=(Rule("r",("x",),"p","defeasible","declared"),Rule("s",("x",),"q","defeasible","declared"))
    p=Premise(id="priority",statement="r stronger than s for this test",status="declared",dependencies=())
    pref=Priority(stronger="r",weaker="s",premise=p)
    t=construct({"X":("x","axiom")},rules,{("p","q"),("q","p")},settings(ordering="last-link",priorities=(pref,)))
    assert evaluate(t,"grounded").extensions==(("X","r(X)"),)
    with pytest.raises(ValueError,match="Cyclic"):
        construct({"X":("x","axiom")},rules,set(),settings(ordering="weakest-link",priorities=(pref,Priority(stronger="s",weaker="r",premise=p))))

def test_bounds_recursion_and_large_preferred():
    t=construct({"P":("p","ordinary")},(Rule("r",("p",),"p","defeasible","cyclic"),),set(),settings())
    assert t.completion=="incomplete" and t.frontier
    assert evaluate(t,"grounded").completion=="incomplete"
    t=Theory(tuple(Argument(str(i),str(i)) for i in range(9)),())
    assert evaluate(t,"preferred").reason=="reference-subset-limit"
    assert evaluate(t,"grounded").completion=="complete"

def test_real_inventory_has_shared_premise_and_only_declared_trigger_dispute(inventory):
    t=from_inventory(inventory)
    assert len(t.arguments)==8 and len(t.attacks)==2
    result=evaluate(t,"grounded")
    assert "source" in result.extensions[0]
    assert "demonstration.A(source)" in result.extensions[0]
    assert "demonstration.B(source)" not in result.extensions[0]
    assert len(evaluate(t,"preferred").extensions)==2

def test_shared_dag_does_not_expand_paths_or_identifiers_exponentially():
    rules=tuple(Rule("r"+str(i),("p"+str(i-1),"p"+str(i-1)),"p"+str(i),"defeasible","declared DAG")
                for i in range(1,31))
    t=construct({"P":("p0","axiom")},rules,set(),settings(max_arguments=40))
    assert t.completion=="complete" and len(t.arguments)==31
    assert all(len(a.id)<=256 for a in t.arguments)
    assert evaluate(t,"preferred").completion=="incomplete"
