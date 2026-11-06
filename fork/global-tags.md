# Global tags

## What changes

Every user sees one shared list of tags. Any user can read, assign and reuse any tag. Creating a
tag whose value already exists returns the existing tag instead of a private copy. In the asset
viewer, an asset's tags are shown to everyone who can open the asset, not only to its owner.

## Why

Upstream tags are private to the user who created them. In a family library that means the same
word typed by two people becomes two unrelated tags, and nobody sees the tagging others did on
photos shared with them. The family wants one vocabulary that everyone builds on.

Removing the ownership check altogether, rather than adding a way to share individual tags, is
deliberate: every account on this instance is a trusted family member. It would be wrong for an
instance with unrelated users.

## How

- `server/src/utils/access.ts`: `TagRead`, `TagUpdate`, `TagDelete` and `TagAsset` allow every id.
- `server/src/repositories/tag.repository.ts`: `getByValue` and `getAll` are not scoped to a user,
  and `upsertValue` returns an existing tag with the same value before inserting.
- `server/src/services/tag.service.ts`: calls those two methods without a user id.
- `web/src/lib/components/asset-viewer/DetailPanelTags.svelte`: the tags section is shown to
  non-owners.

## Known limits

- Mobile tag sync is still per user, so the mobile app only shows a user's own tags.
- Deleting a tag id that does not exist succeeds silently instead of returning an error.
- Any user can rename or delete any tag.

## Test

`server/test/medium/specs/fork/global-tags.spec.ts`

## Drop this when

Upstream lets tags be shared between users, or shared across an instance.
