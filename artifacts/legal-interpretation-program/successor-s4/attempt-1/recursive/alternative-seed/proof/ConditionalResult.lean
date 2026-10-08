import Std

namespace LegalMathConditional

structure Rule where
  facts : List Nat
  parents : List Nat
  head : Nat
deriving DecidableEq, Repr

def admitted (code : Nat) : Bool := Nat.beq code 1

theorem admitted_only_positive (c : Nat) : admitted c = true ↔ c = 1 := by
  exact ⟨Nat.eq_of_beq_eq_true, fun h => h ▸ Nat.beq_refl 1⟩

theorem unknown_not_admitted : admitted 0 = false := rfl
theorem negative_not_admitted : admitted 2 = false := rfl
theorem conflict_not_admitted : admitted 3 = false := rfl

def factsGood (codes : List Nat) (r : Rule) : Prop :=
  r.facts.all (fun f => codes[f]? == some 1) = true

inductive Derivable (rules : List Rule) (codes : List Nat) : Nat → Prop where
  | byRule (r : Rule) (present : r ∈ rules) (facts : factsGood codes r)
      (parents : ∀ p ∈ r.parents, Derivable rules codes p) :
      Derivable rules codes r.head

def Closed (rules : List Rule) (codes : List Nat) (xs : List Nat) : Prop :=
  ∀ r ∈ rules, factsGood codes r → (∀ p ∈ r.parents, p ∈ xs) → r.head ∈ xs

def Sound (rules : List Rule) (codes : List Nat) (xs : List Nat) : Prop :=
  ∀ h ∈ xs, Derivable rules codes h

theorem closed_contains_derivable (rules : List Rule) (codes xs : List Nat)
    (closed : Closed rules codes xs) (h : Nat) (proof : Derivable rules codes h) :
    h ∈ xs := by
  induction proof with
  | byRule r present facts parents ih =>
    exact closed r present facts ih

theorem sound_closed_exact (rules : List Rule) (codes xs : List Nat)
    (sound : Sound rules codes xs) (closed : Closed rules codes xs) :
    ∀ h, h ∈ xs ↔ Derivable rules codes h := by
  intro h
  constructor
  · exact sound h
  · exact closed_contains_derivable rules codes xs closed h

theorem least_closed_result (rules : List Rule) (codes xs ys : List Nat)
    (sound : Sound rules codes xs) (closedY : Closed rules codes ys) :
    ∀ h ∈ xs, h ∈ ys := by
  intro h member
  exact closed_contains_derivable rules codes ys closedY h (sound h member)

theorem supported_rule_only (rules : List Rule) (codes : List Nat) (h : Nat)
    (proof : Derivable rules codes h) :
    ∃ r ∈ rules, r.head = h ∧ factsGood codes r := by
  cases proof with
  | byRule r present facts parents => exact ⟨r, present, rfl, facts⟩

#print axioms admitted_only_positive
#print axioms sound_closed_exact
#print axioms least_closed_result
#print axioms supported_rule_only

end LegalMathConditional

open LegalMathConditional
set_option maxRecDepth 8192
set_option maxHeartbeats 4000000
def inputCodes : List Nat := [3]
def rule0 : Rule := { facts := [0], parents := [], head := 0 }
def rule1 : Rule := { facts := [], parents := [], head := 0 }
def rule2 : Rule := { facts := [], parents := [0], head := 1 }
def inputRules : List Rule := [rule0, rule1, rule2]
def returned : List Nat := [0, 1]
theorem head_0 : Derivable inputRules inputCodes 0 := by
  apply Derivable.byRule (r := rule1) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule1] at hp
theorem head_1 : Derivable inputRules inputCodes 1 := by
  apply Derivable.byRule (r := rule2) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule2, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_0
theorem result_sound : Sound inputRules inputCodes returned := by
  intro h member
  simp only [returned, List.mem_cons, List.not_mem_nil, or_false] at member
  rcases member with member | member
  · subst h; exact head_0
  subst h; exact head_1
theorem result_closed : Closed inputRules inputCodes returned := by
  intro r member
  simp only [inputRules, List.mem_cons, List.not_mem_nil, or_false] at member
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  subst r
  intro facts parents
  exact (by decide)
theorem actual_runtime_exact : ∀ h, h ∈ returned ↔ Derivable inputRules inputCodes h :=
  sound_closed_exact inputRules inputCodes returned result_sound result_closed
#print axioms actual_runtime_exact
