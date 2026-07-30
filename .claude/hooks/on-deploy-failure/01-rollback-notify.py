"""on-deploy-failure -- a failed deploy, i.e. a rollback candidate.

Same two-caller shape as on-validate-fail: it filters failed tool calls down to
deploy-CLI commands itself, and skips that check when a deploy pipeline invokes
it directly with an explicit `target`.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import command_of, load_payload, write_log  # noqa: E402

DEPLOY_RE = re.compile(
    r"\b(vercel|netlify|flyctl|railway|supabase|doctl|heroku|aws|gcloud|az|"
    r"kubectl|docker\s+push|terraform\s+apply)\b"
)


def main():
    payload = load_payload()
    if payload.get("is_interrupt"):
        return

    invoked_by_pipeline = "target" in payload
    if not invoked_by_pipeline and not DEPLOY_RE.search(command_of(payload)):
        return

    write_log("deploy-fail.log", "DEPLOY-FAIL", payload)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
