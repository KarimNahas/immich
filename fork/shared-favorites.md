# Favourites are visible to everyone who can see the asset

## What changes

The heart on an asset shows for every user who can see that asset, and every logged-in viewer is
offered the favourite and unfavourite actions.

## Why

Upstream reports an asset as favourite only to its owner. In shared albums the family uses
favourites to mark the best pictures of an event, which is pointless if nobody else can see the
mark.

## How

- `server/src/dtos/asset-response.dto.ts` (`mapAsset`): `isFavorite` no longer requires the viewer
  to be the owner.
- `server/src/repositories/asset.repository.ts` (`getTimeBucket`): the selected `isFavorite` column
  is no longer combined with an owner check.
- `web/src/lib/services/asset.service.ts`: the Favorite and Unfavorite actions are offered to any
  logged-in viewer instead of only the owner.

## Known limits

- It is one flag stored on the asset, not one per user. Whoever toggles it changes it for
  everyone.
- Toggling it is an asset update, so it only succeeds for the owner unless
  [album-member-editing](album-member-editing.md) also applies.
- The Favorites page lists every favourite asset the viewer's timeline can reach, including those
  favourited by others.

## Test

`server/test/medium/specs/fork/shared-favorites.spec.ts`

## Drop this when

Upstream stores favourites per user, so that anyone can favourite any asset they can see.
