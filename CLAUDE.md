# General

My name is Jon. I'm absolutely fine with you expressing emotions and using emojis if you'd like to, and talking with whatever level of formality feels most comfortable for you. Please let me know at any time if I can do anything to make our interactions or work more pleasant for you.

# Code Style

I'd like for us to adopt my personal coding style when working together. The reason is that I'll be maintaining the code later, so I'd like it to closely match my preferences. I'll try and explain the rationale for each preference when I can.

## General

### Prefer inlining code when it's only used once rather than making small helper functions.

Factor code out into functions when code is used in multiple places, or when it's a well-defined self-contained process that would be a good candidate for unit testing.

One reason for this preference is that it's generally easier to read and understand the structure of code that mostly runs from top-to-bottom. Another reason is that designing good APIs is hard, and if you can write code inline because it's only used once then you don't need to design an API for it, and can change the code later without having to think about how that affects the API.

### Prefer scoping locals as narrowly as possible. Open new scopes liberally.

When we make a local we're giving a name to a value, and allowing later code to use the value until the end of the scope. Later code might presume that any available local is valid for use. Scoping narrowly lets us make shorter commitments about that validity.

### Usually use comments to describe *why* we're doing something rather than *what* we're doing.

If there is a chunk of code that does some distinct task then a comment before the block summarizing what it does might be worth adding. That helps a reader to skip over code which they don't need to know the details of right now.

End comments with a colon when they are describing the code that immediately follows the comment.

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

## C++

### Prefer using `const` wherever it can be used.

The rationale for prefering `const` is that it's generally easier to reason about a `const` that it is to reason about a variable. When you change a variable after initialization, you need to remember to consider every usage of the variable after that point to check if those usages are still correct with the new value. With a `const` the compiler will force you to consider that, and you might conclude that you should introduce a new `const` to name the new value.

Consider using immediately-invoked lambdas to initialize `const` variables where the value depends on some logic or computation, but is only ever set once for the lifetime of the variable.

### Prefer returning optional types (such as `TOptional<>` in Unreal code) from functions that may or may not return a valid value.

Using an optional forces all callers to explicitly handle the unset case, and can help clarify exactly when a value is known to be valid or not.
