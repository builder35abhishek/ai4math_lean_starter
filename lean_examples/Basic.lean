theorem nat_add_zero (n : Nat) : n + 0 = n := by
  simp

theorem nat_zero_add (n : Nat) : 0 + n = n := by
  simp

theorem and_comm_toy (P Q : Prop) : P ∧ Q -> Q ∧ P := by
  intro h
  exact And.intro h.right h.left

theorem imp_trans_toy (P Q R : Prop) : (P -> Q) -> (Q -> R) -> P -> R := by
  intro hpq hqr hp
  exact hqr (hpq hp)

theorem exists_self_eq (n : Nat) : ∃ m : Nat, m = n := by
  exact Exists.intro n rfl
