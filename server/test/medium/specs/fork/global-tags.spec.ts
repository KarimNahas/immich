// Fork-only test. What it protects and why: fork/global-tags.md
import { Kysely } from 'kysely';
import { AccessRepository } from 'src/repositories/access.repository.js';
import { LoggingRepository } from 'src/repositories/logging.repository.js';
import { TagRepository } from 'src/repositories/tag.repository.js';
import { DB } from 'src/schema/index.js';
import { TagService } from 'src/services/tag.service.js';
import { newMediumService } from 'test/medium.factory.js';
import { factory } from 'test/small.factory.js';
import { getKyselyDB } from 'test/utils.js';

let database: Kysely<DB>;

beforeAll(async () => {
  database = await getKyselyDB();
});

const setup = async () => {
  const { sut, ctx } = newMediumService(TagService, {
    database,
    real: [TagRepository, AccessRepository],
    mock: [LoggingRepository],
  });
  const { user: creator } = await ctx.newUser();
  const { user: other } = await ctx.newUser();
  const value = `family-${creator.id}`;
  const [tag] = await sut.upsert(factory.auth({ user: { id: creator.id } }), { tags: [value] });

  return { sut, tag, value, otherAuth: factory.auth({ user: { id: other.id } }) };
};

describe('fork: global tags', () => {
  it('should list a tag created by another user', async () => {
    const { sut, tag, otherAuth } = await setup();

    const tags = await sut.getAll(otherAuth);
    expect(tags.map(({ id }) => id)).toContain(tag.id);
  });

  it('should let another user read a tag by id', async () => {
    const { sut, tag, otherAuth } = await setup();

    await expect(sut.get(otherAuth, tag.id)).resolves.toEqual(expect.objectContaining({ id: tag.id }));
  });

  it('should reuse the existing tag when another user upserts the same value', async () => {
    const { sut, tag, value, otherAuth } = await setup();

    const [reused] = await sut.upsert(otherAuth, { tags: [value] });
    expect(reused.id).toBe(tag.id);
  });
});
