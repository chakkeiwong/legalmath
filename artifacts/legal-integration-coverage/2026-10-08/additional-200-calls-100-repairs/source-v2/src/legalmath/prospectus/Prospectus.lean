/- Scoped mathematical specification. No theorem asserts English or legal fidelity. -/
namespace Prospectus

def allTrue : List Bool → Bool
  | [] => true
  | b :: bs => b && allTrue bs

def definiteAllow (worldResults : List Bool) : Bool :=
  !worldResults.isEmpty && allTrue worldResults

theorem allTrue_sound (xs : List Bool) (h : allTrue xs = true)
    (b : Bool) (hm : b ∈ xs) : b = true := by
  induction xs with
  | nil => simp at hm
  | cons x xs ih =>
    simp only [allTrue, Bool.and_eq_true] at h
    simp only [List.mem_cons] at hm
    rcases hm with he | ht
    · exact he.trans h.1
    · exact ih h.2 ht

theorem definite_sound (xs : List Bool) (h : definiteAllow xs = true)
    (b : Bool) (hm : b ∈ xs) : b = true := by
  simp only [definiteAllow, Bool.and_eq_true] at h
  exact allTrue_sound xs h.2 b hm

theorem no_vacuous_permission : definiteAllow [] = false := by rfl

theorem allTrue_complete (xs : List Bool) (h : ∀ b ∈ xs, b = true) : allTrue xs = true := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
    simp only [allTrue, Bool.and_eq_true]
    constructor
    · exact h x (by simp)
    · exact ih (by intro b hb; exact h b (by simp [hb]))

theorem refinement_preserves_truth (xs ys : List Bool)
    (hx : allTrue xs = true) (subset : ∀ b ∈ ys, b ∈ xs) : allTrue ys = true := by
  apply allTrue_complete
  intro b hb
  exact allTrue_sound xs hx b (subset b hb)

def spiEligible (client category knowledge consent current budget other : Bool) : Bool :=
  client && category && knowledge && consent && current && budget && other

theorem eligibility_requires_every_condition (client category knowledge consent current budget other : Bool)
    (h : spiEligible client category knowledge consent current budget other = true) :
    client = true ∧ category = true ∧ knowledge = true ∧ consent = true ∧
    current = true ∧ budget = true ∧ other = true := by
  simpa [spiEligible, Bool.and_eq_true, and_assoc] using h

def permanentPrincipal (principal reduction : Nat) : Nat := principal - reduction

theorem full_write_down_zero (principal : Nat) : permanentPrincipal principal principal = 0 := by
  simp [permanentPrincipal]

def skippedDistribution (principal : Nat) : Nat × Nat := (principal, 0)

theorem dividend_cancellation_preserves_principal (principal : Nat) :
    (skippedDistribution principal).1 = principal := by rfl

#print axioms definite_sound
#print axioms no_vacuous_permission
#print axioms refinement_preserves_truth
#print axioms eligibility_requires_every_condition
#print axioms full_write_down_zero
#print axioms dividend_cancellation_preserves_principal
end Prospectus
