# Implementation Plan: [Title]

## Overview
Brief summary of what's being built and why.

## Work Units

### Unit 1: [Name]
- **Layer**: domain | application | adapters
- **Files**: `path/to/file.py`
- **Description**: What this unit does.
- **Dependencies**: Other units that must complete first (or "none").
- **Tests**: What to test and where (`tests/test_layer/test_file.py`).

### Unit 2: [Name]
...

## Parallel Execution Plan

| Group | Units | Rationale |
|-------|-------|-----------|
| A (parallel) | Unit 1, Unit 2 | No shared files or dependencies |
| B (after A) | Unit 3 | Depends on Unit 1's port definition |
| C (after B) | Unit 4 | Integration, touches composition root |

## New Domain Types
- `TypeName` — description, fields, validation rules

## New Ports
- `PortName` — methods, what it abstracts

## New Use Cases
- `UseCaseName` — what it orchestrates, which ports it needs

## Adapter Changes
- What existing adapters need modification and why

## Risk Notes
Anything that might be tricky, uncertain, or could affect existing functionality.
