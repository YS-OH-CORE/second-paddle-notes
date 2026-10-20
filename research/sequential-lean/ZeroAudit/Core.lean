import Mathlib

/-!
Finite adaptive-tree certification core. Every node may have a different
real-valued conditional distribution. No independence or fixed depth is assumed.
The tree is finite; an infinite-horizon measure-theoretic limit is not formalized.
-/
namespace ZeroAudit
open scoped BigOperators

inductive Tree where
  | leaf (value : ℝ)
  | node (value : ℝ) (weight : Fin 8 → ℝ) (child : Fin 8 → Tree)

def value : Tree → ℝ
  | .leaf w => w
  | .node w _ _ => w

/-- Nonnegative capital, probability branches, and a local supermartingale bound. -/
def Valid : Tree → Prop
  | .leaf w => 0 ≤ w
  | .node w p t =>
      0 ≤ w ∧ (∀ i, 0 ≤ p i) ∧ (∑ i, p i) = 1 ∧
      (∀ i, Valid (t i)) ∧ (∑ i, p i * value (t i)) ≤ w

/-- Probability of visiting capital >= B before the finite tree ends. -/
noncomputable def hitMass (B : ℝ) : Tree → ℝ
  | .leaf w => if B ≤ w then 1 else 0
  | .node w p t => if B ≤ w then 1 else ∑ i, p i * hitMass B (t i)

/-- Finite-tree Ville inequality, uniform over all finite adaptive trees. -/
theorem threshold_mul_hit_le (B : ℝ) (t : Tree) (ht : Valid t) :
    B * hitMass B t ≤ value t := by
  induction t with
  | leaf w =>
      change 0 ≤ w at ht
      by_cases hb : B ≤ w
      · simpa [hitMass, value, hb] using hb
      · simpa [hitMass, value, hb] using ht
  | node w p children ih =>
      rcases ht with ⟨hw, hp, hsum, hc, hs⟩
      by_cases hb : B ≤ w
      · simpa [hitMass, value, hb] using hb
      · simp only [hitMass, hb, ↓reduceIte, value]
        calc
          B * (∑ i, p i * hitMass B (children i)) =
              ∑ i, p i * (B * hitMass B (children i)) := by
                rw [Finset.mul_sum]
                apply Finset.sum_congr rfl
                intro i _
                ring
          _ ≤ ∑ i, p i * value (children i) :=
              Finset.sum_le_sum (fun i _ =>
                mul_le_mul_of_nonneg_left (ih i (hc i)) (hp i))
          _ ≤ w := hs

/-- Capital one and boundary twenty give a 5% bound at every finite horizon. -/
theorem anytime_five_percent (t : Tree) (ht : Valid t) (hroot : value t = 1) :
    hitMass 20 t ≤ (1 : ℝ) / 20 := by
  have h := threshold_mul_hit_le 20 t ht
  rw [hroot] at h
  linarith

/-- Multiplying a null-valid one-step score preserves the capital budget. -/
theorem multiplier_step (p e : Fin 8 → ℝ) (w : ℝ)
    (hw : 0 ≤ w) (hs : (∑ i, p i * e i) ≤ 1) :
    (∑ i, p i * (w * e i)) ≤ w := by
  calc
    (∑ i, p i * (w * e i)) = w * (∑ i, p i * e i) := by
      rw [Finset.mul_sum]
      apply Finset.sum_congr rfl
      intro i _
      ring
    _ ≤ w * 1 := mul_le_mul_of_nonneg_left hs hw
    _ = w := mul_one w

/-- One-step bounds extend to every real convex mixture of the supplied laws. -/
theorem mixture_support {J : Type*} [Fintype J]
    (q : J → Fin 8 → ℝ) (e : Fin 8 → ℝ) (a : J → ℝ)
    (ha : ∀ j, 0 ≤ a j) (hn : (∑ j, a j) = 1)
    (hq : ∀ j, (∑ i, q j i * e i) ≤ 1) :
    (∑ i, (∑ j, a j * q j i) * e i) ≤ 1 := by
  calc
    (∑ i, (∑ j, a j * q j i) * e i) =
        ∑ j, a j * (∑ i, q j i * e i) := by
          simp_rw [Finset.sum_mul]
          rw [Finset.sum_comm]
          apply Finset.sum_congr rfl
          intro j _
          rw [Finset.mul_sum]
          apply Finset.sum_congr rfl
          intro i _
          ring
    _ ≤ ∑ j, a j * 1 := Finset.sum_le_sum (fun j _ =>
        mul_le_mul_of_nonneg_left (hq j) (ha j))
    _ = 1 := by simpa using hn

/-- The same finite tree can represent a stopped log-capital process. -/
def DriftValid (I : ℝ) : Tree → Prop
  | .leaf _ => True
  | .node w p t =>
      (∀ i, 0 ≤ p i) ∧ (∑ i, p i) = 1 ∧
      (∀ i, DriftValid I (t i)) ∧ w + I ≤ ∑ i, p i * value (t i)

noncomputable def duration : Tree → ℝ
  | .leaf _ => 0
  | .node _ p t => 1 + ∑ i, p i * duration (t i)

noncomputable def terminalMean : Tree → ℝ
  | .leaf w => w
  | .node _ p t => ∑ i, p i * terminalMean (t i)

def TerminalBound (B : ℝ) : Tree → Prop
  | .leaf w => w ≤ B
  | .node _ _ t => ∀ i, TerminalBound B (t i)

/-- Stopped drift identity in inequality form. No integrability is assumed. -/
theorem drift_times_duration (I : ℝ) (t : Tree) (ht : DriftValid I t) :
    value t + I * duration t ≤ terminalMean t := by
  induction t with
  | leaf w => simp [value, duration, terminalMean]
  | node w p children ih =>
      rcases ht with ⟨hp, hn, hc, hs⟩
      have hc' : (∑ i, p i * (value (children i) + I * duration (children i))) ≤
          ∑ i, p i * terminalMean (children i) :=
        Finset.sum_le_sum (fun i _ =>
          mul_le_mul_of_nonneg_left (ih i (hc i)) (hp i))
      have heq : (∑ i, p i * (value (children i) + I * duration (children i))) =
          (∑ i, p i * value (children i)) + I * (∑ i, p i * duration (children i)) := by
        simp_rw [mul_add, Finset.sum_add_distrib]
        rw [Finset.mul_sum]
        congr 1
        apply Finset.sum_congr rfl
        intro i _
        ring
      rw [heq] at hc'
      simp only [value, duration, terminalMean]
      nlinarith

/-- Leaf caps also cap the terminal expectation. -/
theorem terminal_mean_le (I B : ℝ) (t : Tree)
    (ht : DriftValid I t) (hb : TerminalBound B t) : terminalMean t ≤ B := by
  induction t with
  | leaf w => exact hb
  | node w p children ih =>
      rcases ht with ⟨hp, hn, hc, hs⟩
      change (∑ i, p i * terminalMean (children i)) ≤ B
      calc
        (∑ i, p i * terminalMean (children i)) ≤ ∑ i, p i * B :=
          Finset.sum_le_sum (fun i _ =>
            mul_le_mul_of_nonneg_left (ih i (hc i) (hb i)) (hp i))
        _ = B := by rw [← Finset.sum_mul, hn, one_mul]

/-- For every truncation: drift * expected duration <= terminal cap - initial value. -/
theorem stopped_mean_numerator (I B : ℝ) (t : Tree)
    (ht : DriftValid I t) (hb : TerminalBound B t) :
    I * duration t ≤ B - value t := by
  have h1 := drift_times_duration I t ht
  have h2 := terminal_mean_le I B t ht hb
  linarith

end ZeroAudit

#print axioms ZeroAudit.threshold_mul_hit_le
#print axioms ZeroAudit.anytime_five_percent
#print axioms ZeroAudit.multiplier_step
#print axioms ZeroAudit.mixture_support
#print axioms ZeroAudit.drift_times_duration
#print axioms ZeroAudit.stopped_mean_numerator
