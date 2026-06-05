import Lake
open Lake DSL

package ai4math_lean_starter

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git"

@[default_target]
lean_lib Ai4Math
