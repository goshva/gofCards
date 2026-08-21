<template>
  <div class="page stack">
    <div class="row row--between">
      <h1>Обмены</h1>
      <RouterLink class="btn btn--sm" to="/trades/new">Новое</RouterLink>
    </div>

    <div class="scroller">
      <button
        v-for="tab in TABS"
        :key="tab.value"
        class="chip"
        :class="{ 'chip--active': active === tab.value }"
        @click="active = tab.value"
      >
        {{ tab.label }}
        <span v-if="counts[tab.value]" class="muted">&nbsp;{{ counts[tab.value] }}</span>
      </button>
    </div>

    <p v-if="error" class="alert alert--error">{{ error }}</p>
    <p v-if="loading" class="empty empty--loading">Загрузка обменов</p>

    <p v-else-if="!visible.length" class="empty">Здесь пока пусто</p>

    <article v-for="offer in visible" :key="offer.id" class="card-surface stack">
      <div class="row row--between">
        <strong>{{ offer.sender.username }} → {{ offer.receiver.username }}</strong>
        <span class="chip" :class="statusClass(offer.status)">{{ statusLabel(offer.status) }}</span>
      </div>

      <p v-if="offer.message" class="small muted">«{{ offer.message }}»</p>

      <div class="exchange">
        <div class="stack">
          <span class="small muted">Отдаёт</span>
          <CardGrid :cards="offer.sender_cards" empty-text="—" />
          <span v-if="offer.sender_coins" class="chip">🪙 {{ offer.sender_coins }}</span>
        </div>
        <div class="stack">
          <span class="small muted">Просит</span>
          <CardGrid :cards="offer.receiver_cards" empty-text="—" />
        </div>
      </div>

      <div v-if="offer.status === 'PENDING'" class="row">
        <template v-if="active === 'incoming'">
          <button class="btn btn--success btn--sm" @click="act(offer.id, 'accept')">Принять</button>
          <button class="btn btn--ghost btn--sm" @click="act(offer.id, 'decline')">Отклонить</button>
          <RouterLink class="btn btn--ghost btn--sm" :to="`/trades/new?counter=${offer.id}`">
            Встречное
          </RouterLink>
        </template>
        <button v-else class="btn btn--danger btn--sm" @click="act(offer.id, 'cancel')">Отменить</button>
      </div>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CardGrid from '@/components/CardGrid.vue'
import { trades as tradesApi } from '@/api/endpoints'
import { useCollectionStore } from '@/stores/collection'
import type { TradeOffer, TradeStatus } from '@/types'

const collection = useCollectionStore()

type Tab = 'incoming' | 'outgoing' | 'history'
const TABS: Array<{ value: Tab; label: string }> = [
  { value: 'incoming', label: 'Входящие' },
  { value: 'outgoing', label: 'Исходящие' },
  { value: 'history', label: 'История' },
]

const active = ref<Tab>('incoming')
const incoming = ref<TradeOffer[]>([])
const outgoing = ref<TradeOffer[]>([])
const history = ref<TradeOffer[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const counts = computed<Record<Tab, number>>(() => ({
  incoming: incoming.value.length,
  outgoing: outgoing.value.length,
  history: history.value.length,
}))

const visible = computed(() => {
  if (active.value === 'incoming') return incoming.value
  if (active.value === 'outgoing') return outgoing.value
  return history.value
})

const STATUS_LABELS: Record<TradeStatus, string> = {
  PENDING: 'ожидает',
  ACCEPTED: 'принято',
  DECLINED: 'отклонено',
  CANCELLED: 'отменено',
  COUNTERED: 'встречное',
}
function statusLabel(status: TradeStatus) {
  return STATUS_LABELS[status] ?? status
}
function statusClass(status: TradeStatus) {
  return { 'chip--active': status === 'PENDING' }
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const [inc, out, hist] = await Promise.all([
      tradesApi.incoming(),
      tradesApi.outgoing(),
      tradesApi.history(),
    ])
    incoming.value = inc
    outgoing.value = out
    history.value = hist
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить обмены'
  } finally {
    loading.value = false
  }
}

async function act(id: string, action: 'accept' | 'decline' | 'cancel') {
  error.value = null
  try {
    await tradesApi[action](id)
    await Promise.all([load(), collection.load()])
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Действие не выполнено'
  }
}

onMounted(load)
</script>

<style scoped>
.exchange { display: grid; grid-template-columns: 1fr; gap: 12px; }
@media (min-width: 560px) {
  .exchange { grid-template-columns: 1fr 1fr; }
}
</style>
