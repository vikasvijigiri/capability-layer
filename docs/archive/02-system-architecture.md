# 02 — System Architecture

## Overview
Logical layers:
- Interface layer (APIs, CLIs)
- Execution layer (Planner, Orchestrator)
- Skill & Tool layer (pluggable skills)
- Memory layer (short & long term)
- Governance & Validation layer
- Observability & Telemetry

## Components
- Planner: breaks goals into tasks.
- Skill Router: selects skill implementations.
- Blueprint Store: validated patterns.
- Validator: checks outcomes against requirements.

## Data Flows
1. User / API request
2. Planner decomposes task
3. Skills execute with memory + tool calls
4. Validator verifies output
5. Reflection & learning update Blueprints/skills