<template>
  <div class="page stack">
    <h1>Матчи</h1>

    <div v-if="live.length" class="stack">
      <h2>Идут сейчас</h2>
      <MatchRow v-for="match in live" :key="match.id" :match="match" />
    </div>

    <div class="scroller">
      <button class="chip" :class="{ 'chip--active': !status }" @click="setStatus(undefined)">Все</button>
      <button class="chip" :class="{ 'chip--active': status === 'SCHEDULED' }" @click="setStatus('SCHEDULED')">
        Предстоящие
      </button>
      <button class="chip" :class="{ 'chip--active': status === 'COMPLETED' }" @click="setStatus('COMPLETED')">
        Завершённые
      </button>
    </div>

    <p v-if="error" class="alert alert--error">{{ error }}</p>
    <p v-if="loading" class="empty empty--loading">Загрузка матчей</p>

    <template v-else>
      <MatchRow v-for="match in items" :key="match.id" :match="match" />
      <p v-if="!items.length" class="empty">Матчей нет. Запустите синхронизацию на бэкенде.</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import MatchRow from '@/components/MatchRow.vue'
import { matches as matchesApi } from '@/api/endpoints'
import type { Match, MatchStatus } from '@/types'

const items = ref<Match[]>([])
const live = ref<Match[]>([])
const status = ref<MatchStatus | undefined>(undefined)
const loading = ref(false)
const error = ref<string | null>(null)

let timer: number | undefined

async function load() {
  loading.value = true
  error.value = null
  try {
    const page = await matchesApi.list({ status: status.value, limit: 100 })
    items.value = page.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить матчи'
  } finally {
    loading.value = false
  }
}

async function loadLive() {
  try {
    live.value = await matchesApi.live()
  } catch {
    live.value = []
  }
}

function setStatus(next: MatchStatus | undefined) {
  status.value = next
  load()
}

onMounted(async () => {
  await Promise.all([load(), loadLive()])
  // the MVP polls instead of holding a socket open
  timer = window.setInterval(loadLive, 30_000)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>
