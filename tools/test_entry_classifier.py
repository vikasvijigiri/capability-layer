#!/usr/bin/env python3
"""Test the UserPromptSubmit entry classifier against the labelled trigger corpus.

Why this suite exists
---------------------
"Fire whenever the prompt genuinely involves a task" is a predicate, and a
predicate stated only in prose is one every reader resolves differently. This
pins it to `docs/evals/trigger-queries.json` -- the same labelled queries that
define what each stage's `description:` is supposed to catch.

Reusing that corpus rather than writing a second one is the point. A private
fixture would let the classifier and the descriptions drift apart while both
stayed green, and the two are answering the same question about the same prompt.

The corpus is three-class here, assembled from two binary sets:

  * `task-brief` positives    -> must classify `entry-unframed`
  * `brainstormer` positives  -> must classify `entry-open`
  * either set's negatives    -> must NOT get the class that set names, though a
    negative may legitimately land on the *other* class. "add a settings screen
    with three tabs" is a `brainstormer` negative precisely because it is framing
    work, so demanding silence there would be asserting the wrong thing.

The last rule is what stops this suite from over-fitting into a second, stricter
routing table that nothing else agrees with.

Run: python tools/test_entry_classifier.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "prompt-intake" / "01-entry-classifier.py"
CORPUS = ROOT / "docs" / "evals" / "trigger-queries.json"

# Which state key each stage's positives must produce. Only the two entry stages
# appear: the classifier is silent for every later stage by design, and asserting
# that here would duplicate the OTHER_STAGE pass rather than check it.
CLASS_OF = {
    "writing-plans": "entry-unframed",
    "brainstormer": "entry-open",
}

# `writing-plans` absorbed the framing skill on 2026-08-09, and that broke the
# assumption this suite was built on: that a skill name is one entry shape.
#
# It now owns two. "add a dark mode toggle" arrives unframed and the entry rule
# is worth injecting; "break this down into steps" is already framed and enters
# at the planning stage, where the skill's own description does the routing and a
# nudge would be noise. Both are true positives for the same skill.
#
# So the corpus carries the distinction per query, in an `entry` field that
# `eval_triggers.py` ignores (it validates `query` and `should_trigger` only).
# The alternative was a private list of framing-shaped queries in this file,
# which is the drift this suite was written to avoid -- two labellings of one
# corpus, one of them invisible to the harness that spends money on it.
ENTRY_FIELD_STAGES = {"writing-plans"}

# Queries the corpus labels for one stage that are textually indistinguishable
# from another stage's, mapped to the resolution and the reason.
#
# These are declared rather than quietly dropped. A classifier tuned until every
# label agreed would be overfitted to a corpus that disagrees with itself, and the
# disagreement would move from a named line here into an unexplained regex.
#
# The one entry: `brainstormer` labels "what should the settings screen look
# like" as a trigger, and `designer` labels "what should this dashboard look
# like" as a trigger. Same grammar, same subject, opposite owners. workflow.md's
# Off-chain table settles it -- a user-facing surface with no design contract is
# `designer`, which is entered before surface work rather than as stage 2 -- so
# both go silent and the surface skill's own description does the routing.
KNOWN_COLLISIONS = {
    "what should the settings screen look like": (
        None,
        "identical in shape to a designer-labelled query; surface design is "
        "off-chain and owned by its own skill, so the classifier stays silent",
    ),
}

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load_classifier():
    """Import the hook by path -- its filename is not a Python identifier."""
    spec = importlib.util.spec_from_file_location("entry_classifier", HOOK)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {HOOK}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    check("the classifier hook exists", HOOK.is_file(), str(HOOK))
    if failures:
        return 1

    # `docs/evals/` is not part of what `install.py` copies -- the corpus is this
    # repository's measurement of its own descriptions, not something an
    # installed layer carries. So in a target repo there is nothing to check
    # against, and the honest answer is to say so rather than to fail.
    #
    # Found by `test_package.py`, which installs the wheel into a fresh repo and
    # runs that repo's own tier: this suite went red there while being green
    # here, on its first run after the corpus became load-bearing.
    if not CORPUS.is_file():
        print(f"SKIP: no {CORPUS.relative_to(ROOT).as_posix()} -- the labelled "
              f"corpus ships with the source repository, not with an install; "
              f"the classifier's predicate is unmeasured here")
        return 0

    mod = load_classifier()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))

    # --- positives: the class the stage owns ---------------------------------
    for stage, want in CLASS_OF.items():
        entries = corpus.get(stage) or []
        check(f"{stage} has corpus entries", bool(entries))
        for e in entries:
            if not e.get("should_trigger"):
                continue
            q = e["query"]
            got = mod.classify(q)
            if q in KNOWN_COLLISIONS:
                pinned, why = KNOWN_COLLISIONS[q]
                check(f"[collision -> {pinned}] {q[:44]}", got == pinned,
                      f"got {got!r}; declared resolution is {pinned!r} because {why}")
                continue
            if stage in ENTRY_FIELD_STAGES:
                # A missing `entry` on a stage that owns two shapes is a hole in
                # the corpus, not a default. Defaulting it would quietly assert
                # whichever shape happened to be right for the last query added.
                marked = e.get("entry")
                check(f"[{stage}] {q[:44]} declares its entry shape",
                      marked in ("unframed", "silent"),
                      f"got {marked!r}; a stage owning two shapes must say which")
                expect = want if marked == "unframed" else None
                check(f"[{marked}] {q[:52]}", got == expect, f"got {got!r}")
                continue
            check(f"[{want}] {q[:58]}", got == want, f"got {got!r}")

    # --- negatives: never the class that set names ---------------------------
    #
    # Asserted as "not this class" rather than "silent" on purpose; see the
    # module docstring. A negative landing on the other entry class is correct
    # routing, not a miss.
    for stage, forbidden in CLASS_OF.items():
        for e in corpus.get(stage) or []:
            if e.get("should_trigger"):
                continue
            q = e["query"]
            got = mod.classify(q)
            check(f"[not {forbidden}] {q[:54]}", got != forbidden, f"got {got!r}")

    # --- every later stage's positives are silent ----------------------------
    #
    # The OTHER_STAGE pass is the one that decides whether this hook is noise. A
    # framing nudge on a debugging or delivery prompt competes with the stage
    # that should actually run, so it is checked against real prompts for those
    # stages rather than against invented ones.
    for stage, entries in corpus.items():
        if stage.startswith("_") or stage in CLASS_OF:
            continue
        for e in entries:
            if not e.get("should_trigger"):
                continue
            q = e["query"]
            got = mod.classify(q)
            check(f"[silent:{stage}] {q[:50]}", got is None, f"got {got!r}")

    # --- breadth overrides the settled reading -------------------------------
    #
    # The regression this pins: the prompt that started this work -- a greenfield
    # product naming six news domains, nine blueprint sections and four roadmap
    # horizons -- classified `entry-unframed`, because "build a web app that..."
    # is the same imperative as "add a dark mode toggle". Framing it would have
    # written the anchor that stage 2 exists to prevent.
    #
    # Both limbs are asserted, since either alone would let a broad prompt with
    # no commas, or a terse one with many, slip back through.
    wide = ("build a web app that continuously monitors business, market, "
            "technology, government, funding and regulatory news from reliable "
            "sources, detects emerging opportunities and generates a grounded "
            "blueprint for each with a staged execution roadmap")
    check("a broad greenfield build reads as open, not settled",
          mod.classify(wide) == "entry-open", f"got {mod.classify(wide)!r}")
    check("a narrow build still reads as settled",
          mod.classify("add a dark mode toggle to the settings") == "entry-unframed",
          f"got {mod.classify('add a dark mode toggle to the settings')!r}")

    # Short enough that the word floor cannot be what trips it, so this isolates
    # the clause limb.
    commas = "we need a way to add a, b, c, d, e, f and g"
    check("clause count alone can trip breadth",
          mod.classify(commas) == "entry-open", f"got {mod.classify(commas)!r}")

    # The threshold's whole safety argument is headroom over the corpus. If a
    # future query is longer than the floor, the floor silently starts
    # reclassifying labelled data instead of catching genuinely broad requests.
    longest = max(
        (len(e["query"].split()) for k, v in corpus.items()
         if not k.startswith("_") for e in v),
        default=0,
    )
    check(f"breadth floor ({mod.BREADTH_WORDS}) clears the longest query ({longest})",
          mod.BREADTH_WORDS > longest,
          "re-measure the corpus before lowering the floor")

    # --- layer vocabulary is qualified, not bare -----------------------------
    #
    # `HARD_STAGE` carried bare `\bhooks?\b` and `\bskills?\b` until a review
    # caught them. Two of the commonest words in product vocabulary, unqualified,
    # in the pass that runs first: ordinary framing work was silently swallowed
    # before it could reach the TASK pass.
    #
    # The corpus could not catch this and still cannot -- it has no non-layer use
    # of either word, so every label stayed green. That is the whole reason these
    # cases are written out here instead: an over-broad pattern is only ever
    # visible against inputs nobody thought to label.
    for _q in ("build a skill tree for the RPG character screen",
               "add a git hook that blocks commits without tests"):
        check(f"[not swallowed] {_q[:46]}", mod.classify(_q) is not None,
              "product vocabulary must not match the agent-layer pass")

    # The same words WITH agent-layer context still belong to that pass. Both
    # directions are asserted: a fix that merely deleted the patterns would pass
    # the two checks above and lose the behaviour they were added for.
    for _q in ("my new skill never fires, figure out what is wrong with the wiring",
               "the post-run hook produces no output at all",
               "audit .claude for drift"):
        check(f"[layer, silent] {_q[:46]}", mod.classify(_q) is None,
              "the agent layer is not framed as product work")

    # Known and deliberately not fixed here: TASK matches `we need a way to` but
    # not a bare `we need <noun>`, so "we need react hooks for the new state
    # management" is still silent. That is narrowness in the TASK pass, not the
    # suppression this section pins -- widening it is its own change with its own
    # false-positive budget. Recorded so the two are never confused again.
    check("the residual TASK gap is still the TASK gap, not a HARD_STAGE match",
          not mod._hit(mod.HARD_STAGE,
                       "we need react hooks for the new state management"),
          "if this fails, layer vocabulary has gone bare again")

    # --- TOO_SMALL defers to scope.py's control/sensitive-surface veto ------
    #
    # HANDOFF.md's own reproduced case ("add a --jobs flag to run_checks.py")
    # was a paraphrase -- traced live, pass 1's `\.claude\b` pattern already
    # catches any prompt containing a directory-qualified `.claude/...` path
    # before TOO_SMALL ever runs. The real gap is a path scope.py's own
    # CONTROL_PATTERNS/SENSITIVE_PATTERNS would veto that pass 1 has no
    # vocabulary for. `.github/workflows/*.yml` was tried and rejected as a
    # second case: SMALL_LOCATED's `[^.]{0,60}` gap can never cross the
    # leading dot in `.github/`, so that phrasing never reaches TOO_SMALL in
    # the first place regardless of this fix -- a different, pre-existing
    # quirk, out of scope here. `pyproject.toml` (no directory) and
    # `capability_layer/cli.py` (no leading dot) both genuinely reach
    # TOO_SMALL today; live-verified before writing these cases.
    _scope_spec = importlib.util.spec_from_file_location(
        "scope_for_test", ROOT / "tools" / "scope.py")
    if _scope_spec is None or _scope_spec.loader is None:
        raise RuntimeError("cannot load tools/scope.py")
    scope_mod = importlib.util.module_from_spec(_scope_spec)
    _scope_spec.loader.exec_module(scope_mod)

    for _q, _why in (
        ("fix the version pin in pyproject.toml", "sensitive-surface (literal filename)"),
        ("fix the version check in capability_layer/cli.py", "sensitive-surface (directory pattern)"),
    ):
        check(f"[not entry-small: {_why}] {_q[:44]}",
              mod.classify(_q) != "entry-small", f"got {mod.classify(_q)!r}")

    check("scope.py independently calls pyproject.toml sensitive/control",
          scope_mod._match("pyproject.toml",
                            scope_mod.CONTROL_PATTERNS + scope_mod.SENSITIVE_PATTERNS),
          "the two mechanisms must agree on this fact")

    # Known, deliberate limitation, pinned rather than left to erode silently:
    # a bare filename with no directory component under a wildcard directory
    # pattern (`.claude/hooks/*`) is NOT resolved -- doing so would require
    # checking the token against the real filesystem tree, which would make
    # classify() depend on repo state beyond its two fixed inputs. A
    # regression here means the limitation note has gone stale, not that
    # something broke.
    check("known limitation still holds: a bare wildcard-directory filename "
          "is not caught",
          mod.classify("fix a typo in _hooklib.py") == "entry-small",
          f"got {mod.classify('fix a typo in _hooklib.py')!r}")

    # --- objective 18: full-corpus route-presence (adaptive, not prescriptive)
    #
    # A prescriptive system is one that returns the same answer regardless of
    # input. `classify()` has five possible outputs; the checks above already
    # pin `entry-open`, `entry-unframed` and `None` corpus-wide via CLASS_OF
    # and the OTHER_STAGE pass, so asserting a bare ">1 distinct key" here
    # could never fail -- it would already be satisfied by those. What
    # nothing currently checks is that `entry-small` and `entry-direct` are
    # BOTH actually reachable from the real corpus, not just theoretically
    # possible. Measured this session by direct replay: 217 queries ->
    # {None: 184, 'entry-unframed': 13, 'entry-open': 12, 'entry-small': 4,
    # 'entry-direct': 4}.
    _route_counts: dict[str | None, int] = {}
    for _stage, _entries in corpus.items():
        if _stage.startswith("_"):
            continue
        for _e in _entries:
            _key = mod.classify(_e["query"])
            _route_counts[_key] = _route_counts.get(_key, 0) + 1
    print(f"route distribution across the whole corpus: {_route_counts}")
    check("objective 18: entry-small is reachable from the real corpus",
          _route_counts.get("entry-small", 0) > 0, str(_route_counts))
    check("objective 18: entry-direct is reachable from the real corpus",
          _route_counts.get("entry-direct", 0) > 0, str(_route_counts))

    # --- objective 18: fallback safety for the control/sensitive veto -------
    #
    # `_control_or_sensitive_patterns()` caches `scope.py`'s CONTROL_PATTERNS/
    # SENSITIVE_PATTERNS at first call. Comparing that cache against a
    # freshly-read `scope.py` (a naive "drift check") can never fail -- both
    # sides load the same file at test time and are definitionally equal.
    # What is actually checkable is the fallback path this repo relies on
    # when `scope.py` cannot be loaded: `_load()` returning `None` must
    # degrade the veto to an empty list, never an unhandled exception or a
    # silently-stale cache.
    mod._CONTROL_OR_SENSITIVE_PATTERNS = None
    _real_load = mod._load
    mod._load = lambda rel, name: None
    try:
        _stubbed_patterns = mod._control_or_sensitive_patterns()
    finally:
        mod._load = _real_load
        mod._CONTROL_OR_SENSITIVE_PATTERNS = None  # so later real calls re-load
    check("objective 18: the control/sensitive veto degrades to an empty "
          "list when scope.py cannot be loaded, not an exception",
          _stubbed_patterns == [], f"got {_stubbed_patterns!r}")

    _real_patterns = mod._control_or_sensitive_patterns()
    check("objective 18: the unstubbed veto reflects scope.py's real, "
          "current patterns (non-empty), not a hardcoded stub",
          bool(_real_patterns), f"got {_real_patterns!r}")

    # --- classify() persists its result for telemetry/09-telemetry.py --------
    #
    # Written even when key is None -- the common, silent case -- so a
    # downstream reader can tell "classified as nothing" from "never ran".
    _state = ROOT / ".claude" / "hooks" / "state" / "last-entry-shape.json"
    mod._record_entry_shape("entry-open")
    _recorded = json.loads(_state.read_text(encoding="utf-8"))
    check("_record_entry_shape writes the given key",
          _recorded.get("key") == "entry-open", f"got {_recorded!r}")
    mod._record_entry_shape(None)
    _recorded_none = json.loads(_state.read_text(encoding="utf-8"))
    check("_record_entry_shape writes null, not silence, for the common case",
          _recorded_none.get("key") is None, f"got {_recorded_none!r}")

    # --- the rendered blocks exist -------------------------------------------
    #
    # The hook keeps no fallback text, so a missing block degrades to a generic
    # line in a live session. That is the right failure and the wrong place to
    # discover it.
    for key in CLASS_OF.values():
        check(f"workflow.md has a [state:{key}] block", bool(mod.workflow_block(key)))

    # --- structural: no skill name in the hook's own source ------------------
    #
    # `test_hook_registration.py` asserts this across every hook by AST. Repeated
    # here as a plain substring scan because this hook is the one whose entire
    # job is routing-adjacent, and it is the likeliest place for a hardcoded name
    # to be added back by someone fixing a misclassification in a hurry.
    src = HOOK.read_text(encoding="utf-8")
    body = src.split('"""', 2)[-1]
    skills = {d.name for d in (ROOT / ".claude" / "skills").iterdir() if d.is_dir()}
    named = sorted(s for s in skills if s in body)
    check("the classifier names no skill outside its docstring", not named,
          f"names {named} -- workflow.md decides, the hook measures")

    print()
    if failures:
        print(f"{len(failures)} FAILED")
        return 1
    print("OK: the entry predicate matches the labelled corpus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
