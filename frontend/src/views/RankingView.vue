<template>
  <div class="page stack">
    <div class="row row--between">
      <h1>Рейтинг игроков</h1>
      <div class="row">
        <RouterLink class="btn btn--sm btn--ghost" to="/matches">Матчи</RouterLink>
        <RouterLink class="btn btn--sm btn--ghost" to="/leaderboard">Лидеры</RouterLink>
      </div>
    </div>
    <p class="small muted">
      Позиция считается из реальных результатов команды на турнире: голы в цифровой и физической
      частях, пропущенные, серии пенальти и глубина плей-офф. Чем выше место, тем более редкие
      версии карточки существуют в игре.
    </p>

    <div class="scroller">
      <button class="chip" :class="{ 'chip--active': !position }" @click="setPosition(undefined)">Все</button>
      <button
        class="chip"
        :class="{ 'chip--active': position === 'GOALKEEPER' }"
        @click="setPosition('GOALKEEPER')"
      >
        Вратари
      </button>
      <button class="chip" :class="{ 'chip--active': position === 'FIELD' }" @click="setPosition('FIELD')">
        Полевые
      </button>
    </div>

    <p v-if="error" class="alert alert--error">{{ error }}</p>
    <p v-if="loading" class="empty empty--loading">Загрузка рейтинга</p>

    <template v-else>
      <div v-for="row in rows" :key="row.player.id" class="card-surface rankrow">
        <span class="rankrow__place" :class="placeClass(row.rank)">{{ row.rank }}</span>

        <img v-if="row.player.photo_url" class="rankrow__face" :src="row.player.photo_url" :alt="row.player.nickname" loading="lazy" />
        <span v-else class="rankrow__face rankrow__face--mono">{{ row.player.nickname[0] }}</span>

        <div class="rankrow__who">
          <strong>{{ row.player.nickname }}</strong>
          <span class="small muted">
            <b class="cc">{{ countryCode(row.player.country) }}</b>
            <img v-if="row.player.team?.logo_url" class="rankrow__crest" :src="row.player.team.logo_url" alt="" />
            {{ row.player.team?.short_title ?? row.player.team?.title }}
            · {{ row.player.position === 'GOALKEEPER' ? 'вратарь' : 'полевой' }}
          </span>
          <span class="rankrow__tiers">
            <i v-for="r in row.rarities" :key="r" class="tier" :class="`tier--${r.toLowerCase()}`" :title="RARITY_LABELS[r]" />
          </span>
        </div>

        <span v-if="row.owned" class="chip owned" title="Карточек этого игрока у вас">×{{ row.owned }}</span>
        <strong class="rankrow__ovr">{{ row.ovr }}</strong>
      </div>

      <p v-if="!rows.length" class="empty">Рейтинг пуст — выполните синхронизацию</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { cards as cardsApi } from '@/api/endpoints'
import { RARITY_LABELS, countryCode } from '@/lib/format'
import type { Position, RankingRow } from '@/types'

const rows = ref<RankingRow[]>([])
const position = ref<Position | undefined>(undefined)
const loading = ref(true)
const error = ref<string | null>(null)

function placeClass(rank: number) {
  if (rank <= 10) return 'rankrow__place--legendary'
  if (rank <= 32) return 'rankrow__place--epic'
  if (rank <= 72) return 'rankrow__place--rare'
  return ''
}

async function load() {
  loading.value = true
  error.value = null
  try {
    rows.value = await cardsApi.ranking({ position: position.value, limit: 200 })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить рейтинг'
  } finally {
    loading.value = false
  }
}

function setPosition(next: Position | undefined) {
  position.value = next
  load()
}

onMounted(load)
</script>

<style scoped>
.rankrow {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  transition: border-color 0.16s ease, transform 0.1s ease;
}
.rankrow:active { transform: scale(0.995); }
.rankrow__place {
  width: 30px;
  text-align: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 15px;
  font-variant-numeric: tabular-nums;
  color: var(--text-faint);
}
.rankrow__place--legendary {
  color: var(--rarity-legendary);
  text-shadow: 0 0 14px rgba(255, 193, 7, 0.5);
}
.rankrow__place--epic { color: var(--rarity-epic); }
.rankrow__place--rare { color: var(--rarity-rare); }

.rankrow__face { width: 38px; height: 38px; border-radius: 50%; object-fit: cover; flex: none; }
.rankrow__face--mono {
  display: grid;
  place-items: center;
  background: var(--input);
  font-weight: 700;
}
.rankrow__who { flex: 1; display: flex; flex-direction: column; min-width: 0; gap: 1px; }
.rankrow__who strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--text-dim);
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
}
.rankrow__crest { width: 13px; height: 14px; object-fit: contain; vertical-align: -2px; }
.rankrow__tiers { display: flex; gap: 3px; margin-top: 3px; }
.tier { width: 12px; height: 4px; border-radius: 999px; display: block; }
.tier--common { background: var(--rarity-common); }
.tier--rare { background: var(--rarity-rare); }
.tier--epic { background: var(--rarity-epic); }
.tier--legendary { background: var(--rarity-legendary); }
.owned { font-size: 11px; min-height: 24px; padding: 2px 8px; }
.rankrow__ovr {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}
.rankrow__face { border: 1px solid var(--border); }
</style>
