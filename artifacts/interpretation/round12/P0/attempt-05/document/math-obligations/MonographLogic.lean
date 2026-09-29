import Std

-- Three information states; the inconsistent fourth bit pair is excluded.
inductive Tri where
  | yes | no | unknown
deriving DecidableEq

def truth : Tri → Bool
  | .yes => true
  | _ => false
def falsity : Tri → Bool
  | .no => true
  | _ => false
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

theorem truth_conj (a b : Tri) : truth (conj a b) = (truth a && truth b) := by
  cases a <;> cases b <;> rfl
theorem falsity_conj (a b : Tri) : falsity (conj a b) = (falsity a || falsity b) := by
  cases a <;> cases b <;> rfl
theorem truth_disj (a b : Tri) : truth (disj a b) = (truth a || truth b) := by
  cases a <;> cases b <;> rfl
theorem falsity_disj (a b : Tri) : falsity (disj a b) = (falsity a && falsity b) := by
  cases a <;> cases b <;> rfl
theorem truth_neg (a : Tri) : truth (neg a) = falsity a := by cases a <;> rfl
theorem falsity_neg (a : Tri) : falsity (neg a) = truth a := by cases a <;> rfl
theorem not_inconsistent (a : Tri) : (truth a && falsity a) = false := by cases a <;> rfl
theorem unknown_excluded_middle : disj .unknown (neg .unknown) = .unknown := rfl
theorem knownness_injective (a b : Tri)
    (ht : truth a = truth b) (hf : falsity a = falsity b) : a = b := by
  cases a <;> cases b <;> simp_all [truth, falsity]

-- A two-component offer separates the universal and existential readings.
theorem exists_not_forall : (∃ b : Bool, b = true) ∧ ¬ (∀ b : Bool, b = true) := by
  constructor
  · exact ⟨true, rfl⟩
  · intro h
    have bad := h false
    cases bad
-- Both components are gifts; only the second is a discount.
theorem component_offer_difference :
    ((true && !false) || (true && !true)) ≠
    ((true || true) && !(false || true)) := by decide

-- The source's printed membership test wrongly marks all-fulfilled maintenance.
theorem maintenance_typo_counterexample :
    (true || true || true) ≠ (!true || !true || !true) := by decide

-- Exact quantities, with enough funds and a positive divisor.
theorem transfer_conservation (b r q : Nat) (h : q ≤ b) :
    (b - q) + (r + q) = b + r := by omega
theorem integer_division (amount d : Nat) (hd : 0 < d) :
    amount = d * (amount / d) + amount % d ∧ amount % d < d := by
  constructor
  · exact (Nat.div_add_mod amount d).symm
  · exact Nat.mod_lt amount hd
theorem deadline_excludes_boundary (d : Nat) : ¬ (d < d) := by omega
