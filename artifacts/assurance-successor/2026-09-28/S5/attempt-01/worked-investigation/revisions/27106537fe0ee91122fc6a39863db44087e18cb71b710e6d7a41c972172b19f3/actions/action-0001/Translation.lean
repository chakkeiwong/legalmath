import Std

namespace LegalMathBoolean

-- This small semantics covers total Boolean syntax with unknown information.
-- Conflict is a separate whole-input veto, outside the expression algebra.
inductive Tri where
  | yes | no | unknown
deriving DecidableEq, Repr

def neg : Tri → Tri
  | .yes => .no
  | .no => .yes
  | .unknown => .unknown

def conj : Tri → Tri → Tri
  | .no, _ => .no
  | _, .no => .no
  | .yes, .yes => .yes
  | _, _ => .unknown

def disj : Tri → Tri → Tri
  | .yes, _ => .yes
  | _, .yes => .yes
  | .no, .no => .no
  | _, _ => .unknown

def choose : Tri → Tri → Tri → Tri
  | .yes, t, _ => t
  | .no, _, f => f
  | .unknown, _, _ => .unknown

inductive Expr where
  | fact : Nat → Expr
  | yes | no
  | neg : Expr → Expr
  | conj : Expr → Expr → Expr
  | disj : Expr → Expr → Expr
  | choose : Expr → Expr → Expr → Expr
deriving Repr

def eval (facts : Nat → Tri) : Expr → Tri
  | .fact n => facts n
  | .yes => .yes
  | .no => .no
  | .neg x => neg (eval facts x)
  | .conj a b => conj (eval facts a) (eval facts b)
  | .disj a b => disj (eval facts a) (eval facts b)
  | .choose c a b => choose (eval facts c) (eval facts a) (eval facts b)

inductive Result where
  | yes | no | unknown | conflict | outOfScope
deriving DecidableEq, Repr

def decideRule (facts : Nat → Tri) (conflict : Bool) (scope body : Expr) : Result :=
  if conflict then .conflict else
    match eval facts scope with
    | .no => .outOfScope
    | .unknown => .unknown
    | .yes => match eval facts body with
      | .yes => .yes
      | .no => .no
      | .unknown => .unknown

theorem congruence (facts : Nat → Tri) (conflict : Bool)
    (s1 s2 b1 b2 : Expr) (hs : s1 = s2) (hb : b1 = b2) :
    decideRule facts conflict s1 b1 = decideRule facts conflict s2 b2 := by
  cases hs
  cases hb
  rfl

end LegalMathBoolean

open LegalMathBoolean
def sourceScope : Expr := Expr.yes
def sourceBody : Expr := (Expr.conj (Expr.fact 0) (Expr.neg (Expr.fact 1)))
def loweredScope : Expr := Expr.yes
def loweredBody : Expr := (Expr.conj (Expr.fact 0) (Expr.neg (Expr.fact 1)))
theorem translation_preserved (facts : Nat → Tri) (conflict : Bool) :
  decideRule facts conflict sourceScope sourceBody = decideRule facts conflict loweredScope loweredBody := by
  apply congruence <;> rfl
#print axioms translation_preserved
