<template>
  <div class="slot" :class="{ 'slot--filled': !!entry, 'slot--real': highlight }">
    <button v-if="!entry" class="slot__empty" @click="$emit('pick')">
      <span class="slot__plus">+</span>
      <span class="small muted">{{ slotName }}</span>
    </button>

    <template v-else>
      <button class="slot__player" @click="$emit('pick')">
        <img v-if="image" :src="image" :alt="entry.player.nickname" @error="broken = true" />
        <span v-else class="slot__initial">{{ entry.player.nickname[0] }}</span>
        <span class="slot__name">{{ entry.player.nickname }}</span>
        <span v-if="ovr" class="slot__ovr">{{ ovr }}</span>
        <span class="slot__team small muted">{{ entry.player.team?.short_title ?? entry.player.team?.title ?? '' }}</span>
      </button>

      <div class="slot__actions">
        <button
          class="pill"
          :class="{ 'pill--on': entry.is_captain }"
          title="Капитан"
          @click="$emit('captain', entry)"
        >
          C
        </button>
        <button class="pill pill--danger" title="Убрать" @click="$emit('clear')">×</button>
      </div>
      <span v-if="highlight" class="slot__flag" title="Игрок вышел в реальном стартовом составе">✓</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { PositionSlot, SquadEntry } from '@/types'

const props = defineProps<{
  slotName: PositionSlot
  entry?: SquadEntry
  highlight?: boolean
}>()

defineEmits<{ pick: []; clear: []; captain: [entry: SquadEntry] }>()

const broken = ref(false)
const image = computed(
  () => (broken.value ? null : (props.entry?.card.template.player?.photo_url ?? props.entry?.card.template.image_url)),
)
const ovr = computed(() => props.entry?.card.template.ovr ?? 0)
</script>

<style scoped>
.slot {
  position: relative;
  border-radius: var(--radius-sm);
  background: rgba(4, 14, 10, 0.55);
  border: 1px dashed rgba(255, 255, 255, 0.16);
  min-height: 98px;
  display: flex;
  flex-direction: column;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.slot--filled {
  border-style: solid;
  border-color: rgba(255, 255, 255, 0.2);
  background: linear-gradient(180deg, rgba(26, 23, 56, 0.7), rgba(8, 20, 15, 0.6));
}
.slot--real {
  border-color: var(--success);
  box-shadow: 0 0 0 1px rgba(34, 227, 161, 0.35), 0 6px 18px rgba(34, 227, 161, 0.18);
}

.slot__empty,
.slot__player {
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 6px 4px;
  min-height: 0;
}
.slot__plus { font-size: 20px; color: var(--text-dim); }
.slot__player img {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid rgba(255, 255, 255, 0.18);
}
.slot__initial {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--input);
  font-weight: 700;
}
.slot__name {
  font-size: 11px;
  font-weight: 600;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.slot__team { font-size: 10px; }
.slot__ovr {
  position: absolute;
  top: 5px;
  left: 6px;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
  color: var(--brand-cyan-soft);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
}

.slot__actions {
  display: flex;
  gap: 5px;
  justify-content: center;
  padding: 0 4px 6px;
}
.pill {
  min-height: 32px;
  min-width: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}
.pill--on { background: var(--warning); color: #2a1a00; }
.pill--danger { background: rgba(255, 92, 108, 0.22); color: #ffb3bb; }

.slot__flag {
  position: absolute;
  top: 4px;
  right: 5px;
  color: var(--success);
  font-size: 12px;
}
</style>
