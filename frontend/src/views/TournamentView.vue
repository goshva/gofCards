<template>
  <div class="page stack">
    <h1>Турнир</h1>
    <p class="small muted">
      Ваша пятёрка заходит в реальную сетку Phygital Football 2026 на место самой слабой команды.
      Все остальные пары сохраняют исторический результат — разыгрываются только матчи с вашим
      участием и то, что они меняют дальше по сетке.
    </p>

    <p v-if="error" class="alert alert--error">{{ error }}</p>
    <p v-if="loading" class="empty empty--loading">Загрузка турнира</p>

    <template v-else-if="preview">
      <section class="card-surface stack">
        <div class="row row--between">
          <div>
            <h2>Ваша команда</h2>
            <p class="small muted">рейтинг состава, капитан считается вдвое</p>
          </div>
          <span class="bigovr">{{ preview.squad_ovr }}</span>
        </div>

        <div class="lineup">
          <span v-for="slot in preview.squad" :key="slot.player_id" class="chip lineup__slot">
            <b>{{ slot.slot }}</b>
            {{ slot.nickname }}
            <i>{{ slot.ovr }}</i>
            <em v-if="slot.is_captain" title="капитан">C</em>
            <u v-if="slot.is_permanent" title="вечная карточка">∞</u>
            <u v-else :class="{ low: (slot.runs_left ?? 6) <= 2 }" :title="`осталось турниров: ${slot.runs_left}`">
              {{ slot.runs_left }}
            </u>
          </span>
        </div>

        <p class="small muted">
          Заменяет: <strong>{{ preview.replaced_team.title }}</strong>
          (рейтинг {{ preview.replaced_team.ovr }}, {{ preview.replaced_team.record }},
          {{ preview.replaced_team.rank }}-е место)
        </p>

        <div v-if="preview.first_match" class="alert alert--info small">
          Первый матч — {{ preview.first_match.label }} против
          <strong>{{ preview.first_match.opponent }}</strong> ({{ preview.first_match.opponent_ovr }}).
          Шанс пройти: <strong>{{ percent(preview.first_match.win_chance) }}</strong>
        </div>

        <button class="btn btn--block" :disabled="entering || cooldown > 0" @click="enter">
          {{ buttonLabel }}
        </button>
        <p class="small muted center">
          Взнос {{ preview.entry_fee }} монет · {{ preview.coins_per_stage }} монет и
          {{ preview.points_per_stage }} очков за каждый пройденный этап
        </p>
        <p class="small center" :class="fragile.length ? 'alert alert--error' : 'muted'">
          Участие тратит один из 6 турниров каждой выставленной карточки.
          <template v-if="fragile.length">
            Сгорят после этого захода: {{ fragile.map((s) => s.nickname).join(', ') }}.
          </template>
        </p>
      </section>

      <RunResult v-if="result" :entry="result" />

      <section v-if="history.length" class="stack">
        <h2>Прошлые попытки</h2>
        <button
          v-for="item in history"
          :key="item.id"
          class="card-surface histrow"
          @click="open(item.id)"
        >
          <span class="histrow__stage">{{ item.stage_label }}</span>
          <span class="small muted">рейтинг {{ item.squad_ovr }} · {{ item.wins }}/{{ item.played }} побед</span>
          <span class="histrow__prize" :class="{ plus: item.coins_net > 0 }">
            {{ item.coins_net > 0 ? '+' : '' }}{{ item.coins_net }} 🪙 · +{{ item.points_awarded }} ⭐
          </span>
        </button>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import RunResult from '@/components/RunResult.vue'
import { tournament as api } from '@/api/endpoints'
import { useAuthStore } from '@/stores/auth'
import type { TournamentEntry, TournamentPreview } from '@/types'

const auth = useAuthStore()

const preview = ref<TournamentPreview | null>(null)
const result = ref<TournamentEntry | null>(null)
const history = ref<TournamentEntry[]>([])
const loading = ref(true)
const entering = ref(false)
const error = ref<string | null>(null)
const cooldown = ref(0)

let timer: number | undefined

const fragile = computed(
  () => preview.value?.squad.filter((s) => !s.is_permanent && (s.runs_left ?? 9) <= 1) ?? [],
)

const buttonLabel = computed(() => {
  if (entering.value) return 'Жеребьёвка…'
  if (cooldown.value > 0) return `Следующая попытка через ${Math.ceil(cooldown.value / 60)} мин`
  return 'Участвовать'
})

function percent(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`
}

async function load() {
  loading.value = true
  error.value = null
  try {
    preview.value = await api.preview()
    cooldown.value = preview.value.cooldown_seconds
    history.value = await api.entries()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить турнир'
  } finally {
    loading.value = false
  }
}

async function enter() {
  entering.value = true
  error.value = null
  try {
    result.value = await api.enter()
    await auth.refresh()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось заявиться'
  } finally {
    entering.value = false
  }
}

async function open(id: string) {
  result.value = await api.entry(id)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(async () => {
  await load()
  timer = window.setInterval(() => {
    if (cooldown.value > 0) cooldown.value -= 1
  }, 1000)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<style scoped>
.bigovr {
  font-family: var(--font-display);
  font-size: 34px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.04em;
  background: var(--gradient-brand);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.lineup { display: flex; flex-wrap: wrap; gap: 6px; }
.lineup__slot { gap: 5px; font-size: 11px; }
.lineup__slot b { color: var(--text-dim); font-weight: 700; }
.lineup__slot i { font-style: normal; font-weight: 700; }
.lineup__slot u {
  text-decoration: none;
  font-size: 10px;
  color: var(--text-dim);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0 3px;
}
.lineup__slot u.low { color: var(--danger); border-color: var(--danger); }
.lineup__slot em {
  font-style: normal;
  background: var(--warning);
  color: #2a1a00;
  border-radius: 4px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 800;
}

.histrow {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 11px 13px;
  transition: border-color 0.16s ease, transform 0.1s ease;
}
.histrow:active { transform: scale(0.995); border-color: var(--border-strong); }
.histrow__stage { font-weight: 600; flex: none; }
.histrow__prize {
  margin-left: auto;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--text-dim);
  white-space: nowrap;
}
.histrow__prize.plus { color: var(--success); }
</style>
