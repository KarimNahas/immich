#!/usr/bin/env python3
"""Verify the fork after a rebase: types, upstream tests, and the fork's own behaviour test.

    python3 .claude/skills/updating-immich-fork/scripts/verify.py
    python3 .claude/skills/updating-immich-fork/scripts/verify.py --skip-install
    python3 .claude/skills/updating-immich-fork/scripts/verify.py --update-expected

The database-backed tests start a throwaway Postgres container, so Docker must be running.
They never touch the real Immich database.

A test failure is only a problem if it is not listed in ../expected-failures.txt.
Unexpected failures are retried up to three times, because some upstream tests are flaky.
Exit codes: 0 = verified, 1 = regressions or failed checks, 2 = could not run.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip())
EXPECTED = Path(__file__).resolve().parent.parent / "expected-failures.txt"
FORK_SPECS = "test/medium/specs/fork/"
WORKSPACE_PACKAGES = ["packages/sdk", "packages/plugin-sdk"]
KINDS = ("unit", "medium", "web")


def pnpm():
    """The repo pins a pnpm version that the locally installed pnpm may be unable to switch to."""
    pinned = json.loads((ROOT / "package.json").read_text()).get("packageManager", "pnpm").split("+")[0]
    return ["npx", "-y", pinned]


# Upstream's tests assume the CI machine's settings; a different locale changes date formats.
CI_ENV = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "TZ": "UTC"}


def run(cmd, cwd, capture=False):
    print(f"\n$ {' '.join(cmd)}   (in {Path(cwd).relative_to(ROOT) or '.'})", flush=True)
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture, env=CI_ENV)


def load_expected():
    entries = {"unit": set(), "medium": set(), "web": set(), "env": set(), "tsc": set(), "skip": []}
    if EXPECTED.exists():
        for line in EXPECTED.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            kind, path, rest = [part.strip() for part in line.split("|", 2)]
            if kind == "skip":
                entries["skip"].append(path)
            elif kind == "tsc":
                entries["tsc"].add(path)
            else:
                entries[kind].add(f"{path} | {rest}")
    return entries


SUITES = {
    "unit": ("server", ["--config", "test/vitest.config.mjs"]),
    "medium": ("server", ["--config", "test/vitest.config.medium.mjs"]),
    "web": ("web", []),
}


def vitest(kind, excludes=(), files=()):
    folder, config = SUITES[kind]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "result.json"
        cmd = ["./node_modules/.bin/vitest", *config, "run", *files, "--reporter=json", f"--outputFile={out}"]
        for pattern in excludes:
            cmd += ["--exclude", pattern]
        result = run(cmd, ROOT / folder, capture=True)
        if not out.exists():
            print(result.stdout[-3000:], result.stderr[-3000:])
            raise SystemExit(f"{kind} tests did not produce a result; is Docker running and are dependencies installed?")
        data = json.loads(out.read_text())
        if data["numTotalTests"] == 0:
            print(result.stdout[-3000:], result.stderr[-3000:])
            raise SystemExit(f"{kind} tests ran zero tests; the run is not a verification")
    failed, passed, broken_files = set(), set(), []
    for suite in data["testResults"]:
        path = suite["name"].split(f"/{folder}/")[-1]
        results = suite["assertionResults"]
        if suite["status"] == "failed" and not any(a["status"] == "failed" for a in results):
            broken_files.append(path)
        for assertion in results:
            key = f"{path} | {assertion['fullName']}"
            (failed if assertion["status"] == "failed" else passed).add(key)
    print(f"{kind}: {data['numPassedTests']} passed, {data['numFailedTests']} failed, {len(broken_files)} files failed to load")
    return failed, passed, broken_files


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-install", action="store_true", help="dependencies and workspace packages are already built")
    parser.add_argument("--skip-web", action="store_true", help="skip the web type checks")
    parser.add_argument("--skip-db", action="store_true", help="skip the database-backed tests (no Docker needed)")
    parser.add_argument("--update-expected", action="store_true", help="rewrite expected-failures.txt from this run; only after reading every new failure")
    args = parser.parse_args()

    expected = load_expected()
    problems = []

    if not args.skip_install:
        if run(pnpm() + ["install", "--frozen-lockfile", "--filter", "immich...", "--filter", "immich-web..."], ROOT).returncode:
            raise SystemExit("dependency install failed")
        for package in WORKSPACE_PACKAGES:
            manifest = ROOT / package / "package.json"
            if manifest.exists() and "build" in json.loads(manifest.read_text()).get("scripts", {}):
                if run(pnpm() + ["run", "build"], ROOT / package).returncode:
                    raise SystemExit(f"building {package} failed")

    tsc = run(["./node_modules/.bin/tsc", "--noEmit"], ROOT / "server", capture=True)
    errors = [line for line in tsc.stdout.splitlines() if re.match(r"^\S+\(\d+,\d+\): error", line)]
    unexpected = [line for line in errors if line.split("(")[0] not in expected["tsc"]]
    print(f"server types: {len(errors)} errors, {len(unexpected)} outside the files listed as expected")
    if unexpected:
        problems.append("server type errors:\n    " + "\n    ".join(unexpected[:40]))

    if not args.skip_web:
        if run(pnpm() + ["run", "check:svelte"], ROOT / "web").returncode:
            problems.append("web: svelte-check failed")
        if run(["./node_modules/.bin/tsc", "--noEmit"], ROOT / "web").returncode:
            problems.append("web: tsc failed")

    results = {"unit": vitest("unit")}
    if not args.skip_web:
        results["web"] = vitest("web")
    if not args.skip_db:
        results["medium"] = vitest("medium", expected["skip"])

    for kind, (failed, passed, broken) in results.items():
        intended = expected[kind] | expected["env"]
        new = sorted(failed - intended)
        for attempt in (1, 2, 3):
            if not new:
                break
            files = sorted({key.split(" | ")[0] for key in new})
            print(f"\n{kind}: {len(new)} unexpected failures, retry {attempt}/3 of {len(files)} file(s) to rule out flaky tests")
            retry_failed, _, _ = vitest(kind, files=files)
            flaky = [key for key in new if key not in retry_failed]
            if flaky:
                print(f"{kind}: passed on retry, treated as flaky:\n    " + "\n    ".join(flaky))
            new = [key for key in new if key in retry_failed]
        fixed = sorted(expected[kind] & passed)
        gone = sorted(expected[kind] - failed - passed)
        if new:
            problems.append(f"{kind}: {len(new)} NEW failures (regressions until proven intended):\n    " + "\n    ".join(new))
        if broken:
            problems.append(f"{kind}: files that failed to load:\n    " + "\n    ".join(broken))
        if fixed:
            print(f"\n{kind}: {len(fixed)} expected failures now PASS (upstream may have caught up, or the fork lost a behaviour):")
            print("    " + "\n    ".join(fixed))
        if gone:
            print(f"\n{kind}: {len(gone)} expected failures no longer exist (renamed or removed upstream):")
            print("    " + "\n    ".join(gone))

    if "medium" in results:
        failed, passed, _ = results["medium"]
        fork_tests = [key for key in passed | failed if key.startswith(FORK_SPECS)]
        fork_failed = [key for key in failed if key.startswith(FORK_SPECS)]
        print(f"\nfork behaviour tests: {len(fork_tests) - len(fork_failed)}/{len(fork_tests)} passed")
        if not fork_tests:
            problems.append(f"fork behaviour tests did not run: {FORK_SPECS}")

    if args.update_expected:
        lines = EXPECTED.read_text().splitlines()
        header = [line for line in lines if line.startswith("#")]
        keep = [line for line in lines if line.split("|")[0].strip() in ("tsc", "skip", "env")]
        body = []
        for kind in KINDS:
            failed = results[kind][0] - expected["env"] if kind in results else expected[kind]
            body += [f"{kind} | {key}" for key in sorted(failed)]
        EXPECTED.write_text("\n".join(header + [""] + keep + [""] + body) + "\n")
        print(f"\nrewrote {EXPECTED.relative_to(ROOT)} with {len(body)} expected failures")
        return 0

    print("\n" + "=" * 60)
    if problems:
        print("NOT VERIFIED")
        for problem in problems:
            print(f"- {problem}")
        return 1
    skipped = [name for name, flag in (("web", args.skip_web), ("database tests", args.skip_db)) if flag]
    if skipped:
        print(f"PARTIAL: nothing failed, but {' and '.join(skipped)} were skipped, so this is not a full verification")
        return 1
    print("VERIFIED: types pass, no failures beyond the expected list, fork behaviour tests pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
