# Shared-album assets appear in the member's own timeline

## What changes

A user's main timeline also contains assets owned by other users when those assets are in an
album the user is a member of. The same applies to the explore page's cities, the places list and
the search suggestions.

## Why

Upstream only mixes other people's photos into your timeline through partner sharing, which
exposes a whole library. The family shares by album, and expects photos shared that way to show
up in the normal timeline rather than only inside each album.

## How

- `server/src/services/timeline.service.ts`: sets `sharedAlbumUserId` when a user views their own
  timeline.
- `server/src/repositories/asset.repository.ts`: `getTimeBuckets` and `getTimeBucket` add
  upstream's `inSharedAlbum(...)` helper to the owner filter, and `getAssetIdByCity` accepts the
  same id.
- `server/src/repositories/search.repository.ts` and `server/src/services/search.service.ts`:
  `getAssetsByCity`, the suggestion getters and `getExifField` accept the viewer's id.
- `server/src/utils/database.ts`: `searchAssetBuilderLegacy` has the shared-album conditions.

## Known limits

- Search results still contain only owned and partner assets. The legacy search builder applies
  the original owner filter next to the new conditions, which cancels them, and the newer search
  path is not wired at all.
- Trash and archive views of one's own timeline also include matching shared-album assets.
- There is no per-user switch; it is always on.

## Test

`server/test/medium/specs/fork/shared-album-timeline.spec.ts`

## Drop this when

Upstream offers shared-album assets in the timeline. Upstream closed a community pull request for
exactly this (immich-app/immich#24938) because it is reworking sharing itself.
