<script lang="ts">
  import StarRating, { type Rating } from '#lib/elements/StarRating.svelte';
  import { authManager } from '#lib/managers/auth-manager.svelte.ts';
  import { handlePromiseError } from '#lib/utils.ts';
  import { handleError } from '#lib/utils/handle-error.ts';
  import { updateAsset, type AssetResponseDto } from '@immich/sdk';
  import { t } from 'svelte-i18n';

  interface Props {
    asset: AssetResponseDto;
    canEdit: boolean;
  }

  let { asset, canEdit }: Props = $props();

  let rating = $derived(asset.exifInfo?.rating ?? null) as Rating;

  const handleChangeRating = async (rating: Rating) => {
    try {
      await updateAsset({ id: asset.id, updateAssetDto: { rating } });
    } catch (error) {
      handleError(error, $t('errors.cant_apply_changes'));
    }
  };
</script>

{#if !authManager.isSharedLink && authManager.authenticated && authManager.preferences.ratings.enabled}
  <section class="px-4 pt-4">
    <StarRating {rating} readOnly={!canEdit} onRating={(rating) => handlePromiseError(handleChangeRating(rating))} />
  </section>
{/if}
