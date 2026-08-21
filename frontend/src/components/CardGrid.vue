<template>
  <div v-if="cards.length" class="card-grid">
    <CardTile
      v-for="card in cards"
      :key="card.id"
      :card="card"
      :selected="selectedIds?.includes(card.id)"
      @select="$emit('select', card)"
    />
  </div>
  <p v-else class="empty">{{ emptyText }}</p>
</template>

<script setup lang="ts">
import CardTile from './CardTile.vue'
import type { UserCard } from '@/types'

withDefaults(
  defineProps<{
    cards: UserCard[]
    selectedIds?: string[]
    emptyText?: string
  }>(),
  { emptyText: 'Карточек нет' },
)

defineEmits<{ select: [card: UserCard] }>()
</script>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
  gap: 10px;
}
@media (min-width: 480px) {
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
}
</style>
