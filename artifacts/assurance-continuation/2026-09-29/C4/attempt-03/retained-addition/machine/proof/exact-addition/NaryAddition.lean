import Std

namespace LegalMathExactAddition

-- Missing is a declared arithmetic input state; conflict and time selection
-- occur outside this theorem. Int is unbounded exact mathematical arithmetic.
def add : Option Int → Option Int → Option Int
  | some a, some b => some (a + b)
  | _, _ => none

def sum (xs : List (Option Int)) : Option Int := xs.foldl add (some 0)

theorem ordered_lowering (x : Option Int) (xs : List (Option Int)) :
    sum (x :: xs) = xs.foldl add x := by
  cases x with
  | none => rfl
  | some a => simp [sum, List.foldl, add]

theorem unknown_absorbs (xs : List (Option Int)) : xs.foldl add none = none := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp [List.foldl, add, ih]

theorem missing_operand (xs ys : List (Option Int)) :
    sum (xs ++ none :: ys) = none := by
  unfold sum
  rw [List.foldl_append]
  simp only [List.foldl]
  cases xs.foldl add (some 0) <;> simp [add, unknown_absorbs]

theorem exact_fold (xs : List Int) (a : Int) :
    (xs.map some).foldl add (some a) = some (a + xs.sum) := by
  induction xs generalizing a with
  | nil => simp
  | cons x xs ih => simp [List.foldl, add, ih, Int.add_assoc]

theorem exact_sum (xs : List Int) : sum (xs.map some) = some xs.sum := by
  simp [sum, exact_fold]

#print axioms ordered_lowering
#print axioms missing_operand
#print axioms exact_sum

end LegalMathExactAddition
