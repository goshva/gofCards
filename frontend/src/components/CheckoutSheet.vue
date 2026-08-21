<template>
  <Teleport to="body">
    <div v-if="product" class="sheet" @click.self="close">
      <div class="panel">
        <div class="grip" />

        <div class="sandbox">
          <b>ТЕСТОВЫЙ РЕЖИМ</b>
          <span>Оплата имитируется приложением. Деньги не списываются, реквизиты карты не
            принимаются и не сохраняются.</span>
        </div>

        <div class="row row--between">
          <div>
            <h2>{{ product.title }}</h2>
            <p class="small muted">{{ product.subtitle }}</p>
          </div>
          <span class="amount">{{ product.price.toLocaleString('ru-RU') }}<i>₸</i></span>
        </div>

        <div v-if="checkout" class="card-mock" aria-hidden="true">
          <span class="card-mock__brand">SANDBOX</span>
          <span class="card-mock__number">{{ checkout.test_card.number }}</span>
          <span class="card-mock__row">
            <span>{{ checkout.test_card.expiry }}</span>
            <span>CVC {{ checkout.test_card.cvc }}</span>
          </span>
          <span class="card-mock__hint">демонстрационные реквизиты, поля не редактируются</span>
        </div>

        <p v-if="error" class="alert alert--error small">{{ error }}</p>

        <p v-if="result?.status === 'SUCCEEDED'" class="alert alert--success small">
          Оплата прошла. {{ deliveredText }}
        </p>
        <p v-else-if="result?.status === 'FAILED'" class="alert alert--error small">
          {{ result.failure_reason }}
        </p>

        <template v-if="!result">
          <button class="btn btn--block" :disabled="busy" @click="pay('success')">
            {{ busy ? 'Проводим оплату…' : `Оплатить ${product.price.toLocaleString('ru-RU')} ₸` }}
          </button>
          <button class="btn btn--ghost btn--block btn--sm" :disabled="busy" @click="pay('failure')">
            Смоделировать отказ банка
          </button>
        </template>
        <button v-else class="btn btn--block" @click="close">Готово</button>

        <p class="small muted center">
          Ссылка на платёж: <code>{{ checkout?.payment.reference ?? '—' }}</code>
        </p>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { store as storeApi } from '@/api/endpoints'
import type { Checkout, Payment, Product } from '@/types'

const props = defineProps<{ product: Product | null }>()
const emit = defineEmits<{ close: []; paid: [payment: Payment] }>()

const checkout = ref<Checkout | null>(null)
const result = ref<Payment | null>(null)
const busy = ref(false)
const error = ref<string | null>(null)

const deliveredText = computed(() => {
  const d = result.value?.delivered
  if (!d) return ''
  const parts: string[] = []
  if (d.coins) parts.push(`Начислено ${d.coins.toLocaleString('ru-RU')} монет`)
  if (d.cards?.length) parts.push(`Получено вечных карточек: ${d.cards.length}`)
  return parts.join('. ')
})

watch(
  () => props.product,
  async (product) => {
    checkout.value = null
    result.value = null
    error.value = null
    if (!product) return
    try {
      checkout.value = await storeApi.checkout(product.sku)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Не удалось открыть оплату'
    }
  },
  { immediate: true },
)

async function pay(outcome: 'success' | 'failure') {
  if (!checkout.value) return
  busy.value = true
  error.value = null
  try {
    const payment = await storeApi.confirm(checkout.value.payment.id, outcome)
    result.value = payment
    if (payment.status === 'SUCCEEDED') emit('paid', payment)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Оплата не прошла'
  } finally {
    busy.value = false
  }
}

function close() {
  emit('close')
}
</script>

<style scoped>
.sheet {
  position: fixed;
  inset: 0;
  background: rgba(3, 2, 10, 0.78);
  display: flex;
  align-items: flex-end;
  z-index: 60;
}
.panel {
  width: 100%;
  max-width: 780px;
  margin: 0 auto;
  background: linear-gradient(180deg, #1a1738, #0c0a20);
  border-top: 1px solid var(--border-strong);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  box-shadow: 0 -20px 60px rgba(112, 0, 220, 0.25);
  padding: 10px 16px calc(22px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 92dvh;
  overflow-y: auto;
}
.grip {
  width: 38px;
  height: 4px;
  border-radius: 999px;
  background: var(--border);
  margin: 0 auto 2px;
}

.sandbox {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 11px 13px;
  border-radius: var(--radius-sm);
  background: rgba(255, 201, 77, 0.1);
  border: 1px solid rgba(255, 201, 77, 0.4);
  font-size: 12px;
  color: #ffdf9a;
}
.sandbox b { letter-spacing: 0.12em; font-size: 11px; }

.amount {
  display: inline-flex;
  align-items: baseline;
  gap: 3px;
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.amount i { font-style: normal; font-size: 15px; color: var(--text-dim); }

.card-mock {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border-radius: var(--radius);
  background: var(--gradient-brand-v);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  box-shadow: var(--glow-violet);
}
.card-mock__brand { font-size: 10px; letter-spacing: 0.2em; opacity: 0.85; }
.card-mock__number {
  font-family: var(--font-display);
  font-size: 19px;
  letter-spacing: 0.08em;
  font-variant-numeric: tabular-nums;
}
.card-mock__row { display: flex; gap: 16px; font-size: 12px; opacity: 0.9; }
.card-mock__hint { font-size: 10px; opacity: 0.75; }

code {
  background: var(--input);
  padding: 1px 6px;
  border-radius: 5px;
  font-size: 11px;
}
</style>
