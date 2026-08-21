<template>
  <div class="page stack">
    <h1>Магазин бустеров</h1>
    <p class="muted small">Баланс: {{ auth.user?.coins ?? 0 }} монет</p>

    <p v-if="error" class="alert alert--error">{{ error }}</p>

    <p class="alert alert--info small">
      Карточки из обычных бустеров рассчитаны на 6 турниров и после этого сгорают. Коллекционный
      бустер выдаёт вечные — они не изнашиваются никогда.
    </p>

    <div v-for="pack in packs" :key="pack.id" class="card-surface stack" :class="{ collector: pack.grants_permanent }">
      <div class="row row--between">
        <div>
          <h2>{{ pack.name }}</h2>
          <p class="small muted">{{ pack.description }}</p>
        </div>
        <span class="price">{{ pack.price }}<i>◈</i></span>
      </div>

      <div class="scroller">
        <span v-for="(count, rarity) in pack.contents_json" :key="rarity" class="chip">
          {{ contentLabel(String(rarity)) }} × {{ count }}
        </span>
        <span class="chip">карточка команды ~{{ pack.team_card_chance }}%</span>
        <span v-if="pack.guarantees_goalkeeper" class="chip chip--gk">вратарь гарантирован</span>
        <span v-if="pack.grants_permanent" class="chip chip--forever">∞ вечные</span>
      </div>

      <button
        class="btn btn--block"
        :disabled="busyId !== null || (auth.user?.coins ?? 0) < pack.price"
        @click="open(pack)"
      >
        {{ busyId === pack.id ? 'Открываем…' : (auth.user?.coins ?? 0) < pack.price ? 'Не хватает монет' : 'Открыть' }}
      </button>
    </div>

    <section class="stack">
      <h2>Купить за деньги</h2>
      <p class="small muted">
        Вечные карточки не изнашиваются в турнирах. Оплата в тестовом режиме — деньги не
        списываются.
      </p>
      <div v-for="product in products" :key="product.sku" class="card-surface offer">
        <div class="offer__body">
          <strong>{{ product.title }}</strong>
          <span class="small muted">{{ product.subtitle }}</span>
        </div>
        <button class="btn btn--sm" @click="checkoutProduct = product">
          {{ product.price.toLocaleString('ru-RU') }} ₸
        </button>
      </div>
    </section>

    <PackReveal :cards="revealed" @close="revealed = []" />
    <CheckoutSheet
      :product="checkoutProduct"
      @close="checkoutProduct = null"
      @paid="onPaid"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import CheckoutSheet from '@/components/CheckoutSheet.vue'
import PackReveal from '@/components/PackReveal.vue'
import { cards as cardsApi, store as storeApi } from '@/api/endpoints'
import { useAuthStore } from '@/stores/auth'
import { useCollectionStore } from '@/stores/collection'
import type { Pack, Payment, Product, UserCard } from '@/types'

const auth = useAuthStore()
const collection = useCollectionStore()

const packs = ref<Pack[]>([])
const products = ref<Product[]>([])
const checkoutProduct = ref<Product | null>(null)
const revealed = ref<UserCard[]>([])
const busyId = ref<number | null>(null)
const error = ref<string | null>(null)

const LABELS: Record<string, string> = {
  COMMON: 'Обычная',
  RARE: 'Редкая',
  EPIC: 'Эпик',
  LEGENDARY: 'Легенда',
  ANY: 'Случайная',
}
function contentLabel(key: string) {
  return LABELS[key.toUpperCase()] ?? key
}

async function open(pack: Pack) {
  busyId.value = pack.id
  error.value = null
  try {
    const result = await cardsApi.openPack(pack.id)
    auth.setCoins(result.coins_left)
    revealed.value = result.cards
    await collection.load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось открыть бустер'
  } finally {
    busyId.value = null
  }
}

async function onPaid(_payment: Payment) {
  await auth.refresh()
  await collection.load()
}

onMounted(async () => {
  try {
    const [packList, productList] = await Promise.all([cardsApi.packs(), storeApi.products()])
    packs.value = packList
    products.value = productList
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить магазин'
  }
})
</script>

<style scoped>
.collector {
  overflow: hidden;
  border-color: rgba(255, 193, 7, 0.45);
  box-shadow: 0 10px 34px rgba(255, 193, 7, 0.16), var(--shadow-card);
}
.collector::before {
  content: 'вечные';
  position: absolute;
  top: 12px;
  right: -30px;
  transform: rotate(38deg);
  width: 120px;
  text-align: center;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--bg-deep);
  background: linear-gradient(135deg, #ffd77a, #ffc107);
  padding: 3px 0;
}
.chip--forever { color: var(--rarity-legendary); border-color: rgba(255, 193, 7, 0.5); }
.chip--gk { color: var(--warning); border-color: rgba(255, 201, 77, 0.4); }
.price {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.price i { font-style: normal; font-size: 13px; color: var(--warning); }
.offer { display: flex; align-items: center; gap: 12px; }
.offer__body { flex: 1; display: flex; flex-direction: column; min-width: 0; }
</style>
