<template>
  <AppHeader
    v-if="auth.isAuthenticated"
    :coins="auth.user?.coins ?? 0"
    :points="auth.user?.total_points ?? 0"
    @logout="logout"
  />

  <RouterView v-slot="{ Component }">
    <component :is="Component" />
  </RouterView>

  <AppNav v-if="auth.isAuthenticated" :tabs="tabs" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppNav from '@/components/AppNav.vue'
import { trades as tradesApi } from '@/api/endpoints'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const incomingCount = ref(0)

const tabs = computed(() => [
  { to: '/collection', label: 'Коллекция', icon: '🃏' },
  { to: '/shop', label: 'Бустеры', icon: '🎁' },
  { to: '/squad', label: 'Состав', icon: '⚽' },
  { to: '/quests', label: 'Квесты', icon: '🎯' },
  { to: '/tournament', label: 'Турнир', icon: '🏟️' },
  { to: '/trades', label: 'Обмены', icon: '🔁', badge: incomingCount.value || undefined },
])

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(async () => {
  await auth.refresh()
  if (!auth.isAuthenticated) return
  try {
    incomingCount.value = (await tradesApi.incoming()).length
  } catch {
    incomingCount.value = 0
  }
})
</script>
