#!/usr/bin/env python3
"""Start the app, wait for it to answer, probe it, shut it down.

The gap this closes
-------------------
Every other check in this repo verifies the *source*: it lints, it typechecks, it
runs unit tests, it builds. None of them ever started the thing. That is the
single most-cited failure mode for coding agents in production -- they "run in
code-only sandboxes that can't deploy to real environments or verify that the
code actually works", so they ship code that compiles, tests green, and does not
boot.

`releasing` has mandated a smoke check since it was written and had no mechanism
to perform one. This is the mechanism.

Language-agnostic by construction: it knows how to run a command, poll a URL and
kill a process tree. It does not know or care what the app is written in.

Usage
-----
    python tools/smoke.py --start "npm run dev" --url http://localhost:3000
    python tools/smoke.py --start "uvicorn app:app --port 8000" \
                          --url http://localhost:8000/health \
                          --expect-status 200 --expect-text '"ok"' --timeout 90

Exit 0 only if the server came up AND every probe passed. Anything else is a
non-zero exit with the reason on stderr -- including the server's own last output,
because "it did not start" is useless without knowing why.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

DEFAULT_TIMEOUT = 60
POLL_INTERVAL = 0.5

# Gateway statuses that mean "the thing behind me is not ready", as opposed to an
# answer from the application. Kept narrow on purpose: a 500 is the app's own
# reply and retrying it only delays the same failure, while a 404 means the route
# does not exist and will not start existing.
RETRYABLE_STATUS = frozenset({502, 503, 504, 429})


def kill_tree(proc: subprocess.Popen) -> None:
    """Kill the server and anything it spawned.

    `npm run dev` is a shell that spawns node; killing the shell orphans the
    server, it keeps the port, and the next run fails to bind with an error that
    blames the wrong thing. On POSIX the process group handles it; on Windows
    `taskkill /T` is the only reliable way.
    """
    if proc.poll() is not None:
        return
    # `sys.platform`, not `os.name`: mypy narrows the first and not the second,
    # so this is the difference between clean cross-platform code and six
    # `type: ignore`s that then fire as *unused* on the other platform.
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=20)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception as exc:  # noqa: BLE001 -- reported, never fatal
        print(f"warning: could not fully stop the server: {exc}", file=sys.stderr)


def probe(url: str, timeout: float = 10):
    """(status, body) or (None, error-string). Never raises."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return resp.status, resp.read(20000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        # An HTTP error is still an answer -- a 500 means the server is up and
        # broken, which is a different finding from "nothing is listening".
        return exc.code, exc.read(20000).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", help="command that starts the server; omit if already running")
    ap.add_argument("--url", required=True, help="URL to probe once it is up")
    ap.add_argument("--expect-status", type=int, default=200)
    ap.add_argument("--expect-text", default=None,
                    help="substring the response body must contain")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="seconds to wait for the server to answer at all")
    ap.add_argument("--cwd", default=".")
    args = ap.parse_args()

    proc = None
    if args.start:
        print(f"starting: {args.start}")
        popen_kwargs: dict = {}
        if sys.platform != "win32":
            # New process group, so kill_tree can take the whole tree down.
            popen_kwargs["preexec_fn"] = os.setsid
        proc = subprocess.Popen(  # noqa: S602 -- the command is the caller's own
            args.start, shell=True, cwd=args.cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", **popen_kwargs,
        )

    try:
        deadline = time.time() + args.timeout
        status = body = None
        while time.time() < deadline:
            if proc is not None and proc.poll() is not None:
                out = (proc.stdout.read() if proc.stdout else "") or ""
                print(f"FAIL: the server exited before answering "
                      f"(code {proc.returncode}).\n--- its output ---\n{out[-2000:]}",
                      file=sys.stderr)
                return 1
            status, body = probe(args.url)
            # A response is not the same as THE response. `status is not None`
            # used to break the loop, so a proxy answering 502 while the backend
            # was still warming ended the poll at second one with the whole
            # timeout unspent -- and reported it as "expected 200, got 502",
            # which reads as a broken deploy rather than an impatient check.
            #
            # These four are the gateway's way of saying "not yet". Anything else,
            # including a 500 from the app itself, is an answer and is taken as
            # one: retrying a real error just delays the same failure.
            if status is not None and status not in RETRYABLE_STATUS:
                break
            if status is not None:
                print(f"  {status} -- retrying, {deadline - time.time():.0f}s left")
            time.sleep(POLL_INTERVAL)

        if status is None:
            print(f"FAIL: nothing answered at {args.url} within {args.timeout}s "
                  f"-- last error: {body}", file=sys.stderr)
            return 1

        waited = args.timeout - max(0.0, deadline - time.time())
        print(f"answered after {waited:.1f}s with HTTP {status}")

        if status != args.expect_status:
            print(f"FAIL: expected HTTP {args.expect_status}, got {status}\n"
                  f"--- body ---\n{(body or '')[:1000]}", file=sys.stderr)
            return 1

        if args.expect_text and args.expect_text not in (body or ""):
            print(f"FAIL: body does not contain {args.expect_text!r}\n"
                  f"--- body ---\n{(body or '')[:1000]}", file=sys.stderr)
            return 1

        print(f"SMOKE OK: {args.url} -> {status}"
              + (f", body contains {args.expect_text!r}" if args.expect_text else ""))
        return 0
    finally:
        if proc is not None:
            kill_tree(proc)


if __name__ == "__main__":
    sys.exit(main())
