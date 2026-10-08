import Std

namespace LegalMathGregorian

def leap (y : Int) : Bool := decide ((y % 4 = 0 ∧ y % 100 ≠ 0) ∨ y % 400 = 0)
def yearLength (y : Int) : Int := if leap y then 366 else 365
def yearStart (y : Int) : Int := 365 * (y - 1) + (y - 1) / 4 - (y - 1) / 100 + (y - 1) / 400

theorem year_step (y : Int) : yearStart (y + 1) = yearStart y + yearLength y := by
  unfold yearStart yearLength leap
  split <;> simp_all <;> omega

theorem year_separation (a b : Int) (h : a < b) :
    yearStart a + yearLength a ≤ yearStart b := by
  rw [← year_step]
  unfold yearStart
  omega

def monthStart (l : Bool) (m : Fin 12) : Int :=
  (match m.val with
    | 0 => 0 | 1 => 31 | 2 => 59 | 3 => 90 | 4 => 120 | 5 => 151
    | 6 => 181 | 7 => 212 | 8 => 243 | 9 => 273 | 10 => 304 | _ => 334)
  + if l && decide (2 ≤ m.val) then 1 else 0

def monthLength (l : Bool) (m : Fin 12) : Int :=
  match m.val with
  | 1 => if l then 29 else 28
  | 3 | 5 | 8 | 10 => 30
  | _ => 31

theorem month_bounds : ∀ (l : Bool) (m : Fin 12),
    0 ≤ monthStart l m ∧ 1 ≤ monthLength l m ∧ monthLength l m ≤ 31 ∧
    monthStart l m + monthLength l m ≤ (if l then 366 else 365) := by decide

theorem month_separation : ∀ (l : Bool) (a b : Fin 12), a.val < b.val →
    monthStart l a + monthLength l a ≤ monthStart l b := by decide

structure Date where
  year : Int
  month : Fin 12
  day : Int

def Valid (d : Date) : Prop :=
  1 ≤ d.year ∧ d.year ≤ 9999 ∧ 1 ≤ d.day ∧ d.day ≤ monthLength (leap d.year) d.month

def ordinal (d : Date) : Int := yearStart d.year + monthStart (leap d.year) d.month + d.day - 1
def lexBefore (a b : Date) : Prop := a.year < b.year ∨
  (a.year = b.year ∧ (a.month.val < b.month.val ∨ (a.month.val = b.month.val ∧ a.day < b.day)))

theorem lex_implies_ordinal (a b : Date) (ha : Valid a) (hb : Valid b)
    (h : lexBefore a b) : ordinal a < ordinal b := by
  have ba := month_bounds (leap a.year) a.month
  have bb := month_bounds (leap b.year) b.month
  unfold Valid at ha hb
  unfold lexBefore at h
  unfold ordinal
  rcases h with hy | ⟨hy, hm | ⟨hm, hd⟩⟩
  · have sep := year_separation a.year b.year hy
    unfold yearLength at sep
    omega
  · have sep := month_separation (leap a.year) a.month b.month hm
    rw [hy] at sep ba ha
    rw [hy]
    omega
  · have me : a.month = b.month := Fin.ext hm
    rw [hy, me]
    omega

theorem ordinal_order (a b : Date) (ha : Valid a) (hb : Valid b) :
    ordinal a < ordinal b ↔ lexBefore a b := by
  constructor
  · intro h
    apply Classical.byContradiction
    intro hn
    by_cases he : a.year = b.year ∧ a.month.val = b.month.val ∧ a.day = b.day
    · rcases he with ⟨hy, hm, hd⟩
      have me : a.month = b.month := Fin.ext hm
      unfold ordinal at h
      rw [hy, me, hd] at h
      omega
    · have reverse : lexBefore b a := by unfold lexBefore at *; omega
      have opposite := lex_implies_ordinal b a hb ha reverse
      omega
  · exact lex_implies_ordinal a b ha hb

-- A bounded integer rank models fixed-width year/month/day comparison.
-- It is not an elapsed-day count; ordinal above is the elapsed-day count.
def rank (d : Date) : Int := d.year * 372 + (d.month.val : Int) * 31 + d.day

theorem rank_order (a b : Date) (ha : Valid a) (hb : Valid b) :
    rank a < rank b ↔ lexBefore a b := by
  have ba := month_bounds (leap a.year) a.month
  have bb := month_bounds (leap b.year) b.month
  have ma := a.month.isLt
  have mb := b.month.isLt
  unfold rank lexBefore Valid at *
  omega

theorem rank_ordinal_order (a b : Date) (ha : Valid a) (hb : Valid b) :
    rank a < rank b ↔ ordinal a < ordinal b := by
  rw [rank_order a b ha hb, ordinal_order a b ha hb]

#print axioms year_step
#print axioms ordinal_order
#print axioms rank_ordinal_order
end LegalMathGregorian
