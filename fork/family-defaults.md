# Defaults for a family instance

## What changes

New accounts start with People and Tags shown in the web sidebar and with tags enabled. The map
starts with partners' and shared albums' assets included.

## Why

Upstream hides these until each user finds the setting. Family members who never open the
settings would not see the features the rest of this fork is about.

## How

- `server/src/utils/preferences.ts`: `people.sidebarWeb`, `tags.enabled` and `tags.sidebarWeb`
  default to true.
- `web/src/lib/stores/preferences.store.ts`: the map's `withPartners` and `withSharedAlbums`
  default to true.

## Known limits

These are only defaults. Every user can change them, and existing accounts keep what they have.

## Test

None; nothing here changes behaviour beyond a default value.

## Drop this when

You are willing to set these once per account instead. This is the first candidate to remove.
