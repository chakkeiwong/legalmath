/- Conditional rejection and preservation of disagreement under partitioning.
   Source entailment and selection of the obligations are explicit premises. -/
namespace LegalMathChallenges

structure Obligation (State : Type) where
  guard : State → Bool
  expected : Bool

def Satisfies {State : Type} (scope body : State → Bool)
    (obligation : Obligation State) (state : State) : Prop :=
  obligation.guard state = true →
    scope state = true ∧ body state = obligation.expected

def Admissible {State Index : Type} (scope body : State → Bool)
    (obligations : Index → Obligation State) : Prop :=
  ∀ index state, Satisfies scope body (obligations index) state

theorem conditional_rejection {State Index : Type}
    (scope body : State → Bool) (obligations : Index → Obligation State)
    (index : Index) (state : State)
    (trigger : (obligations index).guard state = true)
    (violation : scope state ≠ true ∨ body state ≠ (obligations index).expected) :
    ¬ Admissible scope body obligations := by
  intro all
  have satisfied := all index state trigger
  cases violation with
  | inl outside => exact outside satisfied.1
  | inr wrong => exact wrong satisfied.2

theorem joined_partition_obligations {Batch : Type} {Item : Batch → Type}
    (property : (batch : Batch) → Item batch → Prop) :
    (∀ batch item, property batch item) ↔
    (∀ joined : Sigma Item, property joined.1 joined.2) := by
  constructor
  · intro each joined
    exact each joined.1 joined.2
  · intro joined batch item
    exact joined ⟨batch, item⟩

theorem partitioned_disagreement {Batch Answer : Type} {Item : Batch → Type}
    (report : (batch : Batch) → Item batch → Answer)
    (left right : Sigma Item)
    (different : report left.1 left.2 ≠ report right.1 right.2) :
    ¬ ∃ answer, ∀ batch item, report batch item = answer := by
  intro uniform
  obtain ⟨answer, every⟩ := uniform
  exact different ((every left.1 left.2).trans (every right.1 right.2).symm)

end LegalMathChallenges
#print axioms LegalMathChallenges.conditional_rejection
#print axioms LegalMathChallenges.joined_partition_obligations
#print axioms LegalMathChallenges.partitioned_disagreement
