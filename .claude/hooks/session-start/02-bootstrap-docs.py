"""
SessionStart hook — global, runs once per session in every repo.

Scope, by design: repository detection, missing-scaffolding detection, and
minimal context loading. Nothing here authors strategic documents, writes
source, reviews, or commits — that's the model's job during the actual
session, not this deterministic script's.

Also subsumes the old inline "load HANDOFF.md" SessionStart command: this
script loads HANDOFF.md itself (plus a few other minimal-context sources),
so that logic isn't duplicated between two separate hook entries.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402


AI_APP_DEP_MARKERS = (
    "openai", "@anthropic-ai/sdk", "anthropic", "langchain", "llama-index",
    "llamaindex", "transformers", "torch", "tensorflow", "@google/generative-ai",
)
MOBILE_DEP_MARKERS = ("react-native", "expo")
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?:\s"
)

NOISE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", "dist", "build", ".next", "target",
    "output", ".claude",
}

BOOTSTRAP_FILES = [
    "README.md",
    "CLAUDE.md",
    "TASK.md",
    "MEMORY.md",
    "HANDOFF.md",
    "LOG.md",
    "ISSUES.md",
]


def find_git_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, ".git")) or os.path.isfile(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def read_json_if_file(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def detect_stack(root):
    languages = set()
    frameworks = set()
    package_managers = set()
    monorepo_tool = None

    def exists(*parts):
        return os.path.isfile(os.path.join(root, *parts))

    pkg_json = read_json_if_file(os.path.join(root, "package.json"))
    if pkg_json is not None:
        languages.add("TypeScript" if exists("tsconfig.json") else "JavaScript")
        deps: dict[str, str] = {}
        deps.update(pkg_json.get("dependencies", {}) or {})
        deps.update(pkg_json.get("devDependencies", {}) or {})
        for dep, label in (
            ("react", "React"), ("vue", "Vue"), ("@angular/core", "Angular"),
            ("next", "Next.js"), ("express", "Express"), ("fastify", "Fastify"),
            ("@nestjs/core", "NestJS"), ("svelte", "Svelte"),
        ):
            if dep in deps:
                frameworks.add(label)
        if "workspaces" in pkg_json:
            monorepo_tool = "npm/yarn workspaces"

    deployment = None
    if exists("vercel.json") or os.path.isdir(os.path.join(root, ".vercel")):
        deployment = "Vercel"
    elif pkg_json is not None:
        pkg_deps: dict[str, str] = {}
        pkg_deps.update(pkg_json.get("dependencies", {}) or {})
        pkg_deps.update(pkg_json.get("devDependencies", {}) or {})
        if "vercel" in pkg_deps:
            deployment = "Vercel"

    if exists("requirements.txt") or exists("pyproject.toml") or exists("setup.py") or exists("Pipfile"):
        languages.add("Python")
        for req_file in ("requirements.txt", "pyproject.toml", "Pipfile"):
            fp = os.path.join(root, req_file)
            if os.path.isfile(fp):
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        text = f.read().lower()
                    if "django" in text:
                        frameworks.add("Django")
                    if "flask" in text:
                        frameworks.add("Flask")
                    if "fastapi" in text:
                        frameworks.add("FastAPI")
                except Exception:
                    pass

    if exists("go.mod"):
        languages.add("Go")
    if exists("Cargo.toml"):
        languages.add("Rust")
        if exists("Cargo.toml") and read_json_if_file(os.path.join(root, "Cargo.toml")) is None:
            try:
                with open(os.path.join(root, "Cargo.toml"), encoding="utf-8", errors="ignore") as f:
                    if "[workspace]" in f.read():
                        monorepo_tool = monorepo_tool or "Cargo workspace"
            except Exception:
                pass
    if exists("pom.xml"):
        languages.add("Java (Maven)")
    if exists("build.gradle") or exists("build.gradle.kts"):
        languages.add("Java/Kotlin (Gradle)")
    if exists("Gemfile"):
        languages.add("Ruby")
    if exists("composer.json"):
        languages.add("PHP")
    for name in os.listdir(root) if os.path.isdir(root) else []:
        if name.endswith(".csproj") or name.endswith(".sln"):
            languages.add(".NET/C#")
            break

    lockfile_map = {
        "package-lock.json": "npm", "yarn.lock": "yarn", "pnpm-lock.yaml": "pnpm",
        "poetry.lock": "poetry", "Pipfile.lock": "pipenv", "Cargo.lock": "cargo",
        "go.sum": "go modules", "Gemfile.lock": "bundler", "composer.lock": "composer",
    }
    for lockfile, mgr in lockfile_map.items():
        if exists(lockfile):
            package_managers.add(mgr)
    if not package_managers and exists("requirements.txt"):
        package_managers.add("pip")

    if exists("pnpm-workspace.yaml"):
        monorepo_tool = "pnpm workspaces"
    elif exists("lerna.json"):
        monorepo_tool = "Lerna"
    elif exists("nx.json"):
        monorepo_tool = "Nx"
    elif exists("turbo.json"):
        monorepo_tool = "Turborepo"
    elif exists("rush.json"):
        monorepo_tool = "Rush"

    if monorepo_tool is None:
        for sub in ("apps", "packages", "services"):
            subdir = os.path.join(root, sub)
            if os.path.isdir(subdir):
                child_count = sum(
                    1 for name in os.listdir(subdir)
                    if os.path.isfile(os.path.join(subdir, name, "package.json"))
                    or os.path.isfile(os.path.join(subdir, name, "go.mod"))
                    or os.path.isfile(os.path.join(subdir, name, "Cargo.toml"))
                )
                if child_count > 1:
                    monorepo_tool = f"multiple packages under {sub}/"
                    break

    all_deps: dict[str, str] = {}
    if pkg_json is not None:
        all_deps.update(pkg_json.get("dependencies", {}) or {})
        all_deps.update(pkg_json.get("devDependencies", {}) or {})
    dep_text = " ".join(all_deps.keys()).lower()
    for req_file in ("requirements.txt", "pyproject.toml", "Pipfile"):
        fp = os.path.join(root, req_file)
        if os.path.isfile(fp):
            try:
                with open(fp, encoding="utf-8", errors="ignore") as f:
                    dep_text += " " + f.read().lower()
            except Exception:
                pass

    project_tags = []
    if any(marker in dep_text for marker in AI_APP_DEP_MARKERS):
        project_tags.append("ai-app")
    if any(marker in dep_text for marker in MOBILE_DEP_MARKERS) or exists("pubspec.yaml"):
        project_tags.append("mobile")
    if os.path.isdir(os.path.join(root, ".xcodeproj")) or any(
        name.endswith(".xcodeproj") or name.endswith(".xcworkspace")
        for name in (os.listdir(root) if os.path.isdir(root) else [])
    ):
        if "mobile" not in project_tags:
            project_tags.append("mobile")
    has_bin_entry = bool(pkg_json is not None and pkg_json.get("bin"))
    has_console_scripts = "console_scripts" in dep_text or "[project.scripts]" in dep_text
    if has_bin_entry or has_console_scripts:
        project_tags.append("cli")

    ci = None
    if os.path.isdir(os.path.join(root, ".github", "workflows")):
        ci = "GitHub Actions"
    elif exists(".gitlab-ci.yml"):
        ci = "GitLab CI"
    elif os.path.isdir(os.path.join(root, ".circleci")):
        ci = "CircleCI"
    elif exists("Jenkinsfile"):
        ci = "Jenkins"
    elif exists("azure-pipelines.yml"):
        ci = "Azure Pipelines"

    docker = exists("Dockerfile") or exists("docker-compose.yml") or exists("docker-compose.yaml") or exists("compose.yml")

    tooling = detect_tooling(root, exists)
    commit_style = detect_commit_style(root)

    return {
        "languages": sorted(languages),
        "frameworks": sorted(frameworks),
        "package_managers": sorted(package_managers),
        "monorepo": monorepo_tool,
        "deployment": deployment,
        "project_tags": sorted(set(project_tags)),
        "ci": ci,
        "docker": docker,
        "tooling": tooling,
        "commit_style": commit_style,
    }


def detect_tooling(root, exists):
    lint = []
    fmt = []
    test = []

    for name in ("eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml"):
        if exists(name):
            lint.append("ESLint")
            break
    if exists("ruff.toml") or exists(".ruff.toml"):
        lint.append("Ruff")
    if exists(".flake8"):
        lint.append("Flake8")
    if exists(".pylintrc"):
        lint.append("Pylint")

    for name in (".prettierrc", ".prettierrc.json", ".prettierrc.js", ".prettierrc.yml"):
        if exists(name):
            fmt.append("Prettier")
            break
    if exists("rustfmt.toml") or exists(".rustfmt.toml"):
        fmt.append("rustfmt")

    for name in ("jest.config.js", "jest.config.ts", "jest.config.json"):
        if exists(name):
            test.append("Jest")
            break
    for name in ("vitest.config.js", "vitest.config.ts"):
        if exists(name):
            test.append("Vitest")
            break
    if exists("pytest.ini"):
        test.append("pytest")
    if exists("phpunit.xml") or exists("phpunit.xml.dist"):
        test.append("PHPUnit")

    # pyproject.toml/setup.cfg can configure black/ruff/pytest without a dedicated
    # dotfile -- checked once, cheaply, rather than re-opening the file per tool.
    for cfg_name in ("pyproject.toml", "setup.cfg"):
        cfg_path = os.path.join(root, cfg_name)
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, encoding="utf-8", errors="ignore") as f:
                    text = f.read().lower()
                if "[tool.black]" in text and "Black" not in fmt:
                    fmt.append("Black")
                if "[tool.ruff]" in text and "Ruff" not in lint:
                    lint.append("Ruff")
                if ("[tool.pytest" in text or "[tool:pytest]" in text) and "pytest" not in test:
                    test.append("pytest")
            except Exception:
                pass

    return {"lint": lint, "format": fmt, "test": test}


def detect_commit_style(root):
    try:
        result = subprocess.run(
            ["git", "log", "-n", "20", "--pretty=%s"],
            cwd=root, capture_output=True, text=True, timeout=5,
        )
        subjects = [line for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return None
    if len(subjects) < 5:
        return None  # too little history to call a convention "detected"
    matching = sum(1 for s in subjects if CONVENTIONAL_COMMIT_PATTERN.match(s))
    if matching / len(subjects) >= 0.6:
        return "Conventional Commits"
    return None


def claude_md_skeleton(repo_name, stack):
    lang = ", ".join(stack["languages"]) or "(not detected)"
    fw = ", ".join(stack["frameworks"]) or "(none detected)"
    pkg = ", ".join(stack["package_managers"]) or "(not detected)"
    mono = stack["monorepo"] or "no"
    deploy = stack["deployment"] or "(not detected)"
    tags = ", ".join(stack["project_tags"]) or "(none detected)"
    ci = stack["ci"] or "(not detected)"
    docker = "yes" if stack["docker"] else "no"
    tooling = stack["tooling"]
    lint = ", ".join(tooling["lint"]) or "(not detected)"
    fmt = ", ".join(tooling["format"]) or "(not detected)"
    test_fw = ", ".join(tooling["test"]) or "(not detected)"
    commit_style = stack["commit_style"] or "(no consistent convention detected)"
    return f"""# {repo_name}

<!-- Auto-bootstrapped stub. Fill in with project specifics as work happens. -->

## What this is

## Architecture

## Layout

## Commands

## Detected stack
- Language(s): {lang}
- Framework(s): {fw}
- Package manager: {pkg}
- Monorepo: {mono}
- Deployment: {deploy}
- Project tags: {tags}
- CI: {ci}
- Docker: {docker}
- Lint: {lint}
- Format: {fmt}
- Test framework: {test_fw}
- Commit style: {commit_style}

## Deployment

## Rules specific to this codebase
"""


TASK_MD_SKELETON = """# Tasks

## Active

<!-- Task(s) currently in progress. Overwrite in place as they change. -->

## Completed

<!-- Append-only, newest entry at the top. Never delete or rewrite an
entry here -- this is the full task/accountability trail for this repo,
from day one. Move a task here the moment it reaches a terminal Status. -->
"""


MEMORY_MD_SKELETON = """# Project Memory

<!-- Engineering-relevant facts and context worth persisting across sessions for
this repo. Distinct from Claude Code's own auto-memory index under
~/.claude/projects/<slug>/memory/ -- this file is checked into the repo. -->
"""

HANDOFF_MD_SKELETON = """# Handoff

<!-- Current-state snapshot. Overwrite in place each time it's updated --
this is status, not history (that's LOG.md and TASK.md's Completed section). -->

## Completed

<!-- Append-only history. Deliberately OUTSIDE the session-context markers
below -- SessionStart never re-injects this, same as TASK.md's own Completed
section. Read the file directly when full history is actually needed. -->

<!-- session-context:start -->
## Current Work

<!-- One line, pointing at the active task in TASK.md -- don't duplicate
its Goal/Input/Output/Constraints/Done Checks detail here. -->

## Pending

## Next Steps

## Open Questions
<!-- session-context:end -->
"""

LOG_MD_SKELETON = """# Log

<!-- Append new entries at the TOP, never rewrite old ones.
Format: ## YYYY-MM-DD HH:MM -->
"""

ISSUES_MD_SKELETON = """# Issues

<!-- Append-only, newest entry at the TOP, never rewrite old ones -- same discipline
as LOG.md. One entry per incident (the whole diagnose/fix sequence), written by the
Written once a bounded diagnose-fix-reverify loop reaches a terminal state.
Format: ## YYYY-MM-DD HH:MM -- <short symptom title>, fields per the ISSUES.md section
one entry per incident, newest first. Not preloaded at SessionStart -- read on demand. -->
"""

README_MD_SKELETON = """# README

<!-- Auto-bootstrapped stub. Fill in with a short project summary, how to run it,
and any repository-specific conventions. -->

## What this is

## Getting started

## Commands

## Conventions

## Notes
"""

DECISIONS_README_SKELETON = """# Decisions

One file per non-obvious decision. Only add an entry for choices that
aren't already spelled out elsewhere and could plausibly be redone
differently later.

Format for each decision file:

## Decision
What was decided.

## Why
Rationale.

## Alternatives considered
What else was on the table and why it lost.
"""

DOCS_PLANS_README_SKELETON = """# Plans

Feature plans, delivery sequences, and implementation notes go in this
folder. Create one file per feature under `docs/plans/`.
"""

DOCS_ARCHIVE_README_SKELETON = """# Archive

Retired designs, archived decisions, and deprecated notes live here.
"""


def write_if_missing(path, content):
    if os.path.isfile(path):
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def parse_active_tasks(task_md_path):
    if not os.path.isfile(task_md_path):
        return ""
    with open(task_md_path, encoding="utf-8") as f:
        text = f.read()
    match = re.search(r"(?ms)^## Active\s*\n(.*?)(?=^## Completed\b|\Z)", text)
    if match is None:
        return text  # older TASK.md without the Active/Completed split -- load as-is
    return match.group(1).strip()


def parse_active_task_pointers(task_md_path, max_status_chars=200):
    """Name + one-line status per active task -- not the full Goal/Input/
    Output/Constraints/Done Checks/Out of Scope detail, which stays a Read
    away instead of being paid on every SessionStart."""
    active_text = parse_active_tasks(task_md_path)
    if not active_text.strip():
        return ""
    pointers = []
    for block in re.split(r"(?m)^## (?=\S)", active_text):
        block = block.strip()
        if not block:
            continue
        name, _, rest = block.partition("\n")
        status_match = re.search(r"(?ms)^-\s*\*\*Status\*\*:\s*(.*?)(?=^-\s*\*\*|\Z)", rest)
        status = " ".join(status_match.group(1).split()) if status_match else "(no Status field)"
        if len(status) > max_status_chars:
            status = status[:max_status_chars].rstrip() + "..."
        pointers.append(f"- {name.strip()} -- Status: {status}")
    return "\n".join(pointers)


def parse_handoff_status(handoff_path):
    """Prefer the explicit <!-- session-context:start/end --> markers --
    robust against any future section added elsewhere in the file (a rogue
    section once rode along with a "Current Work onward" heuristic; a tagged
    boundary can't be fooled that way). Falls back to that same "Current Work
    onward" heuristic for older HANDOFF.md files written before the marker
    convention existed."""
    if not os.path.isfile(handoff_path):
        return ""
    with open(handoff_path, encoding="utf-8") as f:
        text = f.read()
    tagged = re.search(
        r"(?ms)^<!--\s*session-context:start\s*-->\s*\n(.*?)\n^<!--\s*session-context:end\s*-->",
        text,
    )
    if tagged is not None:
        return _clip(tagged.group(1).strip(), HANDOFF_BUDGET, "HANDOFF.md")
    match = re.search(r"(?ms)^## Current Work\s*\n.*\Z", text)
    if match is None:
        # Older/unrecognised format. Falling back to the whole file is right --
        # something is better than nothing -- but it must still be budgeted, or
        # an unmarked HANDOFF.md injects itself entirely.
        return _clip(text, HANDOFF_BUDGET, "HANDOFF.md")
    return _clip(match.group(0).strip(), HANDOFF_BUDGET, "HANDOFF.md")


# Character budgets for what this hook injects at session start.
#
# Measured 2026-08-02: the payload was 26,990 chars (~6,750 tokens) spent before
# the user had typed anything, because both parsers below were uncapped -- five
# whole LOG entries plus everything in HANDOFF.md from "Current Work" onward.
# Long entries are good writing and bad context; the fix is a budget here, not
# shorter entries.
#
# Truncation always names the file, so the full text stays one Read away. An
# injected summary is a pointer, never a replacement.
HANDOFF_BUDGET = 2400
LOG_ENTRY_BUDGET = 700
LOG_TOTAL_BUDGET = 2400
LOG_ENTRIES = 3


def _clip(text, budget, what):
    if len(text) <= budget:
        return text
    return text[:budget].rstrip() + f"\n[... clipped, Read {what} for the rest]"


def parse_last_n_log_entries(log_path, n=LOG_ENTRIES):
    if not os.path.isfile(log_path):
        return ""
    with open(log_path, encoding="utf-8") as f:
        text = f.read()
    parts = re.split(r"(?m)^(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}.*)$", text)
    entries = []
    i = 1
    while i < len(parts) - 1:
        entries.append(_clip(parts[i] + parts[i + 1], LOG_ENTRY_BUDGET, "LOG.md"))
        i += 2
    return _clip("".join(entries[:n]), LOG_TOTAL_BUDGET, "LOG.md")


def _parse_env_file(path):
    """Return {key: value} for non-comment lines. Values are never logged
    or surfaced anywhere -- only key names and whether a value is blank."""
    values: dict[str, str] = {}
    if not os.path.isfile(path):
        return values
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def check_env_setup(root):
    """If .env.example exists, report which of its (non-optional, i.e. not
    commented-out) keys are missing or still blank in .env. Never reads or
    reports actual secret values -- key names only."""
    example_path = os.path.join(root, ".env.example")
    if not os.path.isfile(example_path):
        return []
    example_keys = _parse_env_file(example_path)
    actual = _parse_env_file(os.path.join(root, ".env"))
    return [key for key in example_keys if not actual.get(key)]


def is_stub_claude_md(path):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            return "Auto-bootstrapped stub" in f.read()
    except Exception:
        return False


def list_decisions(root):
    decisions_dir = os.path.join(root, "decisions")
    if not os.path.isdir(decisions_dir):
        return []
    return sorted(
        name for name in os.listdir(decisions_dir)
        if name.endswith(".md") and name != "README.md"
    )


def main():
    # Consume the standard Claude Code payload even though this hook's current
    # policy is identical for startup, resume, and compact events.
    load_payload()
    root = find_git_root(os.getcwd())
    if root is None:
        return

    missing_docs = [
        name for name in BOOTSTRAP_FILES
        if not os.path.isfile(os.path.join(root, name))
    ]
    missing_dirs = [
        name for name in ("decisions", "docs", "docs/plans", "docs/archive")
        if not os.path.isdir(os.path.join(root, name))
    ]

    missing_env_keys = check_env_setup(root)

    sections = []
    if missing_env_keys:
        sections.append(
            "--- Setup checklist ---\n"
            "This repo has a .env.example with keys not yet set in .env: "
            + ", ".join(missing_env_keys)
            + ". Remind the user at a convenient point (not necessarily now) -- "
            "never fill these in yourself, they're the user's own credentials."
        )
    if missing_docs or missing_dirs:
        sections.append(
            "--- Documentation drift detected (read-only) ---\n"
            f"Missing strategic documents: {', '.join(missing_docs) or 'none'}. "
            f"Missing directories: {', '.join(missing_dirs) or 'none'}. "
            "Route the repair to the documented owner; this hook never writes "
            "strategic content."
        )

    claude_md_path = os.path.join(root, "CLAUDE.md")
    if is_stub_claude_md(claude_md_path):
        sections.append(
            "--- CLAUDE.md is still a stub ---\n"
            "This repo's CLAUDE.md hasn't been filled in yet (still the auto-generated "
            "skeleton). Once there's enough context about this repo, fill it in with "
            "real project specifics — commands, layout, gotchas, and hard rules."
        )
    # Full CLAUDE.md content is deliberately NOT injected here -- Claude Code
    # already auto-loads project CLAUDE.md on its own for every session, so
    # re-reading and re-printing it here would just duplicate that context.

    active_pointers = parse_active_task_pointers(os.path.join(root, "TASK.md"))
    if active_pointers:
        sections.append(
            "--- TASK.md (Active -- name + status only; Read the file for "
            "full Goal/Input/Output/Constraints/Done Checks/Out of Scope "
            "detail) ---\n" + active_pointers
        )

    handoff_path = os.path.join(root, "HANDOFF.md")
    handoff_status = parse_handoff_status(handoff_path)
    if handoff_status.strip():
        sections.append(
            "--- HANDOFF.md (Current Work / Pending / Next Steps / Open "
            "Questions -- Read the file for the full Completed history) ---\n"
            + handoff_status
        )

    # No explicit n: the budget lives with the parser, next to the other three
    # constants. Passing n=5 here silently overrode LOG_ENTRIES and shipped four
    # entries under a header claiming five -- caught by running the hook.
    last_logs = parse_last_n_log_entries(os.path.join(root, "LOG.md"))
    if last_logs.strip():
        sections.append(
            f"--- LOG.md (last {LOG_ENTRIES} entries, clipped) ---\n" + last_logs)

    decision_files = list_decisions(root)
    if decision_files:
        sections.append(
            "--- decisions/ (filenames only, read on demand if relevant) ---\n"
            + "\n".join(decision_files)
        )

    if sections:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n\n".join(sections),
            }
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
