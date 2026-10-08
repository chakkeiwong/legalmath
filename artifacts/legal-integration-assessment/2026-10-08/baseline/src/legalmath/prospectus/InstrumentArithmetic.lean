import Std

namespace LegalMathInstrument

-- Quantities are nonnegative integer numerators and positive denominators.
-- To express cents, scale the rational amount's numerator by 100 first.
theorem floor_bounds (n d : Nat) (hd : 0 < d) :
    n / d * d ≤ n ∧ n < (n / d + 1) * d := by
  constructor
  · exact Nat.div_mul_le_self n d
  · apply (Nat.div_lt_iff_lt_mul hd).mp
    omega

-- floor((2n+d)/(2d)) is rational round-half-up; its quotient interval
-- characterizes the computation independently of a decimal library.
theorem half_up_bounds (n d : Nat) (hd : 0 < d) :
    ((2*n+d)/(2*d))*(2*d) ≤ 2*n+d ∧
    2*n+d < ((2*n+d)/(2*d)+1)*(2*d) := by
  exact floor_bounds (2*n+d) (2*d) (by omega)

theorem half_up_tie (k : Nat) : (2*k+1+1)/2 = k+1 := by omega

-- A cumulative count of open days is monotone. If the selected date
-- reaches k and the preceding calendar date reaches k-1, no earlier
-- date after the anchor reaches k. Actual calendar evidence is separate.
theorem deadline_minimal (count : Int → Int) (a d k : Int)
    (mono : ∀ x y, x ≤ y → count x ≤ count y)
    (prior : count (d-1) - count a = k-1) :
    ∀ e, a < e → e < d → count e - count a < k := by
  intro e _ he
  have h := mono e (d-1) (by omega)
  omega

theorem deadline_unique (count : Int → Int) (a d e k : Int)
    (mono : ∀ x y, x ≤ y → count x ≤ count y)
    (hd : a < d) (he : a < e)
    (hitd : count d - count a = k) (hite : count e - count a = k)
    (priord : count (d-1) - count a = k-1)
    (priore : count (e-1) - count a = k-1) : d = e := by
  by_cases hlt : d < e
  ·
    have bad := deadline_minimal count a e k mono priore d hd hlt
    omega
  · by_cases hlt : e < d
    ·
      have bad := deadline_minimal count a d k mono priord e he hlt
      omega
    · omega

#print axioms floor_bounds
#print axioms half_up_bounds
#print axioms half_up_tie
#print axioms deadline_minimal
#print axioms deadline_unique
end LegalMathInstrument
