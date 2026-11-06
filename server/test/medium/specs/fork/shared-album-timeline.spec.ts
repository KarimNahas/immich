// Fork-only test. What it protects and why: fork/shared-album-timeline.md
import { Kysely } from 'kysely';
import { AlbumUserRole } from 'src/enum.js';
import { AccessRepository } from 'src/repositories/access.repository.js';
import { AssetRepository } from 'src/repositories/asset.repository.js';
import { LoggingRepository } from 'src/repositories/logging.repository.js';
import { PartnerRepository } from 'src/repositories/partner.repository.js';
import { DB } from 'src/schema/index.js';
import { TimelineService } from 'src/services/timeline.service.js';
import { newMediumService } from 'test/medium.factory.js';
import { factory } from 'test/small.factory.js';
import { getKyselyDB } from 'test/utils.js';

let database: Kysely<DB>;

beforeAll(async () => {
  database = await getKyselyDB();
});

const setup = async () => {
  const { sut, ctx } = newMediumService(TimelineService, {
    database,
    real: [AssetRepository, AccessRepository, PartnerRepository],
    mock: [LoggingRepository],
  });
  const { user: owner } = await ctx.newUser();
  const { user: member } = await ctx.newUser();
  const { user: outsider } = await ctx.newUser();
  const date = new Date('1970-02-12');
  const { asset } = await ctx.newAsset({ ownerId: owner.id, fileCreatedAt: date, localDateTime: date });
  await ctx.newExif({ assetId: asset.id, make: 'Canon' });
  const { album } = await ctx.newAlbum({ ownerId: owner.id }, [asset.id]);
  await ctx.newAlbumUser({ albumId: album.id, userId: member.id, role: AlbumUserRole.Viewer });

  return {
    sut,
    asset,
    memberAuth: factory.auth({ user: { id: member.id } }),
    outsiderAuth: factory.auth({ user: { id: outsider.id } }),
  };
};

describe('fork: shared album assets in the timeline', () => {
  it('should count another user’s asset in the timeline of a member of an album that contains it', async () => {
    const { sut, memberAuth } = await setup();

    await expect(sut.getTimeBuckets(memberAuth, {})).resolves.toEqual([{ count: 1, timeBucket: '1970-02-01' }]);
  });

  it('should return that asset in the member’s time bucket', async () => {
    const { sut, asset, memberAuth } = await setup();

    const bucket = JSON.parse(await sut.getTimeBucket(memberAuth, { timeBucket: '1970-02-01' }));
    expect(bucket.id).toEqual([asset.id]);
  });

  it('should not show it to a user who is not a member of the album', async () => {
    const { sut, outsiderAuth } = await setup();

    await expect(sut.getTimeBuckets(outsiderAuth, {})).resolves.toEqual([]);
  });
});
