# docs/recon/

One file per repository reconnaissance pass, written by `repo-recon`:

    docs/recon/YYYY-MM-DD-<repo>.md

A recon map is what makes a dropped-in layer able to continue work rather than
restart it. `tools/resume.py` derives workflow state from this layer's own
artifacts — a plan file, a `feat/` branch, a green ref — so a repository that has
never used the layer has nothing for it to read and reports `PLANNING` however
much finished work it contains. The map is the missing input: what exists, what
is half-built, and what cannot be verified.

Distinct from the neighbouring categories on purpose:

| Directory | Answers |
|---|---|
| `docs/recon/` | what this repository already is |
| `docs/specs/` | what we decided to build |
| `docs/plans/` | how we will build it |
| `docs/research/` | what the outside world knows about it |

A map is a snapshot and goes stale. It is not maintained in place — a second pass
writes a second dated file, so the difference between them is readable.
