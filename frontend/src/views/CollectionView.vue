<template>
  <div class="page stack">
    <div class="row row--between">
      <h1>Коллекция</h1>
      <div class="row">
        <RouterLink class="btn btn--sm btn--ghost" to="/ranking">Топ</RouterLink>
        <RouterLink class="btn btn--sm btn--ghost" to="/shop">Бустеры</RouterLink>
      </div>
    </div>

    <div v-if="store.stats" class="stats">
      <div class="tile">
        <strong>{{ store.stats.total_cards }}</strong><span>карточек</span>
      </div>
      <div class="tile">
        <strong class="gradient-text">{{ store.stats.best_ovr || '—' }}</strong><span>лучший OVR</span>
      </div>
      <div class="tile">
        <strong>{{ permanentCount }}</strong><span>вечных</span>
      </div>
      <div class="tile">
        <strong>{{ store.stats.unique_templates }}<i>/{{ store.stats.templates_total }}</i></strong>
        <span>собрано</span>
      </div>
    </div>

    <input v-model.trim="store.search" placeholder="Поиск по имени игрока или команде" />

    <div class="scroller">
      <button class="chip" :class="{ 'chip--active': !store.typeFilter }" @click="store.typeFilter = ''">Все</button>
      <button class="chip" :class="{ 'chip--active': store.typeFilter === 'PLAYER' }" @click="store.typeFilter = 'PLAYER'">
        Игроки
      </button>
      <button class="chip" :class="{ 'chip--active': store.typeFilter === 'TEAM' }" @click="store.typeFilter = 'TEAM'">
        Команды
      </button>
    </div>

    <div class="scroller">
      <button class="chip" :class="{ 'chip--active': store.sort === 'ovr' }" @click="store.sort = 'ovr'">
        По рейтингу
      </button>
      <button class="chip" :class="{ 'chip--active': store.sort === 'new' }" @click="store.sort = 'new'">
        Сначала новые
      </button>
    </div>

    <div class="scroller">
      <button class="chip" :class="{ 'chip--active': !store.rarityFilter }" @click="store.rarityFilter = ''">
        Любая редкость
      </button>
      <button
        v-for="rarity in RARITIES"
        :key="rarity.value"
        class="chip"
        :class="{ 'chip--active': store.rarityFilter === rarity.value }"
        @click="store.rarityFilter = rarity.value"
      >
        {{ rarity.label }}
        <span v-if="store.stats" class="muted">&nbsp;{{ store.stats.by_rarity[rarity.value] ?? 0 }}</span>
      </button>
    </div>

    <p v-if="store.error" class="alert alert--error">{{ store.error }}</p>
    <p v-if="store.loading" class="empty empty--loading">Загрузка коллекции</p>

    <div v-else-if="!store.items.length" class="empty stack">
      <p>Коллекция пуста — игроки покупаются в бустерах.</p>
      <RouterLink class="btn" to="/shop">В магазин</RouterLink>
    </div>

    <CardGrid v-else :cards="store.filtered" empty-text="Ничего не найдено" @select="openCard" />

    <CardSheet :card="active" @close="active = null" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CardGrid from '@/components/CardGrid.vue'
import CardSheet from '@/components/CardSheet.vue'
import { useCollectionStore } from '@/stores/collection'
import type { Rarity, UserCard } from '@/types'

const store = useCollectionStore()
const active = ref<UserCard | null>(null)
const permanentCount = computed(() => store.items.filter((c) => c.is_permanent).length)

const RARITIES: Array<{ value: Rarity; label: string }> = [
  { value: 'COMMON', label: 'Обычные' },
  { value: 'RARE', label: 'Редкие' },
  { value: 'EPIC', label: 'Эпик' },
  { value: 'LEGENDARY', label: 'Легенды' },
]

function openCard(card: UserCard) {
  active.value = card
}

onMounted(() => store.load())
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 12px 6px;
  border-radius: var(--radius-sm);
  background: var(--surface);
  border: 1px solid var(--border);
  backdrop-filter: blur(12px);
}
.tile strong {
  font-family: var(--font-display);
  font-size: 20px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}
.tile strong i { font-style: normal; font-size: 12px; color: var(--text-faint); }
.tile span { font-size: 10px; color: var(--text-faint); text-align: center; }
</style>
