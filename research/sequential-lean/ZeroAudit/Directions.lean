import ZeroAudit.Stream

/-! Both concrete directions, impossible outputs, and the first-alarm decision. -/
namespace ZeroAudit
open scoped BigOperators ENNReal
open MeasureTheory Set
set_option maxRecDepth 1000000
set_option maxHeartbeats 0

def reflect (i : Fin 8) : Fin 8 := ⟨7 - i.val, by omega⟩

theorem reflect_twice (i : Fin 8) : reflect (reflect i) = i := by
  apply Fin.ext
  simp only [reflect]
  omega

def reflection : Fin 8 ≃ Fin 8 where
  toFun := reflect
  invFun := reflect
  left_inv := reflect_twice
  right_inv := reflect_twice

theorem reflect_eq_iff (i j : Fin 8) : reflect i = reflect j ↔ i = j := by
  constructor
  · intro h
    have hh := congrArg reflect h
    simpa only [reflect_twice] using hh
  · exact congrArg reflect

def mirrorMiddle : MiddlePlan → MiddlePlan
  | none => none
  | some (l, r) => some (r, l)

def mirrorFirst : FirstPlan → FirstPlan
  | none => none
  | some (l, r) => some (mirrorMiddle r, mirrorMiddle l)

def mirrorPlan (p : Plan) : Plan := (mirrorFirst p.2, mirrorFirst p.1)

theorem mirror_output : ∀ (p : Plan) (x : Fin 8),
    output (mirrorPlan p) x = reflect (output p (reflect x)) := by
  decide +kernel

theorem point_reflect (z i : Fin 8) : pointMass (reflect z) (reflect i) = pointMass z i := by
  simp [pointMass, reflect_eq_iff]

/-- Direct safe input law, rather than a label attached to the unsafe theorem. -/
noncomputable def safeLaw (p : Plan) (extreme : Bool) (i : Fin 8) : ℝ :=
  if extreme then pointMass (output p 0) i
  else (3 * pointMass (output p 0) i + pointMass (output p 1) i +
    pointMass (output p 2) i + pointMass (output p 4) i) / 6

theorem safeLaw_reflect (p : Plan) (b : Bool) (i : Fin 8) :
    safeLaw p b i = nullLaw (mirrorPlan p) b (reflect i) := by
  cases b <;> simp only [safeLaw, nullLaw, Bool.false_eq_true, ↓reduceIte,
    mirror_output, show reflect (7 : Fin 8) = 0 from rfl,
    show reflect (6 : Fin 8) = 1 from rfl,
    show reflect (5 : Fin 8) = 2 from rfl,
    show reflect (3 : Fin 8) = 4 from rfl, point_reflect]

noncomputable def reverseMultiplier (i : Fin 8) : ℝ := multiplier (reflect i)

theorem safeLaw_support (p : Plan) (b : Bool) :
    (∑ i, safeLaw p b i * reverseMultiplier i) ≤ 1 := by
  simp only [safeLaw_reflect, reverseMultiplier]
  have heq := reflection.sum_comp (fun i => nullLaw (mirrorPlan p) b i * multiplier i)
  change (∑ i, nullLaw (mirrorPlan p) b (reflect i) * multiplier (reflect i)) = _ at heq
  rw [heq]
  exact every_policy_support (mirrorPlan p) b

theorem safeLaw_nonneg (p : Plan) (b : Bool) (i : Fin 8) : 0 ≤ safeLaw p b i := by
  rw [safeLaw_reflect]
  exact law_nonneg _ _ _

theorem safeLaw_total (p : Plan) (b : Bool) : (∑ i, safeLaw p b i) = 1 := by
  simp only [safeLaw_reflect]
  have heq := reflection.sum_comp (nullLaw (mirrorPlan p) b)
  change (∑ i, nullLaw (mirrorPlan p) b (reflect i)) = _ at heq
  rw [heq]
  exact law_total _ _

noncomputable def safeMixLaw (a : MixtureIndex → ℝ) (i : Fin 8) : ℝ :=
  ∑ j, a j * safeLaw j.1 j.2 i

theorem safeMix_nonneg (a : MixtureIndex → ℝ) (ha : ∀ j, 0 ≤ a j) (i : Fin 8) :
    0 ≤ safeMixLaw a i :=
  Finset.sum_nonneg (fun j _ => mul_nonneg (ha j) (safeLaw_nonneg _ _ _))

theorem safeMix_total (a : MixtureIndex → ℝ) (hn : (∑ j, a j) = 1) :
    (∑ i, safeMixLaw a i) = 1 := by
  unfold safeMixLaw
  rw [Finset.sum_comm]
  simp_rw [← Finset.mul_sum, safeLaw_total, mul_one]
  exact hn

theorem safeMix_support (a : MixtureIndex → ℝ)
    (ha : ∀ j, 0 ≤ a j) (hn : (∑ j, a j) = 1) :
    (∑ i, safeMixLaw a i * reverseMultiplier i) ≤ 1 :=
  mixture_support (J := MixtureIndex) (fun j => safeLaw j.1 j.2) reverseMultiplier
    a ha hn (fun j => safeLaw_support j.1 j.2)

theorem concrete_stream_five_percent (μ : Measure Stream) [IsProbabilityMeasure μ]
    (a : History → MixtureIndex → ℝ)
    (ha : ∀ h j, 0 ≤ a h j) (hn : ∀ h, (∑ j, a h j) = 1)
    (hc : CylinderContract μ (fun h => mixLaw (a h))) :
    μ (everHit multiplier 20) ≤ (1 : ℝ≥0∞) / 20 := by
  exact stream_five_percent μ multiplier (fun h => mixLaw (a h)) multiplier_nonneg
    (fun h => mix_nonneg _ (ha h)) (fun h => mix_total _ (hn h))
    (fun h => concrete_mixture_support (a h) (ha h) (hn h)) hc

theorem reflected_stream_five_percent (μ : Measure Stream) [IsProbabilityMeasure μ]
    (a : History → MixtureIndex → ℝ)
    (ha : ∀ h j, 0 ≤ a h j) (hn : ∀ h, (∑ j, a h j) = 1)
    (hc : CylinderContract μ (fun h => safeMixLaw (a h))) :
    μ (everHit reverseMultiplier 20) ≤ (1 : ℝ≥0∞) / 20 := by
  exact stream_five_percent μ reverseMultiplier (fun h => safeMixLaw (a h))
    (fun i => multiplier_nonneg (reflect i))
    (fun h => safeMix_nonneg _ (ha h)) (fun h => safeMix_total _ (hn h))
    (fun h => safeMix_support (a h) (ha h) (hn h)) hc

/-- These finite checks concern actual possible outputs, not an imported list. -/
theorem no_unsafe_zero : ∀ p : Plan,
    output p 7 ≠ 0 ∧ output p 6 ≠ 0 ∧ output p 5 ≠ 0 ∧ output p 3 ≠ 0 := by
  decide +kernel

theorem null_zero (p : Plan) (b : Bool) : nullLaw p b 0 = 0 := by
  obtain ⟨h7, h6, h5, h3⟩ := no_unsafe_zero p
  cases b <;> simp [nullLaw, pointMass, eq_comm, h7, h6, h5, h3]

theorem safe_seven (p : Plan) (b : Bool) : safeLaw p b 7 = 0 := by
  rw [safeLaw_reflect]
  exact null_zero _ _

noncomputable def occurs (z : Fin 8) : Set Stream := ⋃ h : History, cylinder (h ++ [z])

theorem occurs_zero_measure (μ : Measure Stream) (p : History → Fin 8 → ℝ)
    (hc : CylinderContract μ p) (z : Fin 8) (hz : ∀ h, p h z = 0) :
    μ (occurs z) = 0 := by
  apply measure_iUnion_null
  intro h
  rw [hc h z, hz h, ENNReal.ofReal_zero, mul_zero]

def prefix (x : Stream) : ℕ → History
  | 0 => []
  | n + 1 => prefix x n ++ [x n]

theorem prefix_length (x : Stream) (n : ℕ) : (prefix x n).length = n := by
  induction n with
  | zero => rfl
  | succ n ih => simp [prefix, ih]

theorem mem_prefix (x : Stream) (n : ℕ) : x ∈ cylinder (prefix x n) := by
  induction n with
  | zero => trivial
  | succ n ih =>
      rw [prefix, cylinder_append, prefix_length]
      exact ⟨ih, rfl⟩

theorem occurs_iff (z : Fin 8) (x : Stream) : x ∈ occurs z ↔ ∃ n, x n = z := by
  constructor
  · intro hx
    obtain ⟨h, hh⟩ := Set.mem_iUnion.mp hx
    rw [cylinder_append] at hh
    exact ⟨h.length, hh.2⟩
  · rintro ⟨n, hn⟩
    apply Set.mem_iUnion.mpr
    refine ⟨prefix x n, ?_⟩
    rw [cylinder_append, prefix_length]
    exact ⟨mem_prefix x n, hn⟩

noncomputable def occursBefore (z : Fin 8) (n : ℕ) : Set Stream :=
  ⋃ j : Fin n, {x | x j = z}

theorem occursBefore_measurable (z : Fin 8) (n : ℕ) : MeasurableSet (occursBefore z n) :=
  MeasurableSet.iUnion (fun j => measurableSet_eq_fun (measurable_pi_apply (j : ℕ)) measurable_const)

theorem occursBefore_mono (z : Fin 8) : Monotone (occursBefore z) := by
  intro m n hmn x hx
  obtain ⟨j, hj⟩ := Set.mem_iUnion.mp hx
  exact Set.mem_iUnion.mpr ⟨⟨j.val, lt_of_lt_of_le j.isLt hmn⟩, hj⟩

theorem occursBefore_subset (z : Fin 8) (n : ℕ) : occursBefore z n ⊆ occurs z := by
  intro x hx
  obtain ⟨j, hj⟩ := Set.mem_iUnion.mp hx
  exact (occurs_iff z x).mpr ⟨j.val, hj⟩

noncomputable def alarm (e : Fin 8 → ℝ) (z : Fin 8) (n : ℕ) : Set Stream :=
  hitWithin e 20 n [] 1 ∪ occursBefore z n

theorem alarm_measurable (e : Fin 8 → ℝ) (z : Fin 8) (n : ℕ) :
    MeasurableSet (alarm e z n) :=
  (hitWithin_measurable e 20 n [] 1).union (occursBefore_measurable z n)

theorem alarm_mono (e : Fin 8 → ℝ) (z : Fin 8) : Monotone (alarm e z) :=
  fun _ _ h => union_subset_union (hitWithin_mono e 20 [] 1 h) (occursBefore_mono z h)

noncomputable def acceptsSafe : Set Stream := ⋃ n : ℕ,
  alarm multiplier 0 (n + 1) \ (alarm multiplier 0 n ∪ alarm reverseMultiplier 7 n)

noncomputable def acceptsUnsafe : Set Stream := ⋃ n : ℕ,
  alarm reverseMultiplier 7 (n + 1) \
    (alarm multiplier 0 (n + 1) ∪ alarm reverseMultiplier 7 n)

theorem decisions_measurable : MeasurableSet acceptsSafe ∧ MeasurableSet acceptsUnsafe := by
  constructor <;> apply MeasurableSet.iUnion <;> intro n
  · exact (alarm_measurable _ _ _).diff ((alarm_measurable _ _ _).union (alarm_measurable _ _ _))
  · exact (alarm_measurable _ _ _).diff ((alarm_measurable _ _ _).union (alarm_measurable _ _ _))

theorem decisions_disjoint : Disjoint acceptsSafe acceptsUnsafe := by
  apply Set.disjoint_left.mpr
  intro x hx hy
  obtain ⟨n, hn⟩ := Set.mem_iUnion.mp hx
  obtain ⟨m, hm⟩ := Set.mem_iUnion.mp hy
  rcases le_or_gt n m with hnm | hnm
  · exact hm.2 (Or.inl (alarm_mono multiplier 0 (Nat.succ_le_succ hnm) hn.1))
  · exact hn.2 (Or.inr (alarm_mono reverseMultiplier 7 hnm hm.1))

theorem safeDecision_subset : acceptsSafe ⊆ everHit multiplier 20 ∪ occurs 0 := by
  intro x hx
  obtain ⟨n, hn⟩ := Set.mem_iUnion.mp hx
  rcases hn.1 with hh | ho
  · exact Or.inl (Set.mem_iUnion.mpr ⟨n + 1, hh⟩)
  · exact Or.inr (occursBefore_subset 0 (n + 1) ho)

theorem unsafeDecision_subset : acceptsUnsafe ⊆ everHit reverseMultiplier 20 ∪ occurs 7 := by
  intro x hx
  obtain ⟨n, hn⟩ := Set.mem_iUnion.mp hx
  rcases hn.1 with hh | ho
  · exact Or.inl (Set.mem_iUnion.mpr ⟨n + 1, hh⟩)
  · exact Or.inr (occursBefore_subset 7 (n + 1) ho)

theorem false_safe_le_five_percent (μ : Measure Stream) [IsProbabilityMeasure μ]
    (a : History → MixtureIndex → ℝ)
    (ha : ∀ h j, 0 ≤ a h j) (hn : ∀ h, (∑ j, a h j) = 1)
    (hc : CylinderContract μ (fun h => mixLaw (a h))) :
    μ acceptsSafe ≤ (1 : ℝ≥0∞) / 20 := by
  have hz : μ (occurs 0) = 0 := occurs_zero_measure μ _ hc 0 (by
    intro h; simp [mixLaw, null_zero])
  calc
    μ acceptsSafe ≤ μ (everHit multiplier 20 ∪ occurs 0) := measure_mono safeDecision_subset
    _ ≤ μ (everHit multiplier 20) + μ (occurs 0) := measure_union_le _ _
    _ ≤ (1 : ℝ≥0∞) / 20 := by
      rw [hz, add_zero]
      exact concrete_stream_five_percent μ a ha hn hc

theorem false_unsafe_le_five_percent (μ : Measure Stream) [IsProbabilityMeasure μ]
    (a : History → MixtureIndex → ℝ)
    (ha : ∀ h j, 0 ≤ a h j) (hn : ∀ h, (∑ j, a h j) = 1)
    (hc : CylinderContract μ (fun h => safeMixLaw (a h))) :
    μ acceptsUnsafe ≤ (1 : ℝ≥0∞) / 20 := by
  have hz : μ (occurs 7) = 0 := occurs_zero_measure μ _ hc 7 (by
    intro h; simp [safeMixLaw, safe_seven])
  calc
    μ acceptsUnsafe ≤ μ (everHit reverseMultiplier 20 ∪ occurs 7) := measure_mono unsafeDecision_subset
    _ ≤ μ (everHit reverseMultiplier 20) + μ (occurs 7) := measure_union_le _ _
    _ ≤ (1 : ℝ≥0∞) / 20 := by
      rw [hz, add_zero]
      exact reflected_stream_five_percent μ a ha hn hc

end ZeroAudit

#print axioms ZeroAudit.mirror_output
#print axioms ZeroAudit.safeLaw_reflect
#print axioms ZeroAudit.concrete_stream_five_percent
#print axioms ZeroAudit.reflected_stream_five_percent
#print axioms ZeroAudit.occurs_iff
#print axioms ZeroAudit.decisions_disjoint
#print axioms ZeroAudit.false_safe_le_five_percent
#print axioms ZeroAudit.false_unsafe_le_five_percent
