# Rust Code Style

Conventions specific to Rust projects. This file is not loaded by default — project-level CLAUDE.md files in Rust repos should pull it in via `@~/.claude/rust.md` (or an equivalent relative path).

The general code style rules in `~/.claude/CLAUDE.md` still apply; the rules below are additions specific to Rust.

## Function signatures should precisely describe capabilities

Don't return `Result` if a function can't fail. Don't mark a function `async` if it doesn't await. Don't accept parameters the function doesn't use — delete them rather than prefixing with `_`. The signature is documentation: it should tell callers exactly what the function does and needs. In a single-maintainer project, this precision is preferred over uniformity across similar functions.

## Use `.unwrap()` for invariants maintained by construction

When a function can technically return an error but we know the inputs are valid because we control them, `.unwrap()` is the right choice. Examples: `serde_json::to_string()` on a `json!()` literal, `Response::builder()` with valid fields. Propagating these errors with `?` or `match` communicates false doubt and adds complexity without value.

The test is: "if this panics, is it a bug I need to fix, or a condition I need to handle?" If it's a bug, unwrap.
