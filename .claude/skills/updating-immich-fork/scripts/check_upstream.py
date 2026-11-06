#!/usr/bin/env python3
"""Check whether upstream Immich has a newer release than this fork is based on.

Read-only apart from `git fetch` (skip with --no-fetch). Run from anywhere inside the repo:

    python3 .claude/skills/updating-immich-fork/scripts/check_upstream.py
    python3 .claude/skills/updating-immich-fork/scripts/check_upstream.py --forecast
    python3 .claude/skills/updating-immich-fork/scripts/check_upstream.py --target v3.4.0 --since v2.6.3

Exit codes: 0 = on the latest release, 10 = newer release available,
11 = no newer release but the fork is not based on a release, 2 = error.
"""

import argparse
import datetime as dt
import json
import re
import subprocess
import sys

UPSTREAM_URL = "https://github.com/immich-app/immich.git"
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")
DESTRUCTIVE_RE = re.compile(r"\b(DELETE\s+FROM|DROP\s+TABLE|DROP\s+COLUMN|TRUNCATE|UPDATE\s+\S+\s+SET)\b[^;`]*", re.I)
STATEMENT_RE = re.compile(r"sql`(.*?)`", re.S)
FUNCTION_BODY_RE = re.compile(r"\$\$.*?\$\$", re.S)
MIGRATIONS_DIR = "server/src/schema/migrations"


def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def version_key(tag):
    """Semver ordering: 3.4.0-rc.1 < 3.4.0-rc.2 < 3.4.0."""
    major, minor, patch, pre = TAG_RE.match(tag).groups()
    if pre is None:
        pre_key = (1,)
    else:
        parts = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split("."))
        pre_key = (0, parts)
    return (int(major), int(minor), int(patch), pre_key)


def is_stable(tag):
    return TAG_RE.match(tag).group(4) is None


def release_tags():
    return [t for t in git("tag", "-l", "v[0-9]*").splitlines() if TAG_RE.match(t)]


def tag_date(tag):
    return dt.date.fromisoformat(git("log", "-1", "--format=%cs", tag))


def fork_state():
    """The fork is a linear stack of commits that exist on no upstream ref."""
    commits = git("rev-list", "--reverse", "HEAD", "--not", "--remotes=upstream", "--tags=v[0-9]*").splitlines()
    base = git("rev-parse", f"{commits[0]}^") if commits else git("rev-parse", "HEAD")
    merged = [t for t in git("tag", "--merged", base, "-l", "v[0-9]*").splitlines() if TAG_RE.match(t)]
    base_tag = max(merged, key=version_key) if merged else None
    unreleased = int(git("rev-list", "--count", f"{base_tag}..{base}")) if base_tag else 0
    return {"commits": commits, "base": base, "base_tag": base_tag, "unreleased": unreleased}


def destructive_migrations(since, target):
    """Migrations present at `target` but not at `since` whose up() deletes, drops or rewrites data."""
    added = git("diff", "--name-only", "--diff-filter=A", since, target, "--", MIGRATIONS_DIR).splitlines()
    found = []
    for path in sorted(p for p in added if p.endswith(".ts")):
        source = git("show", f"{target}:{path}")
        up = re.search(r"export async function up\b.*?(?=export async function down\b|\Z)", source, re.S)
        statements = set()
        for sql in STATEMENT_RE.findall(up.group(0) if up else source):
            # bookkeeping rows and trigger/function bodies do nothing to existing data when the migration runs
            if "migration_overrides" in sql:
                continue
            for match in DESTRUCTIVE_RE.finditer(FUNCTION_BODY_RE.sub("", sql)):
                statements.add(" ".join(match.group(0).split())[:150])
        statements = sorted(statements)
        if statements:
            found.append({"file": path.rsplit("/", 1)[-1], "statements": statements})
    return {"added": len(added), "destructive": found}


def forecast(state, target, since):
    base, tip = state["base"], "HEAD"
    fork_files = set(git("diff", "--name-only", base, tip).splitlines())
    upstream_files = set(git("diff", "--name-only", base, target).splitlines())
    merge = subprocess.run(
        ["git", "merge-tree", "--write-tree", "--name-only", f"--merge-base={base}", target, tip],
        capture_output=True,
        text=True,
    )
    lines = merge.stdout.split("\n\n", 1)[0].splitlines()[1:]
    conflicts = sorted(set(lines)) if merge.returncode == 1 else []
    silently_merged = sorted((fork_files & upstream_files) - set(conflicts))
    return {
        "target": target,
        "upstream_commits_gained": int(git("rev-list", "--count", f"{base}..{target}")),
        "upstream_commits_dropped": int(git("rev-list", "--count", f"{target}..{base}")),
        "fork_files": len(fork_files),
        "conflicts": conflicts,
        "auto_merged_review": silently_merged,
        "migrations_since": since,
        "migrations": destructive_migrations(since, target),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-fetch", action="store_true", help="use the tags already fetched; do not contact upstream")
    parser.add_argument("--channel", choices=["stable", "rc"], default="stable", help="which releases count (default: stable)")
    parser.add_argument("--target", help="release tag to evaluate instead of the latest one")
    parser.add_argument("--forecast", action="store_true", help="trial-merge the fork onto the target and scan new migrations")
    parser.add_argument("--since", help="tag or commit the DEPLOYED build was based on; migrations are scanned from there. Default: the fork's current base")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    git("rev-parse", "--show-toplevel")
    if not args.no_fetch:
        if git("remote", "get-url", "upstream", check=False) == "":
            git("remote", "add", "upstream", UPSTREAM_URL)
        git("fetch", "--quiet", "upstream", "main", "--tags")

    tags = release_tags()
    if not tags:
        raise SystemExit("No upstream release tags found. Run without --no-fetch.")
    candidates = tags if args.channel == "rc" else [t for t in tags if is_stable(t)]
    latest = max(candidates, key=version_key)
    target = args.target or latest
    if target not in tags:
        raise SystemExit(f"Unknown release tag: {target}")

    state = fork_state()
    base_tag = state["base_tag"]
    on_release = base_tag is not None and state["unreleased"] == 0
    newer = base_tag is None or version_key(target) > version_key(base_tag)
    if on_release and base_tag == target:
        status, code = "up-to-date", 0
    elif newer:
        status, code = "update-available", 10
    else:
        status, code = "off-release", 11

    report = {
        "status": status,
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "fork_commits": len(state["commits"]),
        "base": state["base"][:9],
        "base_tag": base_tag,
        "unreleased_upstream_commits_in_base": state["unreleased"],
        "latest": latest,
        "target": target,
        "target_released": tag_date(target).isoformat(),
        "days_since_target_release": (dt.date.today() - tag_date(target)).days,
        "release_notes": f"https://github.com/immich-app/immich/releases/tag/{target}",
    }
    if base_tag:
        b, t = version_key(base_tag), version_key(target)
        report["jump"] = "major" if t[0] != b[0] else "minor" if t[1] != b[1] else "patch"
    if args.forecast or args.target:
        report["forecast"] = forecast(state, target, args.since or state["base"])

    if args.json:
        print(json.dumps(report, indent=2))
        return code

    based_on = f"{base_tag}" + (f" + {state['unreleased']} unreleased upstream commits" if state["unreleased"] else "")
    print(f"Fork branch {report['branch']}: {report['fork_commits']} fork commits on top of {based_on} ({report['base']})")
    if status == "up-to-date":
        print(f"UP TO DATE: {target} is the latest {args.channel} release.")
    elif status == "update-available":
        print(f"UPDATE AVAILABLE: {target} ({report.get('jump', 'new')} update), released {report['target_released']}, {report['days_since_target_release']} days ago.")
        print(f"Release notes: {report['release_notes']}")
    else:
        print(f"NO NEWER {args.channel.upper()} RELEASE: latest is {latest} ({report['target_released']}), which is older than the fork's base.")
        print(f"The fork is not based on a release. Do not deploy it. Move it onto {latest}, even though that is older:")
        print(f"  forecast with: check_upstream.py --target {latest} --since <base of the deployed build>")

    if "forecast" in report:
        f = report["forecast"]
        print(f"\nForecast for moving the fork onto {target}:")
        print(f"  upstream commits gained: {f['upstream_commits_gained']}, dropped: {f['upstream_commits_dropped']}")
        print(f"  files that will CONFLICT ({len(f['conflicts'])}):")
        for path in f["conflicts"]:
            print(f"    {path}")
        print(f"  files git will merge SILENTLY - review each one ({len(f['auto_merged_review'])}):")
        for path in f["auto_merged_review"]:
            print(f"    {path}")
        m = f["migrations"]
        print(f"  new migrations since {f['migrations_since'][:12]}: {m['added']}, of which delete, drop or rewrite data: {len(m['destructive'])}")
        for item in m["destructive"]:
            print(f"    {item['file']}")
            for statement in item["statements"]:
                print(f"      {statement}")
    return code


if __name__ == "__main__":
    sys.exit(main())
