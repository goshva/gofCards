<template>
  <div class="prow" :class="{ 'prow--picked': picked }">
    <span class="prow__num">{{ player.jersey_number ?? '—' }}</span>
    <span class="prow__name">{{ player.nickname }}</span>
    <span class="prow__pos small muted">{{ player.position === 'GOALKEEPER' ? 'GK' : 'F' }}</span>
    <span v-if="picked" class="prow__tick" title="Есть в вашем составе">✓</span>
  </div>
</template>

<script setup lang="ts">
import type { PlayerBrief } from '@/types'

defineProps<{ player: PlayerBrief; picked?: boolean }>()
</script>

<style scoped>
.prow {
  display: grid;
  grid-template-columns: 28px 1fr auto auto;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--surface-solid);
  border: 1px solid var(--border);
  border-radius: 10px;
}
.prow--picked { border-color: var(--success); }
.prow__num { color: var(--text-dim); font-variant-numeric: tabular-nums; }
.prow__name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prow__tick { color: var(--success); }
</style>
