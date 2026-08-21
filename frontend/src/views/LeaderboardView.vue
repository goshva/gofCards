<template>
  <div class="page stack">
    <h1>Рейтинг</h1>

    <div v-if="me?.row" class="card-surface me">
      <span class="me__rank">#{{ me.rank }}</span>
      <div class="stack">
        <strong>{{ me.row.username }}</strong>
        <span class="small muted">
          {{ me.row.total_points }} очков · {{ me.row.cards_owned }} карточек ·
          Perfect Five: {{ me.row.perfect_fives }}
        </span>
      </div>
      <span class="small muted">из {{ me.total_users }}</span>
    </div>

    <p v-if="error" class="alert alert--error">{{ error }}</p>
    <p v-if="loading" class="empty empty--loading">Загрузка таблицы</p>

    <template v-else>
      <div
        v-for="row in rows"
        :key="row.user_id"
        class="card-surface rowline"
        :class="`rowline--${row.rank <= 3 ? row.rank : 'rest'}`"
      >
        <span class="rowline__rank">{{ medal(row.rank) }}</span>
        <span class="rowline__name">{{ row.username }}</span>
        <span v-if="row.perfect_fives" class="chip" title="Идеальных пятёрок">★ {{ row.perfect_fives }}</span>
        <strong class="rowline__points">{{ row.total_points }}</strong>
      </div>
      <p v-if="!rows.length" class="empty">Очки ещё не начислялись</p>
    </template>

    <h2>Моя история очков</h2>
    <div v-for="entry in history" :key="entry.match_id" class="card-surface stack">
      <div class="row row--between">
        <strong>{{ entry.match_slug }}</strong>
        <span class="chip">{{ entry.points }} очк.</span>
      </div>
      <p v-if="entry.is_perfect_xi" class="alert alert--success small">Perfect Five: +20</p>
    </div>
    <p v-if="!history.length" class="empty small">Пока нет начислений</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { leaderboard as leaderboardApi } from '@/api/endpoints'
import type { LeaderboardRow } from '@/types'

const rows = ref<LeaderboardRow[]>([])
const me = ref<{ rank: number | null; total_users: number; row: LeaderboardRow | null } | null>(null)
const history = ref<Array<{ match_id: number; match_slug: string; points: number; is_perfect_xi: boolean }>>([])
const loading = ref(true)
const error = ref<string | null>(null)

function medal(rank: number): string {
  return { 1: '🥇', 2: '🥈', 3: '🥉' }[rank] ?? String(rank)
}

onMounted(async () => {
  try {
    const [top, mine, hist] = await Promise.all([
      leaderboardApi.top(),
      leaderboardApi.me(),
      leaderboardApi.history(),
    ])
    rows.value = top
    me.value = mine
    history.value = hist
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить рейтинг'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.me { display: flex; align-items: center; gap: 12px; }
.me__rank { font-size: 22px; font-weight: 800; color: var(--accent-strong); }
.rowline { display: flex; align-items: center; gap: 11px; padding: 11px 13px; }
.rowline--1 { border-color: rgba(255, 193, 7, 0.45); box-shadow: 0 6px 22px rgba(255, 193, 7, 0.14); }
.rowline--2 { border-color: rgba(164, 67, 255, 0.4); }
.rowline--3 { border-color: rgba(1, 160, 234, 0.4); }
.rowline__rank {
  width: 28px;
  text-align: center;
  color: var(--text-faint);
  font-family: var(--font-display);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.rowline__name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rowline__points {
  font-family: var(--font-display);
  font-size: 17px;
  font-variant-numeric: tabular-nums;
}
.me { border-color: var(--border-strong); box-shadow: var(--glow-violet); }
.me__rank { font-family: var(--font-display); }
</style>
