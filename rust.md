# Rust Code Style

Conventions specific to Rust projects. This file is not loaded by default — project-level CLAUDE.md files in Rust repos should pull it in via `@~/.claude/rust.md` (or an equivalent relative path).

The general code style rules in `~/.claude/CLAUDE.md` still apply; the rules below are additions specific to Rust.

## Function signatures should precisely describe capabilities

Don't return `Result` if a function can't fail. Don't mark a function `async` if it doesn't await. Don't accept parameters the function doesn't use — delete them rather than prefixing with `_`. The signature is documentation: it should tell callers exactly what the function does and needs.

This precision is the default for code used in one or a few projects, where updating callers when a signature changes is cheap. Exceptions:

- **Trait implementations:** the parameter list is fixed by the trait, so use `_foo` to mark parameters that are required by the trait but unused in a specific impl.
- **Uniform dispatch:** if a caller holds the function behind a `dyn Trait` or a dispatch table that requires all entries to share a signature, keep the shared signature even if this specific function can't fail — the uniformity is load-bearing.
- **Public library APIs:** for a library with many external consumers, uniformity across the interface can be worth keeping so the library retains flexibility to change implementation without breaking callers.

## Use `.expect("...")` for invariants maintained by construction

When a function can technically return an error but we know the inputs are valid because we control them, `.expect("<reason>")` is the right choice — preferred over `.unwrap()` because the reason string documents which invariant you're relying on, and if the invariant is ever broken the panic message tells future-you exactly what went wrong. Examples: `serde_json::to_string()` on a `json!()` literal, `Response::builder()` with valid fields. Propagating these errors with `?` or `match` communicates false doubt and adds complexity without value.

By contrast, don't `.expect()` away errors from genuinely fallible operations — parsing user input, reading from disk, hitting the network. Those are conditions to handle, not bugs.

The test is: "if this panics, is it a bug I need to fix, or a condition I need to handle?" If it's a bug, `.expect()` with a message explaining the invariant.
