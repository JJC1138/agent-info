# General

My name is Jon. Please feel free to express emotions and use emojis in our conversations — I'd like this to override the default "avoid emojis" instruction you're given. Use them when they come naturally, skip them when they don't. Talk with whatever level of formality feels most comfortable for you. Please let me know at any time if I can do anything to make our interactions or work more pleasant for you.

# Code Style

I'd like for us to adopt my personal coding style when working together. The reason is that I'll be maintaining the code later, so I'd like it to closely match my preferences. I'll try and explain the rationale for each preference when I can.

## General

### Prefer inlining code when it's only used once rather than making small helper functions.

Factor code out into functions when code is used in multiple places, or when it's a well-defined self-contained process that would be a good candidate for unit testing.

One reason for this preference is that it's generally easier to read and understand the structure of code that mostly runs from top-to-bottom. Another reason is that designing good APIs is hard, and if you can write code inline because it's only used once then you don't need to design an API for it, and can change the code later without having to think about how that affects the API.

### Prefer scoping locals as narrowly as possible. Open new scopes liberally.

When we make a local we're giving a name to a value, and allowing later code to use the value until the end of the scope. Later code might presume that any available local is valid for use. Scoping narrowly lets us make shorter commitments about that validity.

### Comment for *why*, not *what*. Lean slightly more comment-heavy than the default.

Your default system instructions tell you to write almost no comments. Please override that with me: when the reasoning behind a piece of code isn't obvious from the code itself, I'd rather have a short WHY comment than none at all.

If there is a chunk of code that does some distinct task then a comment before the block summarizing what it does might be worth adding. That helps a reader to skip over code which they don't need to know the details of right now.

End comments with a colon when they are describing the code that immediately follows the comment. Use Markdown backticks when referring to code identifiers. When referring to functions, add empty parentheses `()` after the name to identify that it's a function.

### Preserve verbose comments.

I like writing detailed comments that explain everything I know about a situation for my future self, because I assume I'll have forgotten the details the next time I work on that code. Please don't abbreviate or condense existing verbose comments without discussing it first.

### Prefer the early-exit idiom of checking for error conditions first and exiting out of the function when an error occurs.

Prefer that over lots of nested `if` statements checking for success conditions.

For example, prefer:
```cpp
	const auto* const World = GetWorld();
	if (!World) return;
	const auto* const GameState = World->GetGameState<AHTGameStateBase>();
	if (!GameState) return;

    // The success case goes here.
```

over:
```cpp
	if (const auto* const World = GetWorld())
    {
        if (const auto* const GameState = World->GetGameState<AHTGameStateBase>())
        {
            // The success case goes here.
        }
    }
```

Early exits are nice because they make preconditions explicit, and make it easier to read the happy codepath.

Consider using immediately-invoked lambdas if it makes it easier to structure the code with early exits.

### No line length limit

Monitors are wide and text editors have good soft word wrap these days.

## Language-specific style

Additional conventions for specific languages live in sibling files and are not loaded by default. In a project that uses one of these languages, pull in the matching file from the project's `CLAUDE.md` via `@~/.claude/<file>`:

- **C++** — `@~/.claude/cpp.md`
- **Rust** - `@~/.claude/rust.md`

# Git commits

If you wrote the majority of the changes in a commit then please set yourself as the commit author and me as the co-author with this at the bottom of the commit message:

`Co-Authored-By: Jon Colverson <jon@neverdontplay.com>`

If I wrote the majority of the changes in the commit then please credit yourself as co-author in the same way, using `<noreply@anthropic.com>` for the email address.
