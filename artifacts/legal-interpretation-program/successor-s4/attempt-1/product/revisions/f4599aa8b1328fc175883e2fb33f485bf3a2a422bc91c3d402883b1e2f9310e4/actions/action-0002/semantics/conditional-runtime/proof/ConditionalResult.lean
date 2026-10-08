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
def inputCodes : List Nat := [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 3, 1, 1, 1, 2, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
def rule0 : Rule := { facts := [1, 24, 15], parents := [], head := 0 }
def rule1 : Rule := { facts := [1, 24, 16], parents := [], head := 1 }
def rule2 : Rule := { facts := [1, 24, 18], parents := [], head := 2 }
def rule3 : Rule := { facts := [1, 24, 19, 17], parents := [], head := 3 }
def rule4 : Rule := { facts := [1, 24, 10], parents := [], head := 4 }
def rule5 : Rule := { facts := [1, 24, 19, 11], parents := [], head := 5 }
def rule6 : Rule := { facts := [1, 24, 21, 20], parents := [], head := 6 }
def rule7 : Rule := { facts := [1, 24, 23, 22], parents := [], head := 7 }
def rule8 : Rule := { facts := [38, 33, 42], parents := [], head := 8 }
def rule9 : Rule := { facts := [38, 33, 34, 41], parents := [], head := 9 }
def rule10 : Rule := { facts := [38, 14, 43, 39], parents := [], head := 10 }
def rule11 : Rule := { facts := [38, 14, 43, 40], parents := [], head := 11 }
def rule12 : Rule := { facts := [0, 12, 13, 3, 36], parents := [], head := 12 }
def rule13 : Rule := { facts := [0, 12, 35, 2, 37], parents := [], head := 13 }
def rule14 : Rule := { facts := [1, 8, 29], parents := [], head := 14 }
def rule15 : Rule := { facts := [1, 7, 28], parents := [], head := 15 }
def rule16 : Rule := { facts := [1, 5, 27], parents := [], head := 16 }
def rule17 : Rule := { facts := [1, 4, 26, 25], parents := [], head := 17 }
def rule18 : Rule := { facts := [1, 9, 31, 30], parents := [], head := 18 }
def rule19 : Rule := { facts := [1, 6, 32], parents := [], head := 19 }
def inputRules : List Rule := [rule0, rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10, rule11, rule12, rule13, rule14, rule15, rule16, rule17, rule18, rule19]
def returned : List Nat := [1, 2, 4, 6, 8, 9, 10, 11, 12, 13]
theorem head_1 : Derivable inputRules inputCodes 1 := by
  apply Derivable.byRule (r := rule1) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule1] at hp
theorem head_2 : Derivable inputRules inputCodes 2 := by
  apply Derivable.byRule (r := rule2) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule2] at hp
theorem head_4 : Derivable inputRules inputCodes 4 := by
  apply Derivable.byRule (r := rule4) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule4] at hp
theorem head_6 : Derivable inputRules inputCodes 6 := by
  apply Derivable.byRule (r := rule6) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule6] at hp
theorem head_8 : Derivable inputRules inputCodes 8 := by
  apply Derivable.byRule (r := rule8) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule8] at hp
theorem head_9 : Derivable inputRules inputCodes 9 := by
  apply Derivable.byRule (r := rule9) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule9] at hp
theorem head_10 : Derivable inputRules inputCodes 10 := by
  apply Derivable.byRule (r := rule10) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule10] at hp
theorem head_11 : Derivable inputRules inputCodes 11 := by
  apply Derivable.byRule (r := rule11) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule11] at hp
theorem head_12 : Derivable inputRules inputCodes 12 := by
  apply Derivable.byRule (r := rule12) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule12] at hp
theorem head_13 : Derivable inputRules inputCodes 13 := by
  apply Derivable.byRule (r := rule13) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule13] at hp
theorem result_sound : Sound inputRules inputCodes returned := by
  intro h member
  simp only [returned, List.mem_cons, List.not_mem_nil, or_false] at member
  rcases member with member | member
  · subst h; exact head_1
  rcases member with member | member
  · subst h; exact head_2
  rcases member with member | member
  · subst h; exact head_4
  rcases member with member | member
  · subst h; exact head_6
  rcases member with member | member
  · subst h; exact head_8
  rcases member with member | member
  · subst h; exact head_9
  rcases member with member | member
  · subst h; exact head_10
  rcases member with member | member
  · subst h; exact head_11
  rcases member with member | member
  · subst h; exact head_12
  subst h; exact head_13
theorem result_closed : Closed inputRules inputCodes returned := by
  intro r member
  simp only [inputRules, List.mem_cons, List.not_mem_nil, or_false] at member
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    exact (by decide)
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  rcases member with member | member
  · subst r
    intro facts parents
    change false = true at facts
    cases facts
  subst r
  intro facts parents
  change false = true at facts
  cases facts
theorem actual_runtime_exact : ∀ h, h ∈ returned ↔ Derivable inputRules inputCodes h :=
  sound_closed_exact inputRules inputCodes returned result_sound result_closed
#print axioms actual_runtime_exact
