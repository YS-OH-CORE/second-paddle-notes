import ZeroAudit.Core
import Mathlib.Data.Fintype.Option
import Mathlib.Data.Fin.VecNotation
import Mathlib.Tactic.NormNum

/-!
An explicit finite current-prefix, at-most-one-flip reader. `none` flips the
current bit; `some` waits and chooses a subtree after the next true bit. At the
last bit a Boolean decides whether to flip. Thus there are 26 * 26 policies.
The bound below is evaluated by kernel reduction, not native evaluation.
-/
namespace ZeroAudit
open scoped BigOperators

abbrev LastPlan := Bool
abbrev MiddlePlan := Option (LastPlan × LastPlan)
abbrev FirstPlan := Option (MiddlePlan × MiddlePlan)
abbrev Plan := FirstPlan × FirstPlan

def choose {α : Type} (p : α × α) (b : Bool) : α := if b then p.2 else p.1

def encode (a b c : Bool) : Fin 8 :=
  ⟨(if a then 4 else 0) + (if b then 2 else 0) + (if c then 1 else 0), by
    cases a <;> cases b <;> cases c <;> decide⟩

def output (p : Plan) (x : Fin 8) : Fin 8 :=
  let a := x.val / 4 == 1
  let b := x.val / 2 % 2 == 1
  let c := x.val % 2 == 1
  match choose p a with
  | none => encode (!a) b c
  | some next =>
    match choose next b with
    | none => encode a (!b) c
    | some last => encode a b (if choose last c then !c else c)

def denominator : ℕ := 3000000000000000001

def numerator : Fin 8 → ℕ :=
  ![3150000000000000000, 3122440433388473574, 3237690510647816286,
    2800726181771964618, 3213631576243997040, 2778348778954729878,
    2887169478277046670, 0]

def multiplier (i : Fin 8) : ℝ := (numerator i : ℝ) / denominator

def unsafeCost (p : Plan) (extreme : Bool) : ℕ :=
  if extreme then 6 * numerator (output p 7)
  else 3 * numerator (output p 7) + numerator (output p 6) +
       numerator (output p 5) + numerator (output p 3)

set_option maxRecDepth 1000000 in
set_option maxHeartbeats 0 in
theorem all_causal_integer_bounds :
    ∀ (p : Plan) (extreme : Bool), unsafeCost p extreme ≤ 6 * denominator := by
  decide +kernel

theorem policy_count : Fintype.card Plan = 676 := by decide +kernel

def pointMass (z i : Fin 8) : ℝ := if i = z then 1 else 0

def nullLaw (p : Plan) (extreme : Bool) (i : Fin 8) : ℝ :=
  if extreme then pointMass (output p 7) i
  else (3 * pointMass (output p 7) i + pointMass (output p 6) i +
        pointMass (output p 5) i + pointMass (output p 3) i) / 6

theorem point_mean (z : Fin 8) (e : Fin 8 → ℝ) :
    (∑ i, pointMass z i * e i) = e z := by
  simp [pointMass]

theorem null_expectation (p : Plan) (extreme : Bool) :
    (∑ i, nullLaw p extreme i * multiplier i) =
      (unsafeCost p extreme : ℝ) / (6 * denominator) := by
  cases extreme with
  | false =>
    simp only [nullLaw, Bool.false_eq_true, ↓reduceIte, unsafeCost]
    calc
      (∑ i, (3 * pointMass (output p 7) i + pointMass (output p 6) i +
        pointMass (output p 5) i + pointMass (output p 3) i) / 6 * multiplier i) =
        (3 * multiplier (output p 7) + multiplier (output p 6) +
         multiplier (output p 5) + multiplier (output p 3)) / 6 := by
          simp_rw [div_mul_eq_mul_div, add_mul, Finset.sum_div,
            Finset.sum_add_distrib, mul_assoc, ← Finset.mul_sum]
          rw [point_mean, point_mean, point_mean, point_mean]
      _ = _ := by push_cast; unfold multiplier; ring
  | true =>
      simp only [nullLaw, ↓reduceIte, unsafeCost, point_mean]
      push_cast
      unfold multiplier
      ring

theorem every_policy_support (p : Plan) (extreme : Bool) :
    (∑ i, nullLaw p extreme i * multiplier i) ≤ 1 := by
  rw [null_expectation]
  have hb : (unsafeCost p extreme : ℝ) ≤ 6 * (denominator : ℝ) := by
    exact_mod_cast all_causal_integer_bounds p extreme
  apply (div_le_iff₀ (by norm_num [denominator] : (0 : ℝ) < 6 * denominator)).2
  simpa using hb

/-- Arbitrary real randomization of every causal policy and either unsafe count. -/
theorem concrete_mixture_support (a : (Plan × Bool) → ℝ)
    (ha : ∀ j, 0 ≤ a j) (hn : (∑ j, a j) = 1) :
    (∑ i, (∑ j, a j * nullLaw j.1 j.2 i) * multiplier i) ≤ 1 := by
  exact mixture_support (fun j => nullLaw j.1 j.2) multiplier a ha hn
    (fun j => every_policy_support j.1 j.2)

/-- This is the local capital inequality needed at every adaptive node. -/
theorem concrete_capital_step (a : (Plan × Bool) → ℝ) (w : ℝ)
    (ha : ∀ j, 0 ≤ a j) (hn : (∑ j, a j) = 1) (hw : 0 ≤ w) :
    (∑ i, (∑ j, a j * nullLaw j.1 j.2 i) * (w * multiplier i)) ≤ w := by
  exact multiplier_step _ _ w hw (concrete_mixture_support a ha hn)

end ZeroAudit

#print axioms ZeroAudit.all_causal_integer_bounds
#print axioms ZeroAudit.policy_count
#print axioms ZeroAudit.every_policy_support
#print axioms ZeroAudit.concrete_mixture_support
#print axioms ZeroAudit.concrete_capital_step
