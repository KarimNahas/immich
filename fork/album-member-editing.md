# Album members can edit assets in their albums

## What changes

A user who is an editor of an album can change the description, date, location, rating and tags
of assets in it, and archive or delete them, even when another user owns those assets. The asset
viewer shows the edit controls to those users.

## Why

Upstream lets only the owner change an asset. The family curates shared albums together: one
person fixes dates and locations, another writes descriptions and removes duplicates. Asking each
owner to do that for their own photos defeats the purpose of a shared album.

## How

- `server/src/utils/access.ts`: `AssetUpdate`, `AssetDelete`, `AssetCopy` and the `AssetEdit*`
  permissions accept the owner or anyone with album access to the asset.
- `web/src/lib/services/asset.service.ts`: an `isAlbumEditor` helper, and the Edit action is no
  longer owner-only.
- `web/src/lib/components/asset-viewer/DetailPanel.svelte` and `AssetViewerNavBar.svelte`: compute
  `canEdit` (the owner, or an editor of an album containing the asset) and use it where upstream
  uses `isOwner`.
- The detail panel's child components keep upstream's `isOwner` property; the panel passes
  `canEdit` through it, so those files stay identical to upstream. `DetailPanelDate.svelte` takes
  `isOwner` as a property instead of working it out itself.

## Known limits

- The server is more permissive than the web UI: it grants this to every album member, including
  viewers and the album owner, while the UI offers the controls to editors only.
- Editing people and faces on someone else's asset still follows upstream's rules.

## Test

`server/test/medium/specs/fork/album-member-editing.spec.ts`

## Drop this when

Upstream's sharing rework (draft immich-app/immich#27437, "sharing permissions") gives album
roles the right to edit assets.
