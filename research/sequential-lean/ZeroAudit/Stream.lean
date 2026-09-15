import ZeroAudit.Process

/-!
A measure-level bridge, not an assumed bound on hitting events.
The hypothesis specifies probabilities of one-step cylinder extensions.
The crossing probability is derived for all finite horizons and then for their
countable union on the standard measurable space of infinite observation streams.
-/
namespace ZeroAudit
open scoped BigOperators ENNReal
open MeasureTheory Set

abbrev Stream := ℕ → Fin 8

def tail (x : Stream) : Stream := fun n => x (n + 1)

def cylinder : History → Set Stream
  | [] => Set.univ
  | i :: h => {x | x 0 = i} ∩ tail ⁻¹' cylinder h

theorem measurable_tail : Measurable tail := by
  exact measurable_pi_lambda _ (fun i => measurable_pi_apply (i + 1))

theorem cylinder_measurable (h : History) : MeasurableSet (cylinder h) := by
  induction h with
  | nil => exact MeasurableSet.univ
  | cons i h ih =>
      exact (measurableSet_eq_fun (measurable_pi_apply 0) measurable_const).inter
        (ih.preimage measurable_tail)

theorem cylinder_append (h : History) (i : Fin 8) :
    cylinder (h ++ [i]) = cylinder h ∩ {x | x h.length = i} := by
  induction h with
  | nil => simp [cylinder]
  | cons j h ih =>
      ext x
      simp [cylinder, ih, tail, and_assoc]

theorem cylinder_children_disjoint (h : History) :
    Pairwise (fun i j : Fin 8 => Disjoint (cylinder (h ++ [i])) (cylinder (h ++ [j]))) := by
  intro i j hij
  apply Set.disjoint_left.mpr
  intro x hi hj
  rw [cylinder_append] at hi hj
  exact hij (hi.2.symm.trans hj.2)

/-- A quotient-free conditional-law contract. Null histories are harmless. -/
def CylinderContract (μ : Measure Stream) (p : History → Fin 8 → ℝ) : Prop :=
  ∀ h i, μ (cylinder (h ++ [i])) = μ (cylinder h) * ENNReal.ofReal (p h i)

noncomputable def scoreTree (e : Fin 8 → ℝ) (p : History → Fin 8 → ℝ) :
    ℕ → History → ℝ → Tree
  | 0, _, w => .leaf w
  | n + 1, h, w => .node w (p h)
      (fun i => scoreTree e p n (h ++ [i]) (w * e i))

theorem scoreTree_value (e : Fin 8 → ℝ) (p : History → Fin 8 → ℝ)
    (n : ℕ) (h : History) (w : ℝ) : value (scoreTree e p n h w) = w := by
  cases n <;> rfl

theorem scoreTree_valid (e : Fin 8 → ℝ) (p : History → Fin 8 → ℝ)
    (he : ∀ i, 0 ≤ e i) (hp : ∀ h i, 0 ≤ p h i)
    (hn : ∀ h, (∑ i, p h i) = 1)
    (hs : ∀ h, (∑ i, p h i * e i) ≤ 1)
    (n : ℕ) (h : History) (w : ℝ) (hw : 0 ≤ w) :
    Valid (scoreTree e p n h w) := by
  induction n generalizing h w with
  | zero => exact hw
  | succ n ih =>
      refine ⟨hw, hp h, hn h, ?_, ?_⟩
      · intro i
        exact ih (h ++ [i]) (w * e i) (mul_nonneg hw (he i))
      · simp only [scoreTree_value]
        exact multiplier_step (p h) e w hw (hs h)

theorem hitMass_nonneg (B : ℝ) (t : Tree) (ht : Valid t) : 0 ≤ hitMass B t := by
  induction t with
  | leaf w => simp only [hitMass]; split_ifs <;> norm_num
  | node w p children ih =>
      rcases ht with ⟨hw, hp, hn, hc, hs⟩
      simp only [hitMass]
      split_ifs
      · norm_num
      · exact Finset.sum_nonneg (fun i _ => mul_nonneg (hp i) (ih i (hc i)))

/-- Event of crossing by n further observations, inside a specified prefix. -/
noncomputable def hitWithin (e : Fin 8 → ℝ) (B : ℝ) :
    ℕ → History → ℝ → Set Stream
  | 0, h, w => if B ≤ w then cylinder h else ∅
  | n + 1, h, w => if B ≤ w then cylinder h
      else ⋃ i : Fin 8, hitWithin e B n (h ++ [i]) (w * e i)

theorem hitWithin_measurable (e : Fin 8 → ℝ) (B : ℝ)
    (n : ℕ) (h : History) (w : ℝ) : MeasurableSet (hitWithin e B n h w) := by
  induction n generalizing h w with
  | zero => simp only [hitWithin]; split_ifs; exact cylinder_measurable h; exact MeasurableSet.empty
  | succ n ih =>
      simp only [hitWithin]
      split_ifs
      · exact cylinder_measurable h
      · exact MeasurableSet.iUnion (fun i => ih (h ++ [i]) (w * e i))

theorem hitWithin_subset (e : Fin 8 → ℝ) (B : ℝ)
    (n : ℕ) (h : History) (w : ℝ) : hitWithin e B n h w ⊆ cylinder h := by
  induction n generalizing h w with
  | zero => simp only [hitWithin]; split_ifs; exact Subset.rfl; exact empty_subset _
  | succ n ih =>
      simp only [hitWithin]
      split_ifs
      · exact Subset.rfl
      · apply iUnion_subset
        intro i
        exact (ih (h ++ [i]) (w * e i)).trans (by rw [cylinder_append]; exact inter_subset_left)

theorem hitWithin_mono (e : Fin 8 → ℝ) (B : ℝ) (h : History) (w : ℝ) :
    Monotone (fun n => hitWithin e B n h w) := by
  apply monotone_nat_of_le_succ
  intro n
  induction n generalizing h w with
  | zero =>
      simp only [hitWithin]
      split_ifs
      · exact Subset.rfl
      · exact empty_subset _
  | succ n ih =>
      simp only [hitWithin]
      split_ifs
      · exact Subset.rfl
      · exact iUnion_mono (fun i => ih (h ++ [i]) (w * e i))

/-- The tree mass is proved equal to the measure of the actual cylinder event. -/
theorem measure_hitWithin (μ : Measure Stream) (e : Fin 8 → ℝ)
    (p : History → Fin 8 → ℝ)
    (he : ∀ i, 0 ≤ e i) (hp : ∀ h i, 0 ≤ p h i)
    (hn : ∀ h, (∑ i, p h i) = 1)
    (hs : ∀ h, (∑ i, p h i * e i) ≤ 1)
    (hc : CylinderContract μ p) (B : ℝ) (n : ℕ) (h : History) (w : ℝ)
    (hw : 0 ≤ w) :
    μ (hitWithin e B n h w) =
      μ (cylinder h) * ENNReal.ofReal (hitMass B (scoreTree e p n h w)) := by
  induction n generalizing h w with
  | zero =>
      by_cases hb : B ≤ w <;> simp [hitWithin, scoreTree, hitMass, hb]
  | succ n ih =>
      by_cases hb : B ≤ w
      · simp [hitWithin, scoreTree, hitMass, hb]
      · have hd : Pairwise (fun i j : Fin 8 =>
            Disjoint (hitWithin e B n (h ++ [i]) (w * e i))
              (hitWithin e B n (h ++ [j]) (w * e j))) := by
          intro i j hij
          exact (cylinder_children_disjoint h hij).mono
            (hitWithin_subset e B n (h ++ [i]) (w * e i))
            (hitWithin_subset e B n (h ++ [j]) (w * e j))
        simp only [hitWithin, hb, ↓reduceIte, scoreTree, hitMass]
        rw [measure_iUnion hd (fun i => hitWithin_measurable e B n (h ++ [i]) (w * e i)),
          tsum_fintype]
        calc
          (∑ i, μ (hitWithin e B n (h ++ [i]) (w * e i))) =
              ∑ i, (μ (cylinder h) * ENNReal.ofReal (p h i)) *
                ENNReal.ofReal (hitMass B (scoreTree e p n (h ++ [i]) (w * e i))) := by
                  apply Finset.sum_congr rfl
                  intro i _
                  rw [ih (h ++ [i]) (w * e i) (mul_nonneg hw (he i)), hc h i]
          _ = μ (cylinder h) * ENNReal.ofReal
              (∑ i, p h i * hitMass B (scoreTree e p n (h ++ [i]) (w * e i))) := by
                rw [ENNReal.ofReal_sum_of_nonneg (fun i _ =>
                  mul_nonneg (hp h i) (hitMass_nonneg B _
                    (scoreTree_valid e p he hp hn hs n (h ++ [i]) (w * e i)
                      (mul_nonneg hw (he i)))))]
                simp_rw [ENNReal.ofReal_mul (hp h _)]
                rw [Finset.mul_sum]
                apply Finset.sum_congr rfl
                intro i _
                exact mul_assoc _ _ _

noncomputable def capital (e : Fin 8 → ℝ) : ℝ → Stream → ℕ → ℝ
  | w, _, 0 => w
  | w, x, n + 1 => capital e (w * e (x 0)) (tail x) n

theorem suffix_append (x : Stream) (h : History) (i : Fin 8) :
    (fun j => x ((h ++ [i]).length + j)) = tail (fun j => x (h.length + j)) := by
  funext j
  simp only [List.length_append, List.length_singleton, tail]
  congr 1
  omega

/-- The recursive event really is a product-capital crossing on the stream. -/
theorem mem_hitWithin (e : Fin 8 → ℝ) (B : ℝ) (n : ℕ)
    (h : History) (w : ℝ) (x : Stream) :
    x ∈ hitWithin e B n h w ↔
      x ∈ cylinder h ∧ ∃ k ≤ n,
        B ≤ capital e w (fun j => x (h.length + j)) k := by
  induction n generalizing h w with
  | zero => simp [hitWithin, capital, and_comm]
  | succ n ih =>
      by_cases hb : B ≤ w
      · simp only [hitWithin, hb, ↓reduceIte]
        constructor
        · intro hh
          exact ⟨hh, 0, Nat.zero_le _, hb⟩
        · exact fun hx => hx.1
      · simp only [hitWithin, hb, ↓reduceIte, Set.mem_iUnion]
        constructor
        · rintro ⟨i, hi⟩
          obtain ⟨hci, k, hkn, hk⟩ := (ih (h ++ [i]) (w * e i)).mp hi
          rw [cylinder_append] at hci
          refine ⟨hci.1, k + 1, Nat.succ_le_succ hkn, ?_⟩
          rw [suffix_append] at hk
          change B ≤ capital e (w * e (x (h.length + 0)))
            (tail (fun j => x (h.length + j))) k
          simpa only [Nat.add_zero, hci.2] using hk
        · rintro ⟨hh, k, hkn, hk⟩
          cases k with
          | zero => exact False.elim (hb hk)
          | succ k =>
              refine ⟨x h.length, (ih (h ++ [x h.length]) (w * e (x h.length))).mpr ?_⟩
              refine ⟨?_, k, Nat.le_of_succ_le_succ hkn, ?_⟩
              · rw [cylinder_append]
                exact ⟨hh, rfl⟩
              · rw [suffix_append]
                simpa only [capital, Nat.add_zero] using hk

noncomputable def everHit (e : Fin 8 → ℝ) (B : ℝ) : Set Stream :=
  ⋃ n : ℕ, hitWithin e B n [] 1

theorem everHit_measurable (e : Fin 8 → ℝ) (B : ℝ) : MeasurableSet (everHit e B) :=
  MeasurableSet.iUnion (fun n => hitWithin_measurable e B n [] 1)

theorem everHit_eq (e : Fin 8 → ℝ) (B : ℝ) :
    everHit e B = {x | ∃ n : ℕ, B ≤ capital e 1 x n} := by
  ext x
  simp only [everHit, Set.mem_iUnion, mem_hitWithin, cylinder, Set.mem_univ,
    List.length_nil, zero_add, true_and, Set.mem_setOf_eq]
  constructor
  · rintro ⟨n, k, hkn, hk⟩
    exact ⟨k, hk⟩
  · rintro ⟨k, hk⟩
    exact ⟨k, k, le_rfl, hk⟩

/-- Measure-theoretic any-time bound; no finite hitting bound is assumed. -/
theorem stream_five_percent (μ : Measure Stream) [IsProbabilityMeasure μ]
    (e : Fin 8 → ℝ) (p : History → Fin 8 → ℝ)
    (he : ∀ i, 0 ≤ e i) (hp : ∀ h i, 0 ≤ p h i)
    (hn : ∀ h, (∑ i, p h i) = 1)
    (hs : ∀ h, (∑ i, p h i * e i) ≤ 1)
    (hc : CylinderContract μ p) :
    μ (everHit e 20) ≤ (1 : ℝ≥0∞) / 20 := by
  rw [everHit, (hitWithin_mono e 20 [] 1).measure_iUnion]
  apply iSup_le
  intro n
  rw [measure_hitWithin μ e p he hp hn hs hc 20 n [] 1 (by norm_num)]
  simp only [cylinder, measure_univ, one_mul]
  have ht := anytime_five_percent (scoreTree e p n [] 1)
    (scoreTree_valid e p he hp hn hs n [] 1 (by norm_num))
    (scoreTree_value e p n [] 1)
  calc
    ENNReal.ofReal (hitMass 20 (scoreTree e p n [] 1)) ≤ ENNReal.ofReal ((1 : ℝ) / 20) :=
      ENNReal.ofReal_le_ofReal ht
    _ = (1 : ℝ≥0∞) / 20 := by
      rw [ENNReal.ofReal_div_of_pos (by norm_num : (0 : ℝ) < 20)]
      norm_num

end ZeroAudit

#print axioms ZeroAudit.measure_hitWithin
#print axioms ZeroAudit.mem_hitWithin
#print axioms ZeroAudit.everHit_eq
#print axioms ZeroAudit.stream_five_percent
