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
def inputCodes : List Nat := []
def rule0 : Rule := { facts := [], parents := [], head := 0 }
def rule1 : Rule := { facts := [], parents := [0], head := 1 }
def rule2 : Rule := { facts := [], parents := [1], head := 2 }
def rule3 : Rule := { facts := [], parents := [2], head := 3 }
def rule4 : Rule := { facts := [], parents := [3], head := 4 }
def rule5 : Rule := { facts := [], parents := [4], head := 5 }
def rule6 : Rule := { facts := [], parents := [5], head := 6 }
def rule7 : Rule := { facts := [], parents := [6], head := 7 }
def rule8 : Rule := { facts := [], parents := [7], head := 8 }
def rule9 : Rule := { facts := [], parents := [8], head := 9 }
def rule10 : Rule := { facts := [], parents := [9], head := 10 }
def rule11 : Rule := { facts := [], parents := [10], head := 11 }
def rule12 : Rule := { facts := [], parents := [11], head := 12 }
def rule13 : Rule := { facts := [], parents := [12], head := 13 }
def rule14 : Rule := { facts := [], parents := [13], head := 14 }
def rule15 : Rule := { facts := [], parents := [14], head := 15 }
def rule16 : Rule := { facts := [], parents := [15], head := 16 }
def rule17 : Rule := { facts := [], parents := [16], head := 17 }
def rule18 : Rule := { facts := [], parents := [17], head := 18 }
def rule19 : Rule := { facts := [], parents := [18], head := 19 }
def rule20 : Rule := { facts := [], parents := [19], head := 20 }
def rule21 : Rule := { facts := [], parents := [20], head := 21 }
def rule22 : Rule := { facts := [], parents := [21], head := 22 }
def rule23 : Rule := { facts := [], parents := [22], head := 23 }
def rule24 : Rule := { facts := [], parents := [23], head := 24 }
def rule25 : Rule := { facts := [], parents := [24], head := 25 }
def rule26 : Rule := { facts := [], parents := [25], head := 26 }
def rule27 : Rule := { facts := [], parents := [26], head := 27 }
def rule28 : Rule := { facts := [], parents := [27], head := 28 }
def rule29 : Rule := { facts := [], parents := [28], head := 29 }
def rule30 : Rule := { facts := [], parents := [29], head := 30 }
def rule31 : Rule := { facts := [], parents := [30], head := 31 }
def rule32 : Rule := { facts := [], parents := [31], head := 32 }
def rule33 : Rule := { facts := [], parents := [32], head := 33 }
def rule34 : Rule := { facts := [], parents := [33], head := 34 }
def rule35 : Rule := { facts := [], parents := [34], head := 35 }
def rule36 : Rule := { facts := [], parents := [35], head := 36 }
def rule37 : Rule := { facts := [], parents := [36], head := 37 }
def rule38 : Rule := { facts := [], parents := [37], head := 38 }
def rule39 : Rule := { facts := [], parents := [38], head := 39 }
def rule40 : Rule := { facts := [], parents := [39], head := 40 }
def rule41 : Rule := { facts := [], parents := [40], head := 41 }
def rule42 : Rule := { facts := [], parents := [41], head := 42 }
def rule43 : Rule := { facts := [], parents := [42], head := 43 }
def rule44 : Rule := { facts := [], parents := [43], head := 44 }
def rule45 : Rule := { facts := [], parents := [44], head := 45 }
def rule46 : Rule := { facts := [], parents := [45], head := 46 }
def rule47 : Rule := { facts := [], parents := [46], head := 47 }
def rule48 : Rule := { facts := [], parents := [47], head := 48 }
def rule49 : Rule := { facts := [], parents := [48], head := 49 }
def rule50 : Rule := { facts := [], parents := [49], head := 50 }
def rule51 : Rule := { facts := [], parents := [50], head := 51 }
def rule52 : Rule := { facts := [], parents := [51], head := 52 }
def rule53 : Rule := { facts := [], parents := [52], head := 53 }
def rule54 : Rule := { facts := [], parents := [53], head := 54 }
def rule55 : Rule := { facts := [], parents := [54], head := 55 }
def rule56 : Rule := { facts := [], parents := [55], head := 56 }
def rule57 : Rule := { facts := [], parents := [56], head := 57 }
def rule58 : Rule := { facts := [], parents := [57], head := 58 }
def rule59 : Rule := { facts := [], parents := [58], head := 59 }
def rule60 : Rule := { facts := [], parents := [59], head := 60 }
def rule61 : Rule := { facts := [], parents := [60], head := 61 }
def rule62 : Rule := { facts := [], parents := [61], head := 62 }
def rule63 : Rule := { facts := [], parents := [62], head := 63 }
def inputRules : List Rule := [rule0, rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10, rule11, rule12, rule13, rule14, rule15, rule16, rule17, rule18, rule19, rule20, rule21, rule22, rule23, rule24, rule25, rule26, rule27, rule28, rule29, rule30, rule31, rule32, rule33, rule34, rule35, rule36, rule37, rule38, rule39, rule40, rule41, rule42, rule43, rule44, rule45, rule46, rule47, rule48, rule49, rule50, rule51, rule52, rule53, rule54, rule55, rule56, rule57, rule58, rule59, rule60, rule61, rule62, rule63]
def returned : List Nat := [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63]
theorem head_0 : Derivable inputRules inputCodes 0 := by
  apply Derivable.byRule (r := rule0) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp [rule0] at hp
theorem head_1 : Derivable inputRules inputCodes 1 := by
  apply Derivable.byRule (r := rule1) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule1, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_0
theorem head_2 : Derivable inputRules inputCodes 2 := by
  apply Derivable.byRule (r := rule2) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule2, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_1
theorem head_3 : Derivable inputRules inputCodes 3 := by
  apply Derivable.byRule (r := rule3) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule3, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_2
theorem head_4 : Derivable inputRules inputCodes 4 := by
  apply Derivable.byRule (r := rule4) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule4, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_3
theorem head_5 : Derivable inputRules inputCodes 5 := by
  apply Derivable.byRule (r := rule5) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule5, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_4
theorem head_6 : Derivable inputRules inputCodes 6 := by
  apply Derivable.byRule (r := rule6) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule6, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_5
theorem head_7 : Derivable inputRules inputCodes 7 := by
  apply Derivable.byRule (r := rule7) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule7, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_6
theorem head_8 : Derivable inputRules inputCodes 8 := by
  apply Derivable.byRule (r := rule8) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule8, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_7
theorem head_9 : Derivable inputRules inputCodes 9 := by
  apply Derivable.byRule (r := rule9) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule9, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_8
theorem head_10 : Derivable inputRules inputCodes 10 := by
  apply Derivable.byRule (r := rule10) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule10, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_9
theorem head_11 : Derivable inputRules inputCodes 11 := by
  apply Derivable.byRule (r := rule11) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule11, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_10
theorem head_12 : Derivable inputRules inputCodes 12 := by
  apply Derivable.byRule (r := rule12) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule12, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_11
theorem head_13 : Derivable inputRules inputCodes 13 := by
  apply Derivable.byRule (r := rule13) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule13, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_12
theorem head_14 : Derivable inputRules inputCodes 14 := by
  apply Derivable.byRule (r := rule14) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule14, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_13
theorem head_15 : Derivable inputRules inputCodes 15 := by
  apply Derivable.byRule (r := rule15) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule15, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_14
theorem head_16 : Derivable inputRules inputCodes 16 := by
  apply Derivable.byRule (r := rule16) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule16, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_15
theorem head_17 : Derivable inputRules inputCodes 17 := by
  apply Derivable.byRule (r := rule17) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule17, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_16
theorem head_18 : Derivable inputRules inputCodes 18 := by
  apply Derivable.byRule (r := rule18) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule18, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_17
theorem head_19 : Derivable inputRules inputCodes 19 := by
  apply Derivable.byRule (r := rule19) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule19, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_18
theorem head_20 : Derivable inputRules inputCodes 20 := by
  apply Derivable.byRule (r := rule20) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule20, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_19
theorem head_21 : Derivable inputRules inputCodes 21 := by
  apply Derivable.byRule (r := rule21) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule21, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_20
theorem head_22 : Derivable inputRules inputCodes 22 := by
  apply Derivable.byRule (r := rule22) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule22, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_21
theorem head_23 : Derivable inputRules inputCodes 23 := by
  apply Derivable.byRule (r := rule23) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule23, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_22
theorem head_24 : Derivable inputRules inputCodes 24 := by
  apply Derivable.byRule (r := rule24) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule24, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_23
theorem head_25 : Derivable inputRules inputCodes 25 := by
  apply Derivable.byRule (r := rule25) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule25, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_24
theorem head_26 : Derivable inputRules inputCodes 26 := by
  apply Derivable.byRule (r := rule26) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule26, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_25
theorem head_27 : Derivable inputRules inputCodes 27 := by
  apply Derivable.byRule (r := rule27) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule27, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_26
theorem head_28 : Derivable inputRules inputCodes 28 := by
  apply Derivable.byRule (r := rule28) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule28, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_27
theorem head_29 : Derivable inputRules inputCodes 29 := by
  apply Derivable.byRule (r := rule29) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule29, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_28
theorem head_30 : Derivable inputRules inputCodes 30 := by
  apply Derivable.byRule (r := rule30) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule30, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_29
theorem head_31 : Derivable inputRules inputCodes 31 := by
  apply Derivable.byRule (r := rule31) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule31, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_30
theorem head_32 : Derivable inputRules inputCodes 32 := by
  apply Derivable.byRule (r := rule32) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule32, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_31
theorem head_33 : Derivable inputRules inputCodes 33 := by
  apply Derivable.byRule (r := rule33) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule33, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_32
theorem head_34 : Derivable inputRules inputCodes 34 := by
  apply Derivable.byRule (r := rule34) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule34, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_33
theorem head_35 : Derivable inputRules inputCodes 35 := by
  apply Derivable.byRule (r := rule35) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule35, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_34
theorem head_36 : Derivable inputRules inputCodes 36 := by
  apply Derivable.byRule (r := rule36) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule36, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_35
theorem head_37 : Derivable inputRules inputCodes 37 := by
  apply Derivable.byRule (r := rule37) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule37, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_36
theorem head_38 : Derivable inputRules inputCodes 38 := by
  apply Derivable.byRule (r := rule38) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule38, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_37
theorem head_39 : Derivable inputRules inputCodes 39 := by
  apply Derivable.byRule (r := rule39) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule39, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_38
theorem head_40 : Derivable inputRules inputCodes 40 := by
  apply Derivable.byRule (r := rule40) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule40, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_39
theorem head_41 : Derivable inputRules inputCodes 41 := by
  apply Derivable.byRule (r := rule41) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule41, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_40
theorem head_42 : Derivable inputRules inputCodes 42 := by
  apply Derivable.byRule (r := rule42) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule42, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_41
theorem head_43 : Derivable inputRules inputCodes 43 := by
  apply Derivable.byRule (r := rule43) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule43, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_42
theorem head_44 : Derivable inputRules inputCodes 44 := by
  apply Derivable.byRule (r := rule44) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule44, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_43
theorem head_45 : Derivable inputRules inputCodes 45 := by
  apply Derivable.byRule (r := rule45) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule45, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_44
theorem head_46 : Derivable inputRules inputCodes 46 := by
  apply Derivable.byRule (r := rule46) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule46, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_45
theorem head_47 : Derivable inputRules inputCodes 47 := by
  apply Derivable.byRule (r := rule47) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule47, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_46
theorem head_48 : Derivable inputRules inputCodes 48 := by
  apply Derivable.byRule (r := rule48) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule48, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_47
theorem head_49 : Derivable inputRules inputCodes 49 := by
  apply Derivable.byRule (r := rule49) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule49, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_48
theorem head_50 : Derivable inputRules inputCodes 50 := by
  apply Derivable.byRule (r := rule50) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule50, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_49
theorem head_51 : Derivable inputRules inputCodes 51 := by
  apply Derivable.byRule (r := rule51) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule51, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_50
theorem head_52 : Derivable inputRules inputCodes 52 := by
  apply Derivable.byRule (r := rule52) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule52, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_51
theorem head_53 : Derivable inputRules inputCodes 53 := by
  apply Derivable.byRule (r := rule53) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule53, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_52
theorem head_54 : Derivable inputRules inputCodes 54 := by
  apply Derivable.byRule (r := rule54) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule54, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_53
theorem head_55 : Derivable inputRules inputCodes 55 := by
  apply Derivable.byRule (r := rule55) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule55, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_54
theorem head_56 : Derivable inputRules inputCodes 56 := by
  apply Derivable.byRule (r := rule56) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule56, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_55
theorem head_57 : Derivable inputRules inputCodes 57 := by
  apply Derivable.byRule (r := rule57) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule57, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_56
theorem head_58 : Derivable inputRules inputCodes 58 := by
  apply Derivable.byRule (r := rule58) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule58, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_57
theorem head_59 : Derivable inputRules inputCodes 59 := by
  apply Derivable.byRule (r := rule59) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule59, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_58
theorem head_60 : Derivable inputRules inputCodes 60 := by
  apply Derivable.byRule (r := rule60) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule60, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_59
theorem head_61 : Derivable inputRules inputCodes 61 := by
  apply Derivable.byRule (r := rule61) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule61, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_60
theorem head_62 : Derivable inputRules inputCodes 62 := by
  apply Derivable.byRule (r := rule62) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule62, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_61
theorem head_63 : Derivable inputRules inputCodes 63 := by
  apply Derivable.byRule (r := rule63) (by decide) (by unfold factsGood; decide)
  intro p hp
  simp only [rule63, List.mem_cons, List.not_mem_nil, or_false] at hp
  subst p; exact head_62
theorem result_sound : Sound inputRules inputCodes returned := by
  intro h member
  simp only [returned, List.mem_cons, List.not_mem_nil, or_false] at member
  rcases member with member | member
  · subst h; exact head_0
  rcases member with member | member
  · subst h; exact head_1
  rcases member with member | member
  · subst h; exact head_2
  rcases member with member | member
  · subst h; exact head_3
  rcases member with member | member
  · subst h; exact head_4
  rcases member with member | member
  · subst h; exact head_5
  rcases member with member | member
  · subst h; exact head_6
  rcases member with member | member
  · subst h; exact head_7
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
  rcases member with member | member
  · subst h; exact head_13
  rcases member with member | member
  · subst h; exact head_14
  rcases member with member | member
  · subst h; exact head_15
  rcases member with member | member
  · subst h; exact head_16
  rcases member with member | member
  · subst h; exact head_17
  rcases member with member | member
  · subst h; exact head_18
  rcases member with member | member
  · subst h; exact head_19
  rcases member with member | member
  · subst h; exact head_20
  rcases member with member | member
  · subst h; exact head_21
  rcases member with member | member
  · subst h; exact head_22
  rcases member with member | member
  · subst h; exact head_23
  rcases member with member | member
  · subst h; exact head_24
  rcases member with member | member
  · subst h; exact head_25
  rcases member with member | member
  · subst h; exact head_26
  rcases member with member | member
  · subst h; exact head_27
  rcases member with member | member
  · subst h; exact head_28
  rcases member with member | member
  · subst h; exact head_29
  rcases member with member | member
  · subst h; exact head_30
  rcases member with member | member
  · subst h; exact head_31
  rcases member with member | member
  · subst h; exact head_32
  rcases member with member | member
  · subst h; exact head_33
  rcases member with member | member
  · subst h; exact head_34
  rcases member with member | member
  · subst h; exact head_35
  rcases member with member | member
  · subst h; exact head_36
  rcases member with member | member
  · subst h; exact head_37
  rcases member with member | member
  · subst h; exact head_38
  rcases member with member | member
  · subst h; exact head_39
  rcases member with member | member
  · subst h; exact head_40
  rcases member with member | member
  · subst h; exact head_41
  rcases member with member | member
  · subst h; exact head_42
  rcases member with member | member
  · subst h; exact head_43
  rcases member with member | member
  · subst h; exact head_44
  rcases member with member | member
  · subst h; exact head_45
  rcases member with member | member
  · subst h; exact head_46
  rcases member with member | member
  · subst h; exact head_47
  rcases member with member | member
  · subst h; exact head_48
  rcases member with member | member
  · subst h; exact head_49
  rcases member with member | member
  · subst h; exact head_50
  rcases member with member | member
  · subst h; exact head_51
  rcases member with member | member
  · subst h; exact head_52
  rcases member with member | member
  · subst h; exact head_53
  rcases member with member | member
  · subst h; exact head_54
  rcases member with member | member
  · subst h; exact head_55
  rcases member with member | member
  · subst h; exact head_56
  rcases member with member | member
  · subst h; exact head_57
  rcases member with member | member
  · subst h; exact head_58
  rcases member with member | member
  · subst h; exact head_59
  rcases member with member | member
  · subst h; exact head_60
  rcases member with member | member
  · subst h; exact head_61
  rcases member with member | member
  · subst h; exact head_62
  subst h; exact head_63
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
    exact (by decide)
  subst r
  intro facts parents
  exact (by decide)
theorem actual_runtime_exact : ∀ h, h ∈ returned ↔ Derivable inputRules inputCodes h :=
  sound_closed_exact inputRules inputCodes returned result_sound result_closed
#print axioms actual_runtime_exact
