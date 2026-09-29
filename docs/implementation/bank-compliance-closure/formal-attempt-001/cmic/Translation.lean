import Std

namespace LegalMathSharedLowering

-- For exact scaling, changing the numerator's sign changes the quotient's
-- sign. The converse follows by applying the same identity twice. Thus the
-- rewrite cannot turn an indivisible integer product into an exact one.
theorem negative_scale_exact (x n d q : Int) (exact : x * n = q * d) :
    x * (-n) = (-q) * d := by
  calc
    x * (-n) = -(x * n) := Int.mul_neg x n
    _ = -(q * d) := congrArg (fun z : Int => -z) exact
    _ = (-q) * d := (Int.neg_mul q d).symm

theorem negative_scale_domain (x n d : Int) :
    (∃ q, x * n = q * d) ↔ (∃ q, x * (-n) = q * d) := by
  constructor
  · rintro ⟨q, h⟩
    exact ⟨-q, negative_scale_exact x n d q h⟩
  · rintro ⟨q, h⟩
    have h' := negative_scale_exact x (-n) d q h
    simp only [Int.neg_neg] at h'
    exact ⟨-q, h'⟩

-- Constructor trees express the same typed formal proposal on both sides.
-- This theorem deliberately leaves English interpretation and the backend out.
inductive Tree where
  | atom : String → Tree
  | node : String → List Tree → Tree
deriving Repr

-- Identity of the independently reconstructed trees preserves every semantics
-- of those constructors, for every context (including previously unseen inputs).
theorem preservation {Context Value : Type} (interpret : Context → Tree → Value)
    (context : Context) (source target : Tree) (same : source = target) :
    interpret context source = interpret context target := by
  cases same
  rfl

end LegalMathSharedLowering

open LegalMathSharedLowering
def proposed : Tree := (Tree.node "program" [(Tree.node "output" [(Tree.atom "satisfied"), (Tree.atom "bool"), (Tree.node "literal.bool" [(Tree.atom "true")]), (Tree.node "all" [(Tree.node "fact" [(Tree.atom "otherwise_permissible")]), (Tree.node "any" [(Tree.node "not" [(Tree.node "all" [(Tree.node "fact" [(Tree.atom "transaction_purchase_or_sale")]), (Tree.node "fact" [(Tree.atom "designated_issuer")]), (Tree.node "fact" [(Tree.atom "covered_security")]), (Tree.node "fact" [(Tree.atom "restriction_in_force")]), (Tree.node "any" [(Tree.node "fact" [(Tree.atom "ultimate_party_us_person")]), (Tree.node "all" [(Tree.node "fact" [(Tree.atom "principal_capacity")]), (Tree.node "fact" [(Tree.atom "actor_us_person")])])])])]), (Tree.node "fact" [(Tree.atom "applicable_ofac_authorization")]), (Tree.node "all" [(Tree.node "fact" [(Tree.atom "solely_divestment")]), (Tree.node "fact" [(Tree.atom "divestment_window_open")])])])])])])
def lowered : Tree := (Tree.node "program" [(Tree.node "output" [(Tree.atom "satisfied"), (Tree.atom "bool"), (Tree.node "literal.bool" [(Tree.atom "true")]), (Tree.node "all" [(Tree.node "fact" [(Tree.atom "otherwise_permissible")]), (Tree.node "any" [(Tree.node "not" [(Tree.node "all" [(Tree.node "fact" [(Tree.atom "transaction_purchase_or_sale")]), (Tree.node "fact" [(Tree.atom "designated_issuer")]), (Tree.node "fact" [(Tree.atom "covered_security")]), (Tree.node "fact" [(Tree.atom "restriction_in_force")]), (Tree.node "any" [(Tree.node "fact" [(Tree.atom "ultimate_party_us_person")]), (Tree.node "all" [(Tree.node "fact" [(Tree.atom "principal_capacity")]), (Tree.node "fact" [(Tree.atom "actor_us_person")])])])])]), (Tree.node "fact" [(Tree.atom "applicable_ofac_authorization")]), (Tree.node "all" [(Tree.node "fact" [(Tree.atom "solely_divestment")]), (Tree.node "fact" [(Tree.atom "divestment_window_open")])])])])])])
theorem translation_preserved {Context Value : Type} (interpret : Context → Tree → Value) (context : Context) :
  interpret context proposed = interpret context lowered := by
  apply preservation
  rfl
#print axioms translation_preserved
