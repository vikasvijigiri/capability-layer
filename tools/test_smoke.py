#!/usr/bin/env python3
"""Tests for tools/smoke.py -- the only check that starts the thing.

Everything else in this repository reads the source. This one boots a process and
asks it a question, so its failure modes are timing, not syntax -- and the one
that mattered was impatience.

`while ... : status, body = probe(); if status is not None: break` treated ANY
response as the answer. A proxy in front of a warming backend replies 502
immediately, so the loop ended at second one with the entire timeout unspent and
reported "expected 200, got 502" -- which reads as a broken deploy rather than a
check that did not wait. Retrying a 500 would be the opposite error, since that is
the application's own reply and will not improve.

Run: python tools/test_smoke.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sm = load("tools/smoke.py", "smoke_mod")


# --- the classification, which is the whole fix ------------------------------

check("502 is retryable -- a gateway saying the backend is not up yet",
      502 in sm.RETRYABLE_STATUS)
check("503 is retryable", 503 in sm.RETRYABLE_STATUS)
check("504 is retryable", 504 in sm.RETRYABLE_STATUS)
check("429 is retryable -- rate limiting during warm-up is not a deploy failure",
      429 in sm.RETRYABLE_STATUS)

check("500 is NOT retryable -- that is the app's own reply",
      500 not in sm.RETRYABLE_STATUS,
      "retrying it delays the same failure and hides it behind a timeout")
check("404 is NOT retryable -- a missing route will not start existing",
      404 not in sm.RETRYABLE_STATUS)
check("200 is NOT retryable", 200 not in sm.RETRYABLE_STATUS)
check("the retryable set is narrow", len(sm.RETRYABLE_STATUS) <= 6,
      f"{sorted(sm.RETRYABLE_STATUS)} -- a wide set turns real errors into hangs")


# --- against a real server that is 503 before it is 200 ----------------------
#
# The regression this exists for cannot be seen without a process: it is about
# WHEN the loop stops, not about what any single function returns.

SERVER = textwrap.dedent('''
    import http.server, sys, threading, time
    READY_AFTER = float(sys.argv[2])
    started = time.time()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if time.time() - started < READY_AFTER:
                self.send_response(503)          # the gateway: not yet
                self.end_headers()
                self.wfile.write(b"warming")
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        def log_message(self, *a): pass

    http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
''')

work = Path(tempfile.mkdtemp())
(work / "server.py").write_text(SERVER, encoding="utf-8")


def run_smoke(port: int, ready_after: float, expect: int = 200, timeout: int = 20):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "smoke.py"),
         "--start", f'"{sys.executable}" server.py {port} {ready_after}',
         "--url", f"http://127.0.0.1:{port}/",
         "--expect-status", str(expect),
         "--timeout", str(timeout), "--cwd", str(work)],
        capture_output=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, timeout=timeout + 60,
    )


slow = run_smoke(port=8731, ready_after=3.0)
check("a server that 503s for 3s then serves 200 SMOKES GREEN",
      slow.returncode == 0,
      (slow.stdout + slow.stderr).strip()[-200:])
check("...and it says it retried, rather than waiting silently",
      "retrying" in slow.stdout, slow.stdout.strip()[-200:])
check("...and reports how long it actually waited",
      "answered after" in slow.stdout, slow.stdout.strip()[-160:])

fast = run_smoke(port=8732, ready_after=0.0)
check("a server that is ready immediately still passes",
      fast.returncode == 0, (fast.stdout + fast.stderr).strip()[-200:])

# The opposite error: a non-retryable status must fail FAST, not burn the budget.
never = run_smoke(port=8733, ready_after=999.0, expect=200, timeout=6)
check("a server stuck on 503 eventually fails rather than passing",
      never.returncode != 0, (never.stdout + never.stderr).strip()[-160:])

dead = subprocess.run(
    [sys.executable, str(ROOT / "tools" / "smoke.py"),
     "--start", f'"{sys.executable}" -c "import sys; sys.exit(3)"',
     "--url", "http://127.0.0.1:8734/", "--timeout", "10", "--cwd", str(work)],
    capture_output=True, encoding="utf-8", errors="replace",
    stdin=subprocess.DEVNULL, timeout=90)
check("a server that exits before answering is reported as that, not as a timeout",
      dead.returncode != 0 and "exited before answering" in (dead.stdout + dead.stderr),
      (dead.stdout + dead.stderr).strip()[-160:])

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All smoke tests passed")
