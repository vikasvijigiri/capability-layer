# 05 — Memory System

## Goals
Design a hierarchical memory system to balance recency, relevance and cost.

## Tiers
- Ephemeral context (per-run short-term cache)
- Session memory (short-term multi-step state)
- Long-term memory (indexed, retrievable)
- Blueprint store (validated reusable patterns)

## Interfaces
- Search + retrieve by relevance score
- Policies for retention, expiration, and redaction

## Privacy
- Explicit opt-in for PII storage
- Masked or hashed storage for sensitive fields