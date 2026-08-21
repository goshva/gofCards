<template>
  <RouterLink :to="`/matches/${match.id}`" class="match card-surface">
    <div class="match__meta small muted">
      <span>{{ match.round_label ?? `Тур ${match.round ?? '—'}` }}</span>
      <span class="status" :class="`status--${match.status.toLowerCase()}`">{{ statusLabel }}</span>
    </div>
    <div class="match__teams">
      <span class="match__team">
        <img v-if="match.home_team?.logo_url" :src="match.home_team.logo_url" alt="" class="crest" />
        {{ match.home_team?.title ?? 'TBD' }}
      </span>
      <span class="match__score">{{ match.home_score }} : {{ match.away_score }}</span>
      <span class="match__team match__team--away">
        {{ match.away_team?.title ?? 'TBD' }}
        <img v-if="match.away_team?.logo_url" :src="match.away_team.logo_url" alt="" class="crest" />
      </span>
    </div>
    <div class="match__legs small muted">
      <span>digital {{ match.home_digital }}:{{ match.away_digital }}</span>
      <span>physical {{ match.home_physical }}:{{ match.away_physical }}</span>
      <span v-if="match.home_shootouts || match.away_shootouts">
        пенальти {{ match.home_shootouts }}:{{ match.away_shootouts }}
      </span>
      <span v-if="match.has_lineups" class="lineups">составы есть</span>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Match } from '@/types'

const props = defineProps<{ match: Match }>()

const LABELS: Record<string, string> = {
  SCHEDULED: 'запланирован',
  LIVE: 'идёт',
  COMPLETED: 'завершён',
  CANCELLED: 'отменён',
}
const statusLabel = computed(() => LABELS[props.match.status] ?? props.match.status)
</script>

<style scoped>
.match {
  display: block;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.16s ease, transform 0.1s ease;
}
.match:active { transform: scale(0.995); }
.match__meta { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.match__teams {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.match__team {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.match__team--away { justify-content: flex-end; }
.crest { width: 18px; height: 20px; object-fit: contain; flex: none; }
.match__score {
  font-family: var(--font-display);
  font-variant-numeric: tabular-nums;
  font-size: 18px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
}
.match__legs { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
.status--live {
  color: var(--danger);
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.status--live::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--danger);
  animation: blink 1.4s ease-in-out infinite;
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }
.status--completed { color: var(--text-dim); }
.status--scheduled { color: var(--brand-cyan-soft); }
.lineups { color: var(--success); }
</style>
