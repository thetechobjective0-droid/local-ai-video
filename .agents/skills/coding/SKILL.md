# Coding Skill

## Use when

Implementing or modifying application code.

## Procedure

1. Inspect local architecture and neighboring modules.
2. Identify the smallest appropriate change.
3. Keep public interfaces typed.
4. Separate business logic from provider/runtime code.
5. Keep I/O at boundaries.
6. Validate external/model data immediately.
7. Write or update tests before declaring completion.
8. Run formatter, lint, tests, and relevant smoke checks.

## Required practices

- Prefer dependency injection.
- Prefer pure functions for transformations.
- Prefer immutable configuration objects.
- Use domain-specific exceptions.
- Avoid hidden global state.
- Avoid premature abstractions.
- Preserve backward compatibility unless the phase explicitly permits a breaking change.

## Anti-patterns

- Large god classes.
- Deeply nested conditionals when state or strategy objects would be clearer.
- Provider SDK calls inside business/domain models.
- Shell command strings built by interpolation.
- Silent exception swallowing.
- Returning fake/default success after a failed generation.
