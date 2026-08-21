<template>
  <section class="card-surface stack result" :class="`result--${entry.stage.toLowerCase()}`">
    <div class="row row--between">
      <div>
        <h2>{{ entry.stage_label }}</h2>
        <p class="small muted">{{ entry.wins }} из {{ entry.played }} матчей выиграно</p>
      </div>
      <div class="prize">
        <span :class="{ plus: entry.coins_net > 0 }">
          {{ entry.coins_net > 0 ? '+' : '' }}{{ entry.coins_net }} 🪙
        </span>
        <span class="plus">+{{ entry.points_awarded }} ⭐</span>
      </div>
    </div>

    <ol class="path">
      <li v-for="m in entry.my_matches" :key="m.match_id" :class="{ won: m.user_won }">
        <span class="path__label">{{ m.label }}</span>
        <span class="path__opponent">{{ opponentOf(m) }}</span>
        <span class="path__score">
          {{ scoreOf(m) }}
          <i v-if="m.shootout">пен {{ m.shootout[0] }}:{{ m.shootout[1] }}</i>
        </span>
        <span class="path__odds" :title="'Шанс на победу по жеребьёвке'">
          {{ Math.round((m.user_win_chance ?? 0) * 100) }}%
        </span>
        <span class="path__verdict">{{ m.user_won ? 'прошли' : 'вылет' }}</span>
      </li>
    </ol>

    <div v-if="entry.retired.length" class="alert alert--error small stack">
      <strong>Сгорели после этого турнира:</strong>
      <span>{{ entry.retired.map((c) => `${c.nickname} (${c.slot})`).join(', ') }}</span>
      <span class="muted">Ресурс обычной карточки — 6 турниров. Вечные не изнашиваются.</span>
    </div>

    <div v-else-if="wearing.length" class="alert alert--info small">
      Скоро сгорят: {{ wearing.map((s) => `${s.nickname} — ${s.runs_left}`).join(', ') }}
    </div>

    <button class="btn btn--ghost btn--sm" @click="showAll = !showAll">
      {{ showAll ? 'Скрыть сетку' : 'Показать всю сетку' }}
    </button>

    <div v-if="showAll" class="stack">
      <p class="small muted">
        Матчи с пометкой «история» прошли ровно так, как в реальном турнире. «Пересчитан» — пары,
        которые изменились из-за вашего участия.
      </p>
      <div v-for="m in entry.full_run" :key="m.match_id" class="fixture" :class="{ mine: m.user_involved }">
        <span class="fixture__label small muted">{{ m.label }}</span>
        <span class="fixture__teams">
          {{ m.home.name }} <b>{{ m.home_score }}:{{ m.away_score }}</b> {{ m.away.name }}
        </span>
        <span class="fixture__tag small" :class="m.source">
          {{ m.source === 'real' ? 'история' : 'пересчитан' }}
        </span>
      </div>
    </div>

    <p class="small muted seed">
      Seed жеребьёвки <code>{{ entry.seed }}</code> — по нему результат воспроизводится в точности,
      поэтому исход нельзя подкрутить задним числом.
    </p>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { RunMatch, TournamentEntry } from '@/types'

const props = defineProps<{ entry: TournamentEntry }>()
const showAll = ref(false)

const wearing = computed(() =>
  props.entry.squad.filter((s) => !s.is_permanent && (s.runs_left ?? 9) <= 2),
)

function opponentOf(m: RunMatch): string {
  return m.home.is_user ? m.away.name : m.home.name
}

function scoreOf(m: RunMatch): string {
  return m.home.is_user
    ? `${m.home_score}:${m.away_score}`
    : `${m.away_score}:${m.home_score}`
}
</script>

<style scoped>
.result { border-left: 3px solid var(--border); overflow: hidden; }
.result--champion {
  border-left-color: var(--rarity-legendary);
  box-shadow: 0 10px 34px rgba(255, 193, 7, 0.18), var(--shadow-card);
}
.result--medal { border-left-color: var(--rarity-epic); box-shadow: 0 10px 30px rgba(164, 67, 255, 0.16), var(--shadow-card); }
.result--semi,
.result--quarter { border-left-color: var(--rarity-rare); }

.prize {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-family: var(--font-display);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.prize .plus { color: var(--success); }

.path { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.path li {
  display: grid;
  background: var(--input);
  grid-template-columns: 1fr auto auto;
  grid-template-areas: 'label score verdict' 'opponent odds verdict';
  gap: 2px 8px;
  padding: 8px 10px;
  border-radius: 10px;
  border-left: 3px solid var(--danger);
}
.path li.won { border-left-color: var(--success); }
.path__label { grid-area: label; font-size: 11px; color: var(--text-dim); }
.path__opponent { grid-area: opponent; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.path__score {
  grid-area: score;
  font-family: var(--font-display);
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}
.path__score i { font-style: normal; font-size: 10px; color: var(--text-dim); margin-left: 4px; }
.path__odds { grid-area: odds; font-size: 11px; color: var(--text-dim); text-align: right; }
.path__verdict { grid-area: verdict; align-self: center; font-size: 11px; color: var(--text-dim); }

.fixture {
  display: grid;
  background: var(--input);
  grid-template-columns: 1fr auto;
  gap: 2px 8px;
  padding: 7px 9px;
  border-radius: 8px;
}
.fixture.mine { outline: 1px solid var(--brand-cyan); background: rgba(1, 160, 234, 0.08); }
.fixture__label { grid-column: 1 / -1; }
.fixture__teams { font-size: 13px; }
.fixture__tag.real { color: var(--text-dim); }
.fixture__tag.simulated { color: var(--warning); }

.seed code {
  background: var(--input);
  padding: 1px 5px;
  border-radius: 5px;
  font-size: 11px;
}
</style>
