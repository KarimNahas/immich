// Fork-only test. What it protects and why: fork/album-member-editing.md
import { Kysely } from 'kysely';
import { AlbumUserRole, Permission } from 'src/enum.js';
import { AccessRepository } from 'src/repositories/access.repository.js';
import { LoggingRepository } from 'src/repositories/logging.repository.js';
import { DB } from 'src/schema/index.js';
import { AlbumService } from 'src/services/album.service.js';
import { checkAccess } from 'src/utils/access.js';
import { newMediumService } from 'test/medium.factory.js';
import { factory } from 'test/small.factory.js';
import { getKyselyDB } from 'test/utils.js';

let database: Kysely<DB>;

beforeAll(async () => {
  database = await getKyselyDB();
});

const setup = async () => {
  const { ctx } = newMediumService(AlbumService, {
    database,
    real: [AccessRepository],
    mock: [LoggingRepository],
  });
  const { user: owner } = await ctx.newUser();
  const { user: member } = await ctx.newUser();
  const { user: outsider } = await ctx.newUser();
  const { asset } = await ctx.newAsset({ ownerId: owner.id });
  const { album } = await ctx.newAlbum({ ownerId: owner.id }, [asset.id]);
  await ctx.newAlbumUser({ albumId: album.id, userId: member.id, role: AlbumUserRole.Editor });

  return {
    access: ctx.get(AccessRepository),
    asset,
    memberAuth: factory.auth({ user: { id: member.id } }),
    outsiderAuth: factory.auth({ user: { id: outsider.id } }),
  };
};

const permissions = [Permission.AssetUpdate, Permission.AssetDelete];

describe('fork: editing assets through a shared album', () => {
  it.each(permissions)('should grant %s on another user’s asset to an album member', async (permission) => {
    const { access, asset, memberAuth } = await setup();

    await expect(checkAccess(access, { auth: memberAuth, permission, ids: [asset.id] })).resolves.toEqual(
      new Set([asset.id]),
    );
  });

  it.each(permissions)('should not grant %s to a user outside the album', async (permission) => {
    const { access, asset, outsiderAuth } = await setup();

    await expect(checkAccess(access, { auth: outsiderAuth, permission, ids: [asset.id] })).resolves.toEqual(new Set());
  });
});
