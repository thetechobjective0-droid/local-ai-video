# Documentation Standard

Documentation is a first-class deliverable. Every implementation phase must update the documentation needed for another engineer or AI agent to understand, run, test, troubleshoot, and safely extend the feature.

## Required documentation

For each meaningful feature, provide the applicable items:

- purpose and scope
- architecture and data flow
- public interfaces and schemas
- configuration and environment requirements
- installation/setup steps
- CLI/API usage examples
- expected inputs and outputs
- failure modes and recovery behavior
- test coverage and how to run tests
- performance/resource considerations for M4/36 GB
- security considerations
- provider/model assumptions and versions
- troubleshooting notes
- change/migration notes when behavior or schemas change

## Documentation rules

1. Do not merge undocumented behavior changes.
2. Keep examples executable and synchronized with the implementation.
3. Document decisions, not just code mechanics.
4. Update README, phase documentation, skills, and ADRs when applicable.
5. Generated media is not documentation; document its reproducible generation metadata instead.
6. Agents must treat documentation updates as part of the definition of done.
7. Prefer concise, task-oriented documentation with commands and expected results.
8. Record model/prompt/provider versions when they materially affect output.

## Definition of Done

A feature is not complete until code, tests, documentation, configuration, and operational behavior are consistent.
