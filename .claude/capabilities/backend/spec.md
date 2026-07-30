# Backend Capability Specification

This document expands the `backend` capability into concrete conventions,
APIs, and guidelines.

Overview

- Scope: APIs, data storage, infra-as-code, observability, performance and
  backend-related security.
- Goal: provide reusable blueprints and skills that are safe to run with
  validators and human gates.

Interfaces

- Skills must declare: inputs, outputs, preconditions, side-effects
- Workflows must declare: stages, validators, required skills, human-gates
- Blueprints must include: problem signature, evidence, confidence, and
  reproducible steps

Validators

- All provisioning workflows must include `oauth-validator`, `smoke-test`,
  and a cost estimate validator where relevant.
- Any action that mutates infrastructure requires a human approval gate.

Templates

- Store canonical templates in `templates/` (env snippets, terraform stubs).

Promotion Rules

- Promote a workflow to a blueprint after: 3 independent successful runs with
  evidence and validator pass.

Observability

- Each skill and workflow emits structured events to the repo telemetry
  integration (topic: `backend.*`).

Security

- Secrets must be referenced via vault paths, never in plain text
- Any change modifying auth scopes requires Security review

Testing

- Unit-level smoke scripts for each skill
- Integration harness for workflows using ephemeral test environments

Maintenance

- Update `spec.md` when conventions or required validators change
