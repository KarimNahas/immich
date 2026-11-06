// Fork-only test. What it protects and why: fork/shared-favorites.md
import { Kysely } from 'kysely';
import { AssetVisibility } from 'src/enum.js';
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

describe('fork: shared favorites', () => {
  it('should report the owner’s favorite state to another user who can see the asset', async () => {
    const { sut, ctx } = newMediumService(TimelineService, {
      database,
      real: [AssetRepository, AccessRepository, PartnerRepository],
      mock: [LoggingRepository],
    });
    const { user: owner } = await ctx.newUser();
    const { user: viewer } = await ctx.newUser();
    const date = new Date('1970-02-12');
    const { asset } = await ctx.newAsset({
      ownerId: owner.id,
      fileCreatedAt: date,
      localDateTime: date,
      isFavorite: true,
    });
    await ctx.newExif({ assetId: asset.id, make: 'Canon' });
    await ctx.newPartner({ sharedById: owner.id, sharedWithId: viewer.id });

    const response = await sut.getTimeBucket(factory.auth({ user: { id: viewer.id } }), {
      timeBucket: '1970-02-01',
      withPartners: true,
      visibility: AssetVisibility.Timeline,
    });

    expect(JSON.parse(response)).toEqual(expect.objectContaining({ id: [asset.id], isFavorite: [true] }));
  });
});
