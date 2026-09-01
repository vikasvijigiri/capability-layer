---
description: Create the GitHub repository, add the remote, push the branch and open the PR after explicit confirmation; never configures its own merge gates.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Publish

Mode: mutating
Arguments: `$ARGUMENTS` is the repository name, or empty to propose one from the
directory name. It is not permission to publish.

Outward-facing: this is the only command here that sends anything to a service.

This is the only command that sends anything off this machine. A repository,
once public, can be indexed, cloned or forked before anyone deletes it — so the
confirmation in step 6 is the whole point, and showing a plan is not confirmation.
Step 4 asks *where*; step 6 asks *whether*. Two questions, because answering the
first is not answering the second.

## Order

1. Run `/verify` (equivalently `python tools/run_checks.py --tier all --require-test`).
   Stop if anything is red. The verification must be fresh for this tree; do not
   continue from an earlier transcript claim.
2. Run `git remote -v`, `git status --porcelain=v1 -uall`, `git log --oneline @{u}..HEAD`
   or `git log --oneline -20` when there is no upstream.
   Stop if a remote already exists — this command creates one, it does not
   re-point an existing repository at somewhere else.

3. Discover the owner. **Never resolve it with a single `gh api user`** — that
   names only the active personal account, so an organisation is invisible and
   the repository lands under the wrong owner with no symptom but the URL:

       python tools/git_identity.py --json

   It reports every candidate it can find — the active `gh` account, the orgs
   that account belongs to, other logged-in accounts including enterprise hosts,
   an existing remote's owner, and a GitHub noreply `user.email` — each labelled
   with where it came from. It ranks; it does not choose.

4. **Ask which owner**, with `AskUserQuestion`, before asking whether to publish.
   One option per candidate, up to four, `description` giving the source so the
   user can tell a personal account from an org. The tool appends "Other", and
   that is the box for typing a username or org by hand — so a user whose target
   was not discovered is never stuck.

   When `needs_manual_entry` is true there is nothing to list. Ask anyway, with
   two real options — *"`gh auth login` first"* (say that it is an interactive
   browser flow that cannot be scripted from here) and *"cancel"* — and let the
   appended "Other" take the username. Do not skip the question and guess.

   Validate whatever comes back before using it: 1–39 characters, alphanumerics
   and single interior hyphens. Anything else, ask again rather than interpolating
   it into a `gh` command.

5. Report, in this order: the chosen owner and how it was chosen, the proposed
   repository name, the visibility, the branch, the number of commits that would
   be pushed, and any uncommitted paths that would **not** be pushed.

6. Use **`AskUserQuestion`** to confirm, naming the owner and the visibility in
   the question itself. Options are real positions — publish private, publish
   public, cancel — each `description` saying what it means. Never add an "other"
   option; the tool appends one. A prose question is not confirmation: it is
   answerable by silence and it scrolls away in a long turn.

   The owner question in step 4 is **not** this confirmation. Choosing where a
   repository would go is not agreeing to create it, and treating a click on
   "ngenux" as permission to publish is the failure this separation prevents.
7. `gh repo create <owner>/<name> --private --source . --remote origin`
   then `git push -u origin <branch>`. Never `--force`, never to `main`.
   Use the owner from step 4 verbatim; do not re-derive it here.
8. `gh pr create --fill --base main --head <branch>`.
9. **Probe whether merge gates are even available here, then report. Do not
   print instructions without checking.**

       gh api "repos/<owner>/<name>/branches/main/protection"

   Three outcomes, and each gets a different sentence:

   | Response | Say |
   |---|---|
   | `200` | protection exists — print what it requires, and whether `conclusion` is among the required checks |
   | `404` | available and unset — print the settings to enable by hand: branch protection on `main` requiring the status check `conclusion`, and the merge queue for `main` |
   | `403` `Upgrade to GitHub Pro or make this repository public` | **unavailable on this plan.** Say so, and name what still holds the line |

   On `403`, do not leave a task nobody can do. Branch protection and rulesets
   are not offered on a free private repository, so the honest report is the
   limitation plus its compensating controls:

   - `.github/workflows/checks.yml` runs on every pull request and resolves the
     same `.claude/project-checks.json` the local gate does, so a red branch is
     visible on the PR — **visible, not blocked**;
   - `permission-security/02-branch-guard.py` refuses commits on `main` in any working
     tree that has the layer installed;
   - nothing prevents a direct `git push` to `main` from a clone without the
     layer. State that plainly rather than implying the branch is protected.

   The options are then a real choice for a human: make the repository public,
   upgrade the plan, or accept the gap knowingly. Recommending one is fine;
   deciding is not.

**Why a probe and not a printed instruction.** Step 9 printed those two settings
unconditionally, and on this repository the API answers `403` — so the "pending"
item it created was unfollowable, and it sat in `HANDOFF.md` as though somebody
had simply not got round to it. An instruction that cannot be carried out is
worse than none: it reads as an open task forever and it costs a reader the time
to discover why it is not.

## Never

- Never enable branch protection, required checks, or the merge queue itself.
  Those settings decide what may merge unattended; an agent that configures its
  own gates has removed the reason the gates exist. Print them, let a human set them.
- Never `gh pr merge`, `--admin`, or `--auto` in this command. Landing is
  `release-git`'s business and the queue's, after review.
- Never publish a repository whose tree has uncommitted secrets — step 1 runs
  the secret scan as part of the tier, and a red tier stops here.
- Never guess the owner, and never fall back to the active personal account when
  the question was not answered. Creating a repository under the wrong owner is
  not recoverable by editing a setting: it has a different URL, different
  members, and on a public repo it may be indexed before it is moved.
- Never make a repository public without being told to, in that turn.

## Why it is a command and not a hook

This layer shipped an automatic version once: a `SessionStart` hook installed
the whole capability layer into any git repository it found, unasked. It was
removed with `install.py`, and `session-init/02-session-context.py`
was reduced from authoring to detection — the layer's
`test_session_start_contract.py` (source repo only) asserts it creates nothing.

A hook fires unasked and its failure mode is silence. Publishing is irreversible
and outward-facing, so it gets a command, one confirmation, and a human.
`session-init/03-state-report.py` reports the `[state:no-remote]` condition when
a branch has commits and nowhere to send them; reporting is a hook's job, acting
is not.
