<template>
  <div class="page stack">
    <RouterLink to="/matches" class="small muted">← К матчам</RouterLink>

    <p v-if="error" class="alert alert--error">{{ error }}</p>
    <p v-if="loading" class="empty empty--loading">Загрузка матча</p>

    <template v-else-if="match">
      <div class="card-surface stack">
        <p class="small muted">{{ match.round_label }} · {{ match.venue ?? 'место не указано' }}</p>
        <div class="score">
          <span>{{ match.home_team?.title ?? 'TBD' }}</span>
          <strong>{{ match.home_score }} : {{ match.away_score }}</strong>
          <span>{{ match.away_team?.title ?? 'TBD' }}</span>
        </div>
        <div class="legs small muted">
          <span>Digital {{ match.home_digital }}:{{ match.away_digital }}</span>
          <span>Physical {{ match.home_physical }}:{{ match.away_physical }}</span>
          <span v-if="match.home_shootouts || match.away_shootouts">
            Пенальти {{ match.home_shootouts }}:{{ match.away_shootouts }}
          </span>
        </div>
        <p v-if="match.start_time" class="small muted">{{ formatted }}</p>
      </div>

      <h2>Стартовые составы</h2>
      <p v-if="!hasLineups" class="alert alert--info">
        GoFuture не публикует составы для этого турнира. Их вносит администратор — до этого механика
        Perfect Five на матч недоступна.
      </p>
      <div v-else class="lineups">
        <div class="stack">
          <h3>{{ match.home_team?.title }}</h3>
          <PlayerRow v-for="p in lineups!.home" :key="p.id" :player="p" :picked="myPlayerIds.has(p.id)" />
        </div>
        <div class="stack">
          <h3>{{ match.away_team?.title }}</h3>
          <PlayerRow v-for="p in lineups!.away" :key="p.id" :player="p" :picked="myPlayerIds.has(p.id)" />
        </div>
      </div>

      <div v-if="perfect" class="card-surface stack">
        <h3>Ваш состав против реального</h3>
        <p class="small" :class="perfect.is_perfect ? 'alert alert--success' : 'muted'">
          {{ perfect.message }}
        </p>
        <p v-if="perfect.available" class="small muted">
          Совпадений: хозяева {{ perfect.home_matches.length }}/5, гости
          {{ perfect.away_matches.length }}/5
        </p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PlayerRow from '@/components/PlayerRow.vue'
import { matches as matchesApi, squad as squadApi } from '@/api/endpoints'
import type { Match, PerfectFive, PlayerBrief } from '@/types'

const route = useRoute()
const matchId = Number(route.params.id)

const match = ref<Match | null>(null)
const lineups = ref<{ home: PlayerBrief[]; away: PlayerBrief[]; source: string | null } | null>(null)
const perfect = ref<PerfectFive | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const hasLineups = computed(
  () => Boolean(lineups.value) && (lineups.value!.home.length > 0 || lineups.value!.away.length > 0),
)
const myPlayerIds = computed(() => new Set(perfect.value?.user_player_ids ?? []))
const formatted = computed(() =>
  match.value?.start_time ? new Date(match.value.start_time).toLocaleString('ru-RU') : '',
)

onMounted(async () => {
  try {
    match.value = await matchesApi.one(matchId)
    const [lineupData, perfectData] = await Promise.allSettled([
      squadApi.lineups(matchId),
      squadApi.perfectFive(matchId),
    ])
    if (lineupData.status === 'fulfilled') lineups.value = lineupData.value
    if (perfectData.status === 'fulfilled') perfect.value = perfectData.value
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Матч не найден'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.score {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  text-align: center;
  font-weight: 600;
}
.score strong { font-size: 24px; font-variant-numeric: tabular-nums; }
.legs { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }
.lineups { display: grid; grid-template-columns: 1fr; gap: 16px; }
@media (min-width: 560px) {
  .lineups { grid-template-columns: 1fr 1fr; }
}
</style>
