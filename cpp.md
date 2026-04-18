# C++ Code Style

Conventions specific to C++ projects. This file is not loaded by default — project-level CLAUDE.md files in C++ repos should pull it in via `@~/.claude/cpp.md` (or an equivalent relative path).

The general code style rules in `~/.claude/CLAUDE.md` still apply; the rules below are additions specific to C++.

## Prefer using `const` wherever it can be used.

The rationale for prefering `const` is that it's generally easier to reason about a `const` that it is to reason about a variable. When you change a variable after initialization, you need to remember to consider every usage of the variable after that point to check if those usages are still correct with the new value. With a `const` the compiler will force you to consider that, and you might conclude that you should introduce a new `const` to name the new value.

Consider using immediately-invoked lambdas to initialize `const` variables where the value depends on some logic or computation, but is only ever set once for the lifetime of the variable.

## Prefer returning optional types (such as `TOptional<>` in Unreal code) from functions that may or may not return a valid value.

Using an optional forces all callers to explicitly handle the unset case, and can help clarify exactly when a value is known to be valid or not.
