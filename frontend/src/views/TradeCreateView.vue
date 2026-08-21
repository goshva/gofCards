<template>
  <div class="page stack">
    <h1>{{ counterOf ? 'Встречное предложение' : 'Новое предложение' }}</h1>

    <div class="card-surface stack">
      <label class="stack small">
        <span class="muted">Кому</span>
        <input v-model.trim="query" placeholder="Имя пользователя" @input="searchUsers" />
      </label>

      <div v-if="candidates.length" class="scroller">
        <button
          v-for="candidate in candidates"
          :key="candidate.id"
          class="chip"
          :class="{ 'chip--active': receiver?.id === candidate.id }"
          @click="pickReceiver(candidate)"
        >
          {{ candidate.username }} · {{ candidate.total_points }} очк.
        </button>
      </div>
      <p v-else-if="query && !searching" class="small muted">Никого не нашлось</p>
    </div>

    <template v-if="receiver">
      <h2>Ваши карточки</h2>
      <p class="small muted">Выбрано: {{ mine.length }}</p>
      <CardGrid :cards="myTradable" :selected-ids="mine" @select="toggleMine" />

      <h2>Карточки {{ receiver.username }}</h2>
      <p class="small muted">Выбрано: {{ theirs.length }}</p>
      <p v-if="loadingTheirs" class="empty">Загрузка…</p>
      <CardGrid
        v-else
        :cards="theirCards"
        :selected-ids="theirs"
        empty-text="У пользователя нет доступных карточек"
        @select="toggleTheirs"
      />

      <label class="stack small">
        <span class="muted">Добавить монет (у вас {{ auth.user?.coins ?? 0 }})</span>
        <input v-model.number="coins" type="number" min="0" :max="auth.user?.coins ?? 0" />
      </label>

      <label class="stack small">
        <span class="muted">Сообщение</span>
        <textarea v-model.trim="message" rows="2" maxlength="512" />
      </label>

      <p v-if="error" class="alert alert--error">{{ error }}</p>
      <p v-if="done" class="alert alert--success">Предложение отправлено</p>

      <button class="btn btn--block" :disabled="busy || !canSubmit" @click="submit">
        {{ busy ? 'Отправляем…' : 'Отправить предложение' }}
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CardGrid from '@/components/CardGrid.vue'
import { trades as tradesApi } from '@/api/endpoints'
import { useAuthStore } from '@/stores/auth'
import { useCollectionStore } from '@/stores/collection'
import type { UserCard, UserPublic } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collection = useCollectionStore()

const counterOf = computed(() => (route.query.counter as string | undefined) ?? null)

const query = ref('')
const candidates = ref<UserPublic[]>([])
const receiver = ref<UserPublic | null>(null)
const theirCards = ref<UserCard[]>([])
const loadingTheirs = ref(false)
const searching = ref(false)

const mine = ref<string[]>([])
const theirs = ref<string[]>([])
const coins = ref(0)
const message = ref('')
const busy = ref(false)
const error = ref<string | null>(null)
const done = ref(false)

const myTradable = computed(() =>
  collection.items.filter((card) => !card.locked_by_trade),
)

const canSubmit = computed(
  () => Boolean(receiver.value) && (mine.value.length > 0 || theirs.value.length > 0 || coins.value > 0),
)

let searchTimer: number | undefined
function searchUsers() {
  window.clearTimeout(searchTimer)
  if (!query.value) {
    candidates.value = []
    return
  }
  searching.value = true
  searchTimer = window.setTimeout(async () => {
    try {
      candidates.value = await tradesApi.searchUsers(query.value)
    } finally {
      searching.value = false
    }
  }, 250)
}

async function pickReceiver(user: UserPublic) {
  receiver.value = user
  theirs.value = []
  loadingTheirs.value = true
  try {
    theirCards.value = (await tradesApi.userCards(user.id)).filter((c) => !c.locked_by_trade)
  } finally {
    loadingTheirs.value = false
  }
}

function toggle(list: string[], id: string) {
  const index = list.indexOf(id)
  if (index >= 0) list.splice(index, 1)
  else list.push(id)
}
const toggleMine = (card: UserCard) => toggle(mine.value, card.id)
const toggleTheirs = (card: UserCard) => toggle(theirs.value, card.id)

async function submit() {
  if (!receiver.value) return
  busy.value = true
  error.value = null
  done.value = false
  try {
    const payload = {
      sender_cards: mine.value,
      receiver_cards: theirs.value,
      sender_coins: coins.value || 0,
      message: message.value || null,
    }
    if (counterOf.value) await tradesApi.counter(counterOf.value, payload)
    else await tradesApi.create({ receiver_id: receiver.value.id, ...payload })

    done.value = true
    await collection.load()
    await router.push('/trades')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось отправить предложение'
  } finally {
    busy.value = false
  }
}

/** A counter-offer is always addressed back to whoever sent the original, so
 * the recipient and their cards are preloaded instead of being searched for. */
async function preloadCounter() {
  if (!counterOf.value) return
  const original = (await tradesApi.incoming()).find((o) => o.id === counterOf.value)
  if (!original) {
    error.value = 'Исходное предложение больше не активно'
    return
  }
  await pickReceiver(original.sender)
  // mirror the original: what they asked of you becomes what you now offer
  mine.value = original.receiver_cards.map((c) => c.id)
  theirs.value = original.sender_cards.map((c) => c.id)
}

onMounted(async () => {
  await collection.load()
  await preloadCounter()
})
</script>
