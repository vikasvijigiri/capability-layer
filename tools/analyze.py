#!/usr/bin/env python3
"""Is this plan internally consistent — checked mechanically, before Gate 1.

Every finding here is something a program can decide: a missing heading, an
unresolved marker, a task with no verification command, a path claimed to exist
that does not. Judgement — is this the right architecture, is the scope sane —
stays with `artifact-review` and the human at the gate. Mixing the two produces
a checker that is wrong often enough to be ignored.

Adapted from `github/spec-kit`'s `/speckit.analyze`, which runs the same kind of
cross-artifact pass over spec, plan and tasks before implementation begins.

    python tools/analyze.py                  # the plan for the current branch
    python tools/analyze.py --slug checkout-retry
    python tools/analyze.py --json

Exit code is 1 when anything was found, so it can gate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_rs = _load("tools/resume.py", "resume_for_analyze")
_hooklib_for_analyze = _load(".claude/hooks/_hooklib.py", "hooklib_for_analyze")

REQUIRED_HEADINGS = ["**Goal:**", "**Risk:**", "## File map", "## Tasks"]

# Required in the plan's PREAMBLE -- everything before the first task heading.
#
# Added 2026-08-16, closing `GOAL_CHECKLIST.md` lines that had been prose since
# the checklist was written; prose passes every suite, which is why that document
# counts "enforced by a mechanism" and "described somewhere" separately.
#
# Positional and not a plain substring, which the first version got wrong. Tasks
# carry their own `**Rollback:**`, so a whole-document search is satisfied by
# task 3's revert line and the plan-level requirement adds nothing. The two are
# different claims: undoing task 7 tells nobody how to undo a plan whose tasks
# 1-6 already landed, and Gate 1 is specified to be shown the second one.
PREAMBLE_HEADINGS = ["**Rollback:**", "**Blast radius:**"]
TASK_RE = re.compile(r"(?m)^###\s+Task\s+(\d+)\s*:?(.*)$")
GATE_RE = re.compile(r"(?m)^- \[( |x|X)\]\s+([IVX]+)\s")
# `- [ ] Task 3 — title`. Distinguished from GATE_RE by what follows the box:
# a constitution gate is followed by a roman numeral, a progress box by `Task N`.
# `_hooklib.PROGRESS_TASK_BOX`, imported rather than retyped -- see its
# docstring for the four sites that had drifted into disagreement.
PROGRESS_RE = _hooklib_for_analyze.PROGRESS_TASK_BOX
# `- Create: \`path\` — why` / `- Modify: \`path:symbol\` — why`
FILE_RE = re.compile(r"(?m)^\s*-\s+(Create|Modify|Test|Delete|Move):\s*`([^`]+)`")


COMPLEXITY_HEADING_RE = re.compile(r"(?m)^##\s+Complexity tracking\s*$")


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _rollback_fields_exempt(text: str) -> bool:
    """Whether this plan's own `## Complexity tracking` states, in words, an
    exemption from the per-task `**Rollback:**`/`**Preconditions:**` fields.

    A bare "we have a Complexity tracking section" is not enough here -- unlike
    the constitution-gate check, silence about these two fields must not read
    as an exemption, or every future plan quietly inherits this plan's pass.
    The section must name both fields.
    """
    m = COMPLEXITY_HEADING_RE.search(text)
    if not m:
        return False
    nxt = re.search(r"(?m)^##\s+", text[m.end():])
    section = text[m.end(): m.end() + nxt.start() if nxt else len(text)]
    lowered = section.lower()
    return "rollback" in lowered and "precondition" in lowered


def analyze(text: str, exists=None, slug: str = "") -> list[dict]:
    """Findings for one plan. `exists(relpath)` decides path questions.

    Pure when `exists` is injected, which is how the suite drives every branch
    without building a repository per case.
    """
    if exists is None:
        def exists(_p: str) -> bool:
            return True

    out: list[dict] = []

    def add(line: int, code: str, msg: str) -> None:
        out.append({"line": line, "code": code, "finding": msg})

    # --- structure
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            add(1, "structure", f"missing required section {heading!r}")

    # The preamble is everything before the first task. A plan with no tasks at
    # all has already been reported above; here the whole document is preamble,
    # which is the reading that cannot produce a false pass.
    _first_task = TASK_RE.search(text)
    preamble = text[:_first_task.start()] if _first_task else text
    for heading in PREAMBLE_HEADINGS:
        if heading not in preamble:
            add(1, "structure",
                f"missing required section {heading!r} -- it must appear in the "
                f"plan's preamble; a task's own field is a different claim")

    # --- open questions. The gate cannot be passed while one remains, so
    # finding them here is the difference between a fixable draft and a
    # surprise at approval time.
    for m in re.finditer(re.escape(_rs.CLARIFICATION_MARKER), text):
        line = _line_of(text, m.start())
        snippet = text[m.start():m.start() + 90].split("\n")[0]
        add(line, "clarification", f"unresolved: {snippet}")

    # --- constitution gate
    gates = GATE_RE.findall(text)
    if not gates:
        add(1, "constitution", "no constitution gate block -- see .claude/constitution.md")
    unticked = [num for ticked, num in gates if ticked == " "]
    if unticked and "## Complexity tracking" not in text:
        add(1, "constitution",
            f"article(s) {', '.join(unticked)} unticked with no Complexity tracking "
            f"section -- an exception is legal, an unexplained one is not")

    # --- the progress block executing-plans ticks
    #
    # It said "`writing-plans` mandates that syntax expressly for tracking" while
    # the task template emitted no checkbox at all, so every plan in docs/plans/
    # had zero and the executor's progress mechanism had never had anything to
    # tick. Counted rather than merely required: a plan that gains a task and not
    # its box drifts back into the same silence one task at a time.
    tasks = list(TASK_RE.finditer(text))
    progress = PROGRESS_RE.findall(text)
    if tasks and not progress:
        add(1, "progress",
            f"no `## Progress` checkboxes for {len(tasks)} task(s) -- "
            f"`executing-plans` ticks these, and a plan with none gives it "
            f"nothing to record against")
    elif progress and len(progress) != len(tasks):
        add(1, "progress",
            f"{len(progress)} progress checkbox(es) for {len(tasks)} task(s) -- "
            f"one per task, or the record silently stops matching the plan")

    # --- tasks
    if not tasks:
        add(1, "tasks", "no `### Task N:` sections")
    rollback_exempt = _rollback_fields_exempt(text)
    for i, m in enumerate(tasks):
        body = text[m.end(): tasks[i + 1].start() if i + 1 < len(tasks) else len(text)]
        label = f"Task {m.group(1)}"
        line = _line_of(text, m.start())
        if "**Verification:**" not in body or "Run:" not in body:
            add(line, "untestable", f"{label} has no `Run:` verification command")
        if "Expect:" not in body:
            add(line, "untestable", f"{label} states no expected result")
        if "**Done when:**" not in body:
            add(line, "untestable", f"{label} has no `Done when:` condition")
        if not FILE_RE.search(body):
            add(line, "tasks", f"{label} names no file to create, modify or test")
        # Per task, not per plan: one task's `**Rollback:**` must not be read
        # as covering another, so this checks each task's own body only.
        if not rollback_exempt:
            if "**Rollback:**" not in body:
                add(line, "untestable", f"{label} has no `Rollback:` strategy")
            if "**Preconditions:**" not in body:
                add(line, "untestable", f"{label} has no `Preconditions:` check")

    # --- paths. A Modify target that does not exist is the single most common
    # way a plan is wrong in a way that only surfaces mid-implementation.
    for m in FILE_RE.finditer(text):
        verb, raw = m.group(1), m.group(2).split(":")[0].strip()
        line = _line_of(text, m.start())
        present = exists(raw)
        if verb in ("Modify", "Delete", "Move") and not present:
            add(line, "path", f"{verb} target does not exist: {raw}")
        if verb == "Create" and present:
            add(line, "path", f"Create target already exists: {raw}")

    # --- the slug ties plan, branch, green ref and PR together
    if slug and f"{slug}" not in text:
        add(1, "slug", f"plan never names its slug {slug!r}")

    return out


def plan_text(root: Path, slug: str) -> tuple[Path | None, str]:
    # `plan_path` returns (path, why) since 2026-08-08 -- it had to, because
    # "no plan exists" and "plans exist and none is this unit's" were the same
    # answer and that hid an approved plan from the state engine. This caller
    # wants only the path; the reason is `resume.py`'s to report.
    path, _why = _rs.plan_path(root, slug)
    if path is None:
        return None, ""
    try:
        return path, path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return path, ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    slug = args.slug or _rs.gather_facts(root)["slug"]
    path, text = plan_text(root, slug)

    if path is None:
        print(f"no plan for slug {slug!r} under docs/plans/ -- nothing to analyze")
        return 0

    findings = analyze(text, exists=lambda p: (root / p).exists(), slug=slug)
    rel = path.relative_to(root).as_posix()

    if args.as_json:
        print(json.dumps({"plan": rel, "findings": findings}, indent=2))
    elif not findings:
        print(f"{rel}: consistent -- {text.count('### Task')} task(s), no findings")
    else:
        for f in findings:
            print(f"{rel}:{f['line']}  [{f['code']}] {f['finding']}")
        print(f"\n{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
