import ZeroAudit.Concrete

/-!
Connect the concrete score to arbitrary finite history-dependent mixtures and
stopping decisions. The finite process is constructed here; its capital
inequality is proved rather than supplied as an extra assumption.
-/
namespace ZeroAudit
open scoped BigOperators
set_option maxRecDepth 1000000
set_option maxHeartbeats 0

abbrev MixtureIndex := Plan × Bool
abbrev History := List (Fin 8)

noncomputable def mixLaw (a : MixtureIndex → ℝ) (i : Fin 8) : ℝ :=
  ∑ j, a j * nullLaw j.1 j.2 i

theorem point_nonneg (z i : Fin 8) : 0 ≤ pointMass z i := by
  unfold pointMass
  split_ifs <;> norm_num

theorem point_total (z : Fin 8) : (∑ i, pointMass z i) = 1 := by
  simp [pointMass]

theorem law_nonneg (p : Plan) (b : Bool) (i : Fin 8) : 0 ≤ nullLaw p b i := by
  have h7 := point_nonneg (output p 7) i
  have h6 := point_nonneg (output p 6) i
  have h5 := point_nonneg (output p 5) i
  have h3 := point_nonneg (output p 3) i
  cases b <;> simp only [nullLaw, Bool.false_eq_true, ↓reduceIte] <;> positivity

theorem law_total (p : Plan) (b : Bool) : (∑ i, nullLaw p b i) = 1 := by
  cases b <;>
    simp [nullLaw, ← Finset.sum_div, Finset.sum_add_distrib,
      ← Finset.mul_sum, point_total]

theorem mix_nonneg (a : MixtureIndex → ℝ) (ha : ∀ j, 0 ≤ a j) (i : Fin 8) :
    0 ≤ mixLaw a i :=
  Finset.sum_nonneg (fun j _ => mul_nonneg (ha j) (law_nonneg j.1 j.2 i))

theorem mix_total (a : MixtureIndex → ℝ) (hn : (∑ j, a j) = 1) :
    (∑ i, mixLaw a i) = 1 := by
  unfold mixLaw
  rw [Finset.sum_comm]
  simp_rw [← Finset.mul_sum, law_total, mul_one]
  exact hn

theorem multiplier_nonneg (i : Fin 8) : 0 ≤ multiplier i := by
  unfold multiplier
  positivity

noncomputable def processTree (a : History → MixtureIndex → ℝ)
    (stop : History → Bool) : ℕ → History → ℝ → Tree
  | 0, _, w => .leaf w
  | n + 1, history, w =>
      if stop history then .leaf w
      else .node w (mixLaw (a history))
        (fun i => processTree a stop n (history ++ [i]) (w * multiplier i))

theorem process_value (a : History → MixtureIndex → ℝ) (stop : History → Bool)
    (n : ℕ) (history : History) (w : ℝ) :
    value (processTree a stop n history w) = w := by
  cases n with
  | zero => rfl
  | succ n =>
      simp only [processTree]
      split_ifs <;> rfl

theorem process_valid (a : History → MixtureIndex → ℝ) (stop : History → Bool)
    (ha : ∀ h j, 0 ≤ a h j) (hn : ∀ h, (∑ j, a h j) = 1)
    (n : ℕ) (history : History) (w : ℝ) (hw : 0 ≤ w) :
    Valid (processTree a stop n history w) := by
  induction n generalizing history w with
  | zero => exact hw
  | succ n ih =>
      simp only [processTree]
      split_ifs
      · exact hw
      · refine ⟨hw, mix_nonneg _ (ha history), mix_total _ (hn history), ?_, ?_⟩
        · intro i
          exact ih (history ++ [i]) (w * multiplier i)
            (mul_nonneg hw (multiplier_nonneg i))
        · simp only [process_value]
          exact concrete_capital_step (a history) w (ha history) (hn history) hw

/-- No local capital assumption remains: it follows from the concrete score. -/
theorem concrete_five_percent (a : History → MixtureIndex → ℝ)
    (stop : History → Bool)
    (ha : ∀ h j, 0 ≤ a h j) (hn : ∀ h, (∑ j, a h j) = 1) (n : ℕ) :
    hitMass 20 (processTree a stop n [] 1) ≤ (1 : ℝ) / 20 := by
  exact anytime_five_percent _ (process_valid a stop ha hn n [] 1 (by norm_num))
    (process_value a stop n [] 1)

end ZeroAudit

#print axioms ZeroAudit.process_valid
#print axioms ZeroAudit.concrete_five_percent
