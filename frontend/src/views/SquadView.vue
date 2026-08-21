<template>
  <div class="page stack">
    <div class="row row--between">
      <h1>Состав</h1>
      <span class="chip">{{ squad.squad?.filled_slots ?? 0 }} / {{ squad.squad?.required_slots ?? 5 }}</span>
    </div>

    <p class="small muted">
      Фиджитал-футбол играется составом 5×5, поэтому стартовая пятёрка — вратарь и четыре полевых
      игрока из ваших карточек.
    </p>

    <label class="stack small">
      <span class="muted">Матч для проверки Perfect Five</span>
      <select v-model="selectedMatchId" @change="reload">
        <option :value="null">Черновой состав (без матча)</option>
        <option v-for="m in matchOptions" :key="m.id" :value="m.id">
          {{ m.round_label }} — {{ m.home_team?.title }} vs {{ m.away_team?.title }}
        </option>
      </select>
    </label>

    <div class="pitch">
      <div class="pitch__row pitch__row--field">
        <SquadSlot
          v-for="slot in FIELD_SLOTS"
          :key="slot"
          :slot-name="slot"
          :entry="entryFor(slot)"
          :highlight="isRealStarter(entryFor(slot))"
          @pick="startPick(slot)"
          @clear="clearSlot(slot)"
          @captain="setCaptain"
        />
      </div>
      <div class="pitch__row pitch__row--gk">
        <SquadSlot
          slot-name="GK"
          :entry="entryFor('GK')"
          :highlight="isRealStarter(entryFor('GK'))"
          @pick="startPick('GK')"
          @clear="clearSlot('GK')"
          @captain="setCaptain"
        />
      </div>
    </div>

    <h2>Запасные</h2>
    <div class="bench">
      <SquadSlot
        v-for="slot in BENCH_SLOTS"
        :key="slot"
        :slot-name="slot"
        :entry="entryFor(slot)"
        @pick="startPick(slot)"
        @clear="clearSlot(slot)"
        @captain="setCaptain"
      />
    </div>

    <p v-if="squad.error" class="alert alert--error">{{ squad.error }}</p>

    <button class="btn btn--block" :disabled="squad.loading" @click="validate">Проверить состав</button>

    <div v-if="squad.validation" class="stack">
      <p class="alert" :class="squad.validation.valid ? 'alert--success' : 'alert--error'">
        {{ squad.validation.message }}
      </p>
      <ul v-if="squad.validation.issues.length" class="issues small">
        <li v-for="issue in squad.validation.issues" :key="issue.code + issue.message">
          {{ issue.message }}
        </li>
      </ul>
    </div>

    <div v-if="perfect" class="card-surface stack">
      <h3>Perfect Five</h3>
      <p class="small" :class="perfect.is_perfect ? 'alert alert--success' : 'muted'">
        {{ perfect.message }}
      </p>
      <p v-if="perfect.available" class="small muted">
        Совпало с хозяевами: {{ perfect.home_matches.length }} / 5, с гостями:
        {{ perfect.away_matches.length }} / 5. Полное совпадение даёт +20 очков.
      </p>
    </div>

    <Teleport to="body">
      <div v-if="picking" class="picker" @click.self="picking = null">
        <div class="picker__panel stack">
          <div class="row row--between">
            <h2>Слот {{ picking }}</h2>
            <button class="chip" @click="picking = null">Закрыть</button>
          </div>
          <p class="small muted">{{ pickerHint }}</p>
          <CardGrid
            :cards="pickable"
            empty-text="Нет подходящих карточек — откройте бустер или обменяйтесь."
            @select="choose"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CardGrid from '@/components/CardGrid.vue'
import SquadSlot from '@/components/SquadSlot.vue'
import { matches as matchesApi, squad as squadApi } from '@/api/endpoints'
import { useCollectionStore } from '@/stores/collection'
import { useSquadStore } from '@/stores/squad'
import type { Match, PerfectFive, PositionSlot, SquadEntry, UserCard } from '@/types'

const squad = useSquadStore()
const collection = useCollectionStore()

const FIELD_SLOTS: PositionSlot[] = ['F1', 'F2', 'F3', 'F4']
const BENCH_SLOTS: PositionSlot[] = ['SUB1', 'SUB2']

const selectedMatchId = ref<number | null>(null)
const matchOptions = ref<Match[]>([])
const picking = ref<PositionSlot | null>(null)
const perfect = ref<PerfectFive | null>(null)

const usedCardIds = computed(() => new Set(squad.squad?.entries.map((e) => e.card.id) ?? []))

const pickable = computed(() => {
  const slot = picking.value
  if (!slot) return []
  return collection.availablePlayers.filter((card) => {
    if (usedCardIds.value.has(card.id)) return false
    const position = card.template.position
    if (slot === 'GK') return position === 'GOALKEEPER'
    if (slot.startsWith('F')) return position === 'FIELD'
    return true
  })
})

const pickerHint = computed(() => {
  if (picking.value === 'GK') return 'Только вратари'
  if (picking.value?.startsWith('F')) return 'Только полевые игроки'
  return 'Любой игрок из коллекции'
})

function entryFor(slot: PositionSlot): SquadEntry | undefined {
  return squad.squad?.entries.find((e) => e.position_slot === slot)
}

function isRealStarter(entry?: SquadEntry): boolean {
  if (!entry || !perfect.value?.available) return false
  return (
    perfect.value.home_matches.includes(entry.player.id) ||
    perfect.value.away_matches.includes(entry.player.id)
  )
}

function startPick(slot: PositionSlot) {
  picking.value = slot
}

async function choose(card: UserCard) {
  if (!picking.value) return
  await squad.select(card.id, picking.value, selectedMatchId.value)
  picking.value = null
  await collection.load()
  await refreshPerfect()
}

async function clearSlot(slot: PositionSlot) {
  await squad.remove(slot, selectedMatchId.value)
  await collection.load()
  await refreshPerfect()
}

async function setCaptain(entry: SquadEntry) {
  await squad.setCaptain(entry.id, false, selectedMatchId.value)
}

async function validate() {
  await squad.validate(selectedMatchId.value)
  await refreshPerfect()
}

async function refreshPerfect() {
  if (!selectedMatchId.value) {
    perfect.value = null
    return
  }
  try {
    perfect.value = await squadApi.perfectFive(selectedMatchId.value)
  } catch {
    perfect.value = null
  }
}

async function reload() {
  await squad.load(selectedMatchId.value)
  await refreshPerfect()
}

onMounted(async () => {
  await Promise.all([squad.load(null), collection.load()])
  const page = await matchesApi.list({ limit: 60 })
  matchOptions.value = page.items
})
</script>

<style scoped>
.pitch {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(70% 55% at 50% 0%, rgba(1, 160, 234, 0.16), transparent 70%),
    linear-gradient(180deg, #0d2b1c, #071a12);
  border: 1px solid rgba(34, 227, 161, 0.22);
  border-radius: var(--radius);
  padding: 18px 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: inset 0 0 60px rgba(0, 0, 0, 0.4);
}
/* pitch markings: halfway line and centre circle */
.pitch::before,
.pitch::after {
  content: '';
  position: absolute;
  pointer-events: none;
  border-color: rgba(255, 255, 255, 0.09);
}
.pitch::before {
  left: 0;
  right: 0;
  top: 50%;
  border-top: 1px solid rgba(255, 255, 255, 0.09);
}
.pitch::after {
  left: 50%;
  top: 50%;
  width: 86px;
  height: 86px;
  margin: -43px 0 0 -43px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 50%;
}
.pitch > * { position: relative; z-index: 1; }
.pitch__row { display: grid; gap: 8px; }
.pitch__row--field { grid-template-columns: repeat(4, 1fr); }
.pitch__row--gk { grid-template-columns: 1fr; max-width: 46%; margin: 0 auto; }
.bench { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.issues { margin: 0; padding-left: 18px; color: var(--text-dim); }

.picker {
  position: fixed;
  inset: 0;
  background: rgba(4, 7, 14, 0.75);
  z-index: 55;
  display: flex;
  align-items: flex-end;
}
.picker__panel {
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  max-height: 82dvh;
  overflow-y: auto;
  background: var(--surface-solid);
  border-radius: 18px 18px 0 0;
  padding: 14px 14px calc(20px + env(safe-area-inset-bottom));
}
</style>
