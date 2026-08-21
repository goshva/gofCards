import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cards as cardsApi } from '@/api/endpoints'
import type { CollectionStats, Rarity, UserCard } from '@/types'

export const useCollectionStore = defineStore('collection', () => {
  const items = ref<UserCard[]>([])
  const stats = ref<CollectionStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const rarityFilter = ref<Rarity | ''>('')
  const typeFilter = ref<'' | 'PLAYER' | 'TEAM'>('')
  const search = ref('')
  const sort = ref<'ovr' | 'new'>('ovr')

  const filtered = computed(() => {
    const list = items.value.filter((card) => {
      if (rarityFilter.value && card.template.rarity !== rarityFilter.value) return false
      if (typeFilter.value && card.card_type !== typeFilter.value) return false
      if (search.value) {
        const needle = search.value.toLowerCase()
        const haystack = `${card.template.name} ${card.template.subtitle ?? ''}`.toLowerCase()
        if (!haystack.includes(needle)) return false
      }
      return true
    })
    if (sort.value === 'ovr') {
      // strongest cards first, so the collection opens on what is worth owning
      return [...list].sort((a, b) => (b.template.ovr ?? 0) - (a.template.ovr ?? 0))
    }
    return list
  })

  /** Cards that can go into a squad right now. */
  const availablePlayers = computed(() =>
    items.value.filter((c) => c.card_type === 'PLAYER' && !c.locked_by_trade),
  )

  async function load() {
    loading.value = true
    error.value = null
    try {
      const [page, collectionStats] = await Promise.all([
        cardsApi.collection({ limit: 200 }),
        cardsApi.stats(),
      ])
      items.value = page.items
      stats.value = collectionStats
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Не удалось загрузить коллекцию'
    } finally {
      loading.value = false
    }
  }

  return {
    items,
    stats,
    loading,
    error,
    rarityFilter,
    typeFilter,
    search,
    sort,
    filtered,
    availablePlayers,
    load,
  }
})
