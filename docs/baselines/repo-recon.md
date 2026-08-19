# Baseline: repo-recon

Date: 2026-08-19  
Campaign: [capability-layer-audit](capability-layer-audit.md)

## Same task

Map an unread repository into a durable architecture and unfinished-work report
without mutating the repository under inspection.

## Comparison

The control condition is a directory listing and manual, unstructured reading.
The treatment uses `tools/recon.py` for deterministic facts first, then records
verified versus inferred commands, unfinished items with `file:line`, and the
untestable surface in one recon map.

## Verdict

This is a dated, repository-local baseline. It documents the intended
observable difference and does not claim that a map is correct until a real
host run has produced and reviewed one.
