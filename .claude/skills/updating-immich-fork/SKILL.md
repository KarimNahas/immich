---
name: updating-immich-fork
description: Use when asked to check for updates or whether upstream Immich has a new version, or to update, rebase, sync or upgrade this fork (branch feat/uniform-meta) onto a newer immich-app/immich release, or when such a rebase hits conflicts, failing tests, or migration questions before deployment. Also when adding, changing or dropping one of the fork's behaviours.
---

# Updating the Immich fork

The fork is a short stack on top of an upstream **stable release tag**: one commit per behaviour
(code + its page in `fork/` + its test in `server/test/medium/specs/fork/`), then one commit with
this workflow. Port the intent written in `fork/*.md`, never the old diff. Stay close to
upstream. `scripts/verify.py` decides whether it worked.

Script paths below are relative to `.claude/skills/updating-immich-fork/`.

## Check for updates

Run `python3 scripts/check_upstream.py` and give the user its status line. Stop there unless
asked to update. If it says the fork is **not based on a release**, the target is the latest
stable tag even though that is older than the current base.

## Update

1. **Read `fork/README.md` and every page in `fork/`.** Working tree must be clean.
2. **Forecast.** `python3 scripts/check_upstream.py --target <tag> --since <deployed base>`.
   `<deployed base>` is the tag or commit the build now running was made from, not just the
   version number it reports; ask the user if unknown. Note the `base` commit the script prints.
3. **Back up.** `git branch backup/<branch name with / replaced by ->-<YYYYMMDD>-<short sha>`.
4. **Rebase.** `git rebase --onto <tag> <base> <branch>`. Release tags live on release branches,
   not on `main`, so a plain `git rebase <tag>` would drag unreleased upstream commits along.
5. **Resolve by intent, one commit at a time.** For every conflicted file AND every file the
   forecast lists as merged silently: read how upstream does it at `<tag>`, then re-apply the
   behaviour from that commit's `fork/` page.
   - Upstream now provides the behaviour itself: skip that commit and note it under "Dropped on
     purpose" in `fork/README.md`.
   - A fork change breaks an upstream test only because it renamed something: keep upstream's
     name instead.
6. **Verify.** `python3 scripts/verify.py` (needs Docker; uses a throwaway database).
   - `VERIFIED`: continue.
   - NEW failure caused by the code: fix it. If it is an intended consequence of a behaviour,
     show the user first, then add it to `expected-failures.txt`.
   - NEW failure caused by this machine (missing test assets, missing tools): add an `env` line
     for that test, with the reason, and say so in the report.
   - Expected failures that now pass: check whether the fork lost that behaviour.
7. **Keep one commit per behaviour.** Put each fix into the commit it belongs to
   (`git commit --fixup <commit>`, then `git rebase -i --autosquash <tag>`), together with any
   change to that behaviour's `fork/` page. Commit messages never mention the base version.
8. **Report and stop.** Fill every field:

```
Base:                       <old> -> <new>
Conflicts resolved:         <commit> / <file> - <what was done>
Silently merged, reviewed:  <n of n>, <anything that needed fixing>
Dropped (upstream has it):  <behaviour or none>
verify.py:                  <VERIFIED | NOT VERIFIED>, flaky: <tests>, env: <tests>
Data-changing migrations:   <each one since the deployed base, and whether it touches existing data>
Before deploying:           database backup, machine-learning image version, mobile app major version
Not done:                   push, image build, deployment
```

## Adding or dropping a behaviour

- Add: one commit with the code, `fork/<name>.md` (what, why, how, known limits, when to drop)
  and, where possible, `server/test/medium/specs/fork/<name>.spec.ts`. Place it before the
  workflow commit.
- Drop: remove its commit, then run `verify.py`; expected failures that now pass leave the list.

## Rules

| Do not                                                                           | Instead                                                                                                               |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Rebase onto upstream `main` or a release candidate                               | Stable release tags only. A database that ran unreleased migrations cannot go back.                                   |
| Trust a file because git merged it without conflict                              | Review every file on the forecast's silent list. Clean merges have dropped filters and kept calls to removed helpers. |
| Edit upstream test files so they pass                                            | List intended failures in `expected-failures.txt`.                                                                    |
| Rename things upstream owns                                                      | Keep upstream's names and pass the fork's value through them.                                                         |
| Push, force-push, build the image, or touch the running instance or its database | Stop at the report. Each needs the user's go-ahead in this conversation.                                              |
| Force-push on old information                                                    | `git ls-remote origin <branch>` first, then `--force-with-lease=<branch>:<full sha>`.                                 |
| Prepare a pull request, issue or comment for upstream                            | Upstream has frozen this area and rejects LLM-written contributions. See `fork/README.md`.                            |
