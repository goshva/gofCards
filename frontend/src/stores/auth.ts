import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { auth as authApi } from '@/api/endpoints'
import type { User } from '@/types'

const TOKEN_KEY = 'gof_cards_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.role === 'ADMIN')

  function setToken(value: string | null) {
    token.value = value
    if (value) localStorage.setItem(TOKEN_KEY, value)
    else localStorage.removeItem(TOKEN_KEY)
  }

  async function login(username: string, password: string) {
    const resp = await authApi.login(username, password)
    setToken(resp.access_token)
    user.value = resp.user
  }

  async function register(
    username: string,
    email: string,
    password: string,
    referralCode?: string | null,
  ) {
    const resp = await authApi.register(username, email, password, referralCode)
    setToken(resp.token.access_token)
    user.value = resp.token.user
    return resp.referral_bonus
  }

  async function refresh() {
    if (!token.value) return
    loading.value = true
    try {
      user.value = await authApi.me()
    } catch {
      setToken(null)
      user.value = null
    } finally {
      loading.value = false
    }
  }

  function logout() {
    setToken(null)
    user.value = null
  }

  /** Keeps the coin counter in the header honest after a purchase or trade. */
  function setCoins(coins: number) {
    if (user.value) user.value.coins = coins
  }

  return { token, user, loading, isAuthenticated, isAdmin, login, register, refresh, logout, setCoins }
})
