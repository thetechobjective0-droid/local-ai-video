# Agent and Skill System

## Purpose

The project uses a disciplined agent/skill model so AI coding assistants can work consistently across architecture, implementation, testing, performance, security, documentation, and media-provider integration.

The files under `.agents/skills/` are reusable operating procedures. An agent should load the smallest relevant skill set for the task at hand.

## Agent Roles

### 1. Architect

Use for:

- architecture changes
- module boundaries
- provider interfaces
- persistence/state design
- major dependency decisions

Required outputs:

- decision summary
- affected components
- migration/backward-compatibility impact
- testing implications

### 2. Implementer

Use for ordinary feature development.

Required outputs:

- implementation
- tests
- documentation updates where required
- validation results

### 3. Test Engineer

Use for new functionality, bug fixes, or test-suite expansion.

Required outputs:

- happy-path tests
- negative tests
- boundary tests
- regression test for fixed defects

### 4. Provider Engineer

Use for new LLM/image/video/TTS/music backends.

Required outputs:

- capability definition
- provider adapter
- health check
- normalized errors
- contract tests
- fallback behavior
- resource requirements

### 5. Performance Engineer

Use for memory, speed, concurrency, model-loading, or rendering work.

Required outputs:

- baseline
- measurement method
- before/after metrics
- safety limits

### 6. Security Reviewer

Use when code executes subprocesses, handles files, accepts external input, loads model output, or manages secrets.

Required outputs:

- threat considerations
- boundary validation
- unsafe-input tests
- security recommendations

### 7. Documentation Engineer

Use when architecture, CLI, API, configuration, setup, or provider behavior changes.

Required outputs:

- updated docs
- examples
- migration notes where needed

### 8. Release Reviewer

Use before milestones/releases.

Checks:

- tests pass
- documentation current
- no generated artifacts committed
- no secrets
- version/schema compatibility
- reproducibility
- hardware assumptions documented

## Skill Selection Matrix

| Task | Required skill(s) |
|---|---|
| New module | coding, testing |
| Bug fix | coding, testing, debugging |
| LLM prompt | prompt-engineering, testing |
| New provider | provider-integration, testing, performance |
| FFmpeg work | rendering, testing |
| Memory issue | performance, debugging |
| Filesystem/process execution | security, coding, testing |
| API endpoint | API, coding, testing |
| CLI command | CLI, coding, testing |
| Data model change | architecture, schema, migration, testing |
| Major refactor | architecture, coding, testing |
| Release | release, security, testing, documentation |

## Skill Usage Rule

Do not load every skill for every task. Select the smallest set that fully covers the change. If the task crosses architectural boundaries, add architecture/review skills.

## Standard Agent Loop

```text
Understand
  ↓
Inspect
  ↓
Plan
  ↓
Implement
  ↓
Validate
  ↓
Test
  ↓
Review
  ↓
Document
```

Agents must not skip validation just because implementation is straightforward.

## Agent Context Files

At task start, inspect in this order:

1. `AGENTS.md`
2. `plan.md` relevant phase
3. relevant source files
4. relevant tests
5. relevant skill file(s)
6. provider/model documentation if integrating external software

## Task Completion Record

For meaningful tasks, the agent should be able to report:

```text
Task:
Scope:
Files changed:
Tests added/changed:
Checks run:
Performance impact:
Security impact:
Documentation updated:
Known limitations:
```
