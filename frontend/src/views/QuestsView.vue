<template>
  <div class="page stack">
    <h1>Квесты</h1>
    <p class="small muted">Выполняй задания и зарабатывай монеты на бустеры и турнир.</p>

    <p v-if="error" class="alert alert--error">{{ error }}</p>
    <p v-if="loading" class="empty empty--loading">Загрузка квестов</p>

    <template v-else-if="board">
      <div class="summary">
        <div class="tile"><strong>{{ board.total_earned }}</strong><span>заработано</span></div>
        <div class="tile"><strong>{{ board.friends_invited }}</strong><span>друзей</span></div>
        <div class="tile"><strong>{{ available }}</strong><span>доступно</span></div>
      </div>

      <section class="card-surface invite stack">
        <h2>Приведи друга</h2>
        <p class="small muted">
          Друг вводит код при регистрации: ты получаешь {{ board.referral_reward }} монет,
          он — {{ board.referral_friend_bonus }}.
        </p>
        <button class="code" @click="copyCode">
          <span>{{ board.referral_code }}</span>
          <i>{{ copied ? 'скопировано' : 'нажми, чтобы скопировать' }}</i>
        </button>
        <button class="btn btn--ghost btn--sm" @click="shareLink">Поделиться ссылкой</button>
      </section>

      <article
        v-for="quest in board.quests.filter((q) => !q.referral)"
        :key="quest.key"
        class="card-surface quest"
      >
        <span class="quest__icon" aria-hidden="true">{{ quest.icon }}</span>

        <div class="quest__body">
          <strong>{{ quest.title }}</strong>
          <span class="small muted">{{ quest.description }}</span>
          <span v-if="quest.times_claimed" class="small quest__count">
            выполнено раз: {{ quest.times_claimed }} · заработано {{ quest.coins_earned }}
          </span>
        </div>

        <div class="quest__action">
          <span class="quest__reward">+{{ quest.reward }}</span>
          <a
            v-if="quest.status === 'action_required'"
            class="btn btn--sm"
            :href="quest.url ?? '#'"
            target="_blank"
            rel="noopener"
            @click="markStarted(quest.key)"
          >
            Открыть
          </a>
          <button
            v-else-if="quest.status === 'available'"
            class="btn btn--sm"
            :disabled="busy === quest.key"
            @click="claim(quest.key)"
          >
            Забрать
          </button>
          <span v-else-if="quest.status === 'cooldown'" class="chip small">
            через {{ Math.ceil(quest.cooldown_seconds / 60) }} мин
          </span>
          <span v-else class="chip small done">выполнен</span>
        </div>
      </article>

      <p v-if="toast" class="alert alert--success">{{ toast }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { quests as questsApi } from '@/api/endpoints'
import { useAuthStore } from '@/stores/auth'
import type { QuestBoard } from '@/types'

const auth = useAuthStore()
const board = ref<QuestBoard | null>(null)
const loading = ref(true)
const busy = ref<string | null>(null)
const error = ref<string | null>(null)
const toast = ref<string | null>(null)
const copied = ref(false)

const available = computed(
  () => board.value?.quests.filter((q) => q.status === 'available').length ?? 0,
)

async function load() {
  try {
    board.value = await questsApi.board()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить квесты'
  } finally {
    loading.value = false
  }
}

async function claim(key: string) {
  busy.value = key
  error.value = null
  try {
    const result = await questsApi.claim(key)
    auth.setCoins(result.coins)
    toast.value = `Начислено ${result.reward} монет`
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось забрать награду'
  } finally {
    busy.value = null
  }
}

async function markStarted(key: string) {
  // the link opens in a new tab; the claim unlocks once we know it was followed
  try {
    board.value = await questsApi.start(key)
  } catch {
    /* the reward simply stays locked */
  }
}

const inviteLink = computed(() =>
  board.value ? `${location.origin}/login?ref=${board.value.referral_code}` : '',
)

async function copyCode() {
  if (!board.value) return
  try {
    await navigator.clipboard.writeText(board.value.referral_code)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    error.value = 'Браузер не дал скопировать — выделите код вручную'
  }
}

async function shareLink() {
  const url = inviteLink.value
  if (navigator.share) {
    try {
      await navigator.share({ title: 'GoF Cards', text: 'Собери свою пятёрку', url })
      return
    } catch {
      /* the user dismissed the sheet */
    }
  }
  try {
    await navigator.clipboard.writeText(url)
    toast.value = 'Ссылка скопирована'
  } catch {
    error.value = 'Не удалось поделиться'
  }
}

onMounted(load)
</script>

<style scoped>
.summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 12px 6px;
  border-radius: var(--radius-sm);
  background: var(--surface);
  border: 1px solid var(--border);
}
.tile strong { font-family: var(--font-display); font-size: 20px; }
.tile span { font-size: 10px; color: var(--text-faint); }

.invite { border-color: var(--border-strong); }
.code {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 14px;
  border-radius: var(--radius-sm);
  border: 1px dashed var(--border-strong);
  background: var(--input);
}
.code span {
  font-family: var(--font-display);
  font-size: 26px;
  letter-spacing: 0.28em;
  background: var(--gradient-brand);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.code i { font-style: normal; font-size: 11px; color: var(--text-faint); }

.quest { display: flex; align-items: center; gap: 12px; }
.quest__icon {
  width: 40px;
  height: 40px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--gradient-soft);
  border: 1px solid var(--border);
  font-size: 17px;
  color: var(--brand-cyan-soft);
}
.quest__body { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.quest__count { color: var(--text-faint); }
.quest__action { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex: none; }
.quest__reward {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--warning);
  font-variant-numeric: tabular-nums;
}
.done { color: var(--success); }
</style>
