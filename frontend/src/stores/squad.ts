import { defineStore } from 'pinia'
import { ref } from 'vue'
import { squad as squadApi } from '@/api/endpoints'
import type { PositionSlot, Squad, ValidationResult } from '@/types'

export const useSquadStore = defineStore('squad', () => {
  const squad = ref<Squad | null>(null)
  const validation = ref<ValidationResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function run<T>(fn: () => Promise<T>): Promise<T | null> {
    loading.value = true
    error.value = null
    try {
      return await fn()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Ошибка'
      return null
    } finally {
      loading.value = false
    }
  }

  async function load(matchId?: number | null) {
    const result = await run(() => squadApi.current(matchId))
    if (result) squad.value = result
  }

  async function select(cardId: string, slot: PositionSlot, matchId?: number | null) {
    const result = await run(() => squadApi.select(cardId, slot, matchId))
    if (result) squad.value = result
    return result !== null
  }

  async function remove(slot: PositionSlot, matchId?: number | null) {
    const result = await run(() => squadApi.remove(slot, matchId))
    if (result) squad.value = result
  }

  async function setCaptain(entryId: string, vice = false, matchId?: number | null) {
    const result = await run(() => squadApi.captain(entryId, vice, matchId))
    if (result) squad.value = result
  }

  async function validate(matchId?: number | null) {
    validation.value = await run(() => squadApi.validate(matchId))
  }

  return { squad, validation, loading, error, load, select, remove, setCaptain, validate }
})
