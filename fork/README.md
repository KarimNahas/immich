# This fork

A fork of [Immich](https://github.com/immich-app/immich) for one family's instance. Every member
should see the photos, tags and favourites of what has been shared with them, and be able to help
maintain shared photos.

## How it is organised

- The fork is a short stack of commits on top of an upstream **stable release tag**.
- **One commit per behaviour.** Each commit contains the code, a page in this folder explaining
  what it changes and why, and where possible a test in `server/test/medium/specs/fork/`.
- To remove a behaviour, drop its commit. To add one, add a commit with the same three parts.
- The last commit holds the update workflow in `.claude/skills/updating-immich-fork/`.

Every other file in this folder describes one behaviour. Read the page before changing or
re-porting that behaviour; the "Why" section is the part the code cannot tell you.

## Principles

- Stay as close to upstream as possible. Prefer an upstream feature or a per-user setting over
  fork code.
- Keep upstream's names. Renaming something upstream owns breaks upstream's tests and causes
  conflicts for no gain.
- Do not edit upstream's test files. Tests the fork breaks on purpose are listed in
  `.claude/skills/updating-immich-fork/expected-failures.txt`.
- The moment upstream offers an equivalent, drop the fork's version and note it below.

## Dropped on purpose (do not re-add)

- **Global people and face matching across all users.** Upstream now has person sharing with
  roles, and cluster groups that recognise people across the members' photos.
- **Showing a face's person to non-owners, and an extra asset-update listener in the asset
  viewer.** Upstream does both itself.

## Where upstream is heading

- Upstream has a feature freeze on sharing and asset ownership: bug fixes only, feature pull
  requests are closed. A community pull request for shared-album assets in the timeline
  (immich-app/immich#24938) was closed for that reason.
- The maintainers are reworking sharing themselves (draft immich-app/immich#27437, "sharing
  permissions"). When that or a successor lands, expect large conflicts in the files this fork
  touches. Re-evaluate every behaviour against what upstream then offers before porting anything.
- Upstream does not accept LLM-generated pull requests, descriptions or comments. Do not prepare
  any for it.

## Deployment facts that are easy to forget

- The instance is built by docker compose from this working directory.
- The machine-learning image version is pinned separately and must match the server's major
  version.
- The server only works with mobile apps of the same major version.
- Upstream does not support downgrades. Once a database has run a version's migrations, an older
  version will not start. Never deploy a branch based on unreleased upstream commits.
- If the instance is stopped automatically when idle, keep it awake while migrations run.
