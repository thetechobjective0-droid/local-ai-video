# Security Skill

## Use when

Handling filesystem paths, subprocesses, model output, API input, configuration, secrets, uploads, or provider integrations.

## Threat Model

Treat these as untrusted:

- user prompts
- LLM output
- generated filenames
- provider responses
- downloaded model metadata
- uploaded media

## Rules

- Never execute LLM output as code.
- Never pass user/model text through a shell command string.
- Use subprocess argument arrays.
- Set subprocess timeouts.
- Resolve and validate paths before writing.
- Prevent `..` path traversal.
- Restrict all project artifacts to the configured storage root.
- Never log tokens, passwords, API keys, or secrets.
- Keep `.env` files out of Git.
- Validate media before processing.

## Tests

Include tests for:

- path traversal
- invalid filenames
- shell metacharacters
- malformed provider output
- oversized/unexpected inputs
- missing configuration
- subprocess timeout/failure

## Supply Chain

When introducing a dependency, check:

- maintenance state
- license
- transitive dependency impact
- Apple Silicon compatibility
- security advisories where available
