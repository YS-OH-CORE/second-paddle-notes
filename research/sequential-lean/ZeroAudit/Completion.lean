import ZeroAudit.Directions

/-! The first-alarm decision is total on alarms, and a replay law exposes the
importance of the conditional (not merely marginal) law contract. -/
namespace ZeroAudit
open scoped BigOperators ENNReal
open MeasureTheory Set
set_option maxRecDepth 1000000
set_option maxHeartbeats 0

theorem alarm_zero (e : Fin 8 → ℝ) (z : Fin 8) : alarm e z 0 = ∅ := by
  simp [alarm, hitWithin, occursBefore]

theorem some_alarm_iff (e : Fin 8 → ℝ) (z : Fin 8) (x : Stream) :
    (∃ n, x ∈ alarm e z n) ↔ x ∈ everHit e 20 ∪ occurs z := by
  constructor
  · rintro ⟨n, hh | ho⟩
    · exact Or.inl (Set.mem_iUnion.mpr ⟨n, hh⟩)
    · exact Or.inr (occursBefore_subset z n ho)
  · rintro (hh | ho)
    · obtain ⟨n, hn⟩ := Set.mem_iUnion.mp hh
      exact ⟨n, Or.inl hn⟩
    · obtain ⟨n, hn⟩ := (occurs_iff z x).mp ho
      exact ⟨n + 1, Or.inr (Set.mem_iUnion.mpr ⟨⟨n, Nat.lt_succ_self n⟩, hn⟩)⟩

theorem decision_union : acceptsSafe ∪ acceptsUnsafe =
    (everHit multiplier 20 ∪ occurs 0) ∪ (everHit reverseMultiplier 20 ∪ occurs 7) := by
  apply Set.Subset.antisymm
  · exact union_subset_union safeDecision_subset unsafeDecision_subset
  · intro x hx
    have hx' : ∃ n, x ∈ alarm multiplier 0 n ∨ x ∈ alarm reverseMultiplier 7 n := by
      rcases hx with hp | hm
      · obtain ⟨n, hn⟩ := (some_alarm_iff multiplier 0 x).mpr hp
        exact ⟨n, Or.inl hn⟩
      · obtain ⟨n, hn⟩ := (some_alarm_iff reverseMultiplier 7 x).mpr hm
        exact ⟨n, Or.inr hn⟩
    have hfirst := Nat.find_spec hx'
    have hzero : Nat.find hx' ≠ 0 := by
      intro hz
      rw [hz, alarm_zero, alarm_zero] at hfirst
      exact hfirst.elim (fun h => h) (fun h => h)
    obtain ⟨n, hn⟩ := Nat.exists_eq_succ_of_ne_zero hzero
    have hprev : ¬(x ∈ alarm multiplier 0 n ∨ x ∈ alarm reverseMultiplier 7 n) :=
      Nat.find_min hx' (by omega)
    rw [hn] at hfirst
    by_cases hp : x ∈ alarm multiplier 0 (n + 1)
    · exact Or.inl (Set.mem_iUnion.mpr ⟨n, hp, hprev⟩)
    · have hm : x ∈ alarm reverseMultiplier 7 (n + 1) := hfirst.resolve_left hp
      exact Or.inr (Set.mem_iUnion.mpr ⟨n, hm, fun h => h.elim hp (fun hm' => hprev (Or.inr hm'))⟩)

/-- Product update on a constant observed stream. -/
theorem capital_constant (e : Fin 8 → ℝ) (z : Fin 8) (n : ℕ) (w : ℝ) :
    capital e w (fun _ => z) n = w * (e z) ^ n := by
  induction n generalizing w with
  | zero => simp [capital]
  | succ n ih =>
      change capital e (w * e z) (fun _ => z) n = w * e z ^ (n + 1)
      rw [ih, pow_succ]
      ring

theorem constant_hits (e : Fin 8 → ℝ) (z : Fin 8) (n : ℕ)
    (hh : 20 ≤ e z ^ n) : (fun _ => z) ∈ everHit e 20 := by
  rw [everHit_eq]
  exact ⟨n, by simpa [capital_constant] using hh⟩

theorem constant_no_hit (e : Fin 8 → ℝ) (z : Fin 8)
    (h0 : 0 ≤ e z) (h1 : e z ≤ 1) : (fun _ => z) ∉ everHit e 20 := by
  rw [everHit_eq]
  rintro ⟨n, hn⟩
  have hb : e z ^ n ≤ 1 := pow_le_one₀ h0 h1
  simp only [capital_constant, one_mul, Set.mem_setOf_eq] at hn
  linarith

def middlePolicy : Plan :=
  (some (none, some (true, false)),
    some (some (true, false), some (false, false)))

noncomputable def replayLaw (i : Fin 8) : ℝ :=
  (pointMass 2 i + 2 * pointMass 4 i + 3 * pointMass 5 i) / 6

theorem replayLaw_legal (i : Fin 8) : replayLaw i = nullLaw (mirrorPlan middlePolicy) false i := by
  fin_cases i <;> norm_num [replayLaw, nullLaw, pointMass, middlePolicy,
    mirrorPlan, mirrorFirst, mirrorMiddle, output, choose, encode]

/-- One legal unsafe word is drawn once, then copied at every time. -/
noncomputable def replayMeasure : Measure Stream :=
  (1 / 6 : ℝ≥0∞) • Measure.dirac (fun _ => (2 : Fin 8)) +
  (1 / 3 : ℝ≥0∞) • Measure.dirac (fun _ => (4 : Fin 8)) +
  (1 / 2 : ℝ≥0∞) • Measure.dirac (fun _ => (5 : Fin 8))

instance replay_probability : IsProbabilityMeasure replayMeasure := by
  constructor
  simp [replayMeasure] <;> norm_num

/-- Every time has the same genuinely legal marginal, despite total dependence. -/
theorem replay_marginal (n : ℕ) (i : Fin 8) :
    replayMeasure {x | x n = i} = ENNReal.ofReal (nullLaw (mirrorPlan middlePolicy) false i) := by
  rw [← replayLaw_legal]
  fin_cases i <;>
    simp [replayMeasure, Measure.add_apply, Measure.smul_apply, Measure.dirac_apply,
      Set.indicator_apply, replayLaw, pointMass] <;>
    norm_num [ENNReal.ofReal_div_of_pos]

theorem replay_up_crosses (z : Fin 8) (hz : z = 2 ∨ z = 4) :
    (fun _ => z) ∈ everHit multiplier 20 := by
  apply constant_hits multiplier z 50
  have h : (107 : ℝ) / 100 ≤ multiplier z := by
    rcases hz with rfl | rfl <;> norm_num [multiplier, numerator, denominator]
  have hp := pow_le_pow_left₀ (by norm_num : (0 : ℝ) ≤ 107 / 100) h 50
  have hbig : (20 : ℝ) ≤ (107 / 100 : ℝ) ^ 50 := by norm_num
  exact hbig.trans hp

theorem replay_up_safe (z : Fin 8) (hz : z = 2 ∨ z = 4) :
    (fun _ => z) ∈ acceptsSafe := by
  have hh := replay_up_crosses z hz
  have hm : (fun _ => z) ∉ everHit reverseMultiplier 20 := by
    apply constant_no_hit
    · exact multiplier_nonneg _
    · rcases hz with rfl | rfl <;> norm_num [reverseMultiplier, reflect, multiplier, numerator, denominator]
  have ho : (fun _ => z) ∉ occurs 7 := by
    rw [occurs_iff]
    rcases hz with rfl | rfl <;> simp
  have hd : (fun _ => z) ∈ acceptsSafe ∪ acceptsUnsafe := by
    rw [decision_union]
    exact Or.inl (Or.inl hh)
  rcases hd with hs | hu
  · exact hs
  · exact False.elim ((unsafeDecision_subset hu).elim hm ho)

theorem replay_down_not_safe : (fun _ => (5 : Fin 8)) ∉ acceptsSafe := by
  have hh : (fun _ => (5 : Fin 8)) ∉ everHit multiplier 20 := by
    apply constant_no_hit
    · exact multiplier_nonneg _
    · norm_num [multiplier, numerator, denominator]
  have ho : (fun _ => (5 : Fin 8)) ∉ occurs 0 := by rw [occurs_iff]; simp
  intro hs
  exact (safeDecision_subset hs).elim hh ho

/-- Marginal validity alone permits a false-safe probability of exactly one half. -/
theorem replay_false_safe_half : replayMeasure acceptsSafe = (1 : ℝ≥0∞) / 2 := by
  have h2 := replay_up_safe 2 (Or.inl rfl)
  have h4 := replay_up_safe 4 (Or.inr rfl)
  have h5 := replay_down_not_safe
  simp [replayMeasure, Measure.add_apply, Measure.smul_apply, Measure.dirac_apply,
    Set.indicator_apply, h2, h4, h5] <;> norm_num

theorem replay_not_conditional : ¬ ∃ a : History → MixtureIndex → ℝ,
    (∀ h j, 0 ≤ a h j) ∧ (∀ h, (∑ j, a h j) = 1) ∧
    CylinderContract replayMeasure (fun h => mixLaw (a h)) := by
  rintro ⟨a, ha, hn, hc⟩
  have h := false_safe_le_five_percent replayMeasure a ha hn hc
  rw [replay_false_safe_half] at h
  norm_num at h

end ZeroAudit

#print axioms ZeroAudit.decision_union
#print axioms ZeroAudit.replayLaw_legal
#print axioms ZeroAudit.replay_probability
#print axioms ZeroAudit.replay_marginal
#print axioms ZeroAudit.replay_false_safe_half
#print axioms ZeroAudit.replay_not_conditional
