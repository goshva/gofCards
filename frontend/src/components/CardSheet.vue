<template>
  <Teleport to="body">
    <div v-if="card" class="sheet" @click.self="$emit('close')">
      <div class="sheet__panel">
        <div class="sheet__grip" />

        <div class="sheet__head">
          <CardTile :card="card" class="sheet__tile" />
          <div class="stack">
            <h2>{{ t.name }}</h2>
            <p class="muted small">{{ fullName }}</p>
            <p v-if="t.rank" class="rankline">
              <span class="rankline__value">#{{ t.rank }}</span>
              <span class="small muted">в рейтинге турнира</span>
            </p>
            <dl class="facts small">
              <div><dt>Редкость</dt><dd>{{ RARITY_LABELS[t.rarity] ?? t.rarity }}</dd></div>
              <div><dt>Рейтинг</dt><dd>{{ t.ovr || '—' }}</dd></div>
              <div v-if="t.position"><dt>Позиция</dt><dd>{{ t.position === 'GOALKEEPER' ? 'Вратарь' : 'Полевой' }}</dd></div>
              <div v-if="player?.age"><dt>Возраст</dt><dd>{{ player.age }}</dd></div>
              <div v-if="player?.jersey_number"><dt>Номер</dt><dd>{{ player.jersey_number }}</dd></div>
              <div v-if="country"><dt>Страна</dt><dd>{{ countryCode(country) }} · {{ country }}</dd></div>
              <div><dt>Цена</dt><dd>{{ t.base_price }} монет</dd></div>
              <div>
                <dt>Ресурс</dt>
                <dd :class="card.is_permanent ? 'forever' : ''">
                  {{ card.is_permanent ? 'вечная' : `${card.runs_left ?? 0} из 6 турниров` }}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <section class="stack">
          <h3>Характеристики</h3>
          <div v-for="key in ATTRIBUTE_ORDER" :key="key" class="bar" :title="ATTRIBUTE_TITLES[key]">
            <span class="bar__label">{{ ATTRIBUTE_LABELS[key] }}</span>
            <span class="bar__track">
              <span class="bar__fill" :style="{ width: `${t.attributes?.[key] ?? 0}%` }" />
            </span>
            <span class="bar__value">{{ t.attributes?.[key] ?? '—' }}</span>
          </div>
          <p class="small muted">
            Характеристики рассчитаны из реальных результатов команды на турнире — GoFuture не
            публикует индивидуальную статистику игроков.
          </p>
        </section>

        <p v-if="!card.is_permanent && (card.runs_left ?? 0) <= 2" class="alert alert--error small">
          Карточка скоро сгорит: осталось турниров — {{ card.runs_left ?? 0 }}. Вечные карточки
          выпадают только из коллекционного бустера.
        </p>

        <section v-if="player && player.matches_played" class="card-surface stack">
          <h3 class="clubline">
            <img v-if="player.team?.logo_url" :src="player.team.logo_url" alt="" class="clubline__crest" />
            {{ player.team?.title }}
          </h3>
          <div class="record small">
            <span>{{ player.matches_played }} матчей</span>
            <span class="win">{{ player.wins }} П</span>
            <span>{{ player.draws }} Н</span>
            <span class="loss">{{ player.losses }} П</span>
            <span>мячи {{ player.goals_for }}:{{ player.goals_against }}</span>
          </div>
          <p class="small muted">Дошла до стадии: {{ roundLabel(player.best_round) }}</p>
        </section>

        <p v-if="card.locked_by_trade" class="alert alert--error">
          Карточка участвует в активном предложении обмена
        </p>

        <div class="row">
          <RouterLink class="btn btn--ghost btn--block" to="/trades/new" @click="$emit('close')">
            Обменять
          </RouterLink>
          <RouterLink
            v-if="card.card_type === 'PLAYER'"
            class="btn btn--block"
            to="/squad"
            @click="$emit('close')"
          >
            В состав
          </RouterLink>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import CardTile from './CardTile.vue'
import {
  ATTRIBUTE_LABELS,
  ATTRIBUTE_ORDER,
  ATTRIBUTE_TITLES,
  RARITY_LABELS,
  countryCode,
  roundLabel,
} from '@/lib/format'
import type { UserCard } from '@/types'

const props = defineProps<{ card: UserCard | null }>()
defineEmits<{ close: [] }>()

const t = computed(() => props.card!.template)
const player = computed(() => props.card?.template.player ?? null)
const country = computed(() => player.value?.country ?? props.card?.template.team?.country ?? null)
const fullName = computed(() => {
  const p = player.value
  if (!p) return props.card?.template.subtitle ?? ''
  return [p.first_name, p.last_name].filter(Boolean).join(' ') || p.nickname
})
</script>

<style scoped>
.sheet {
  position: fixed;
  inset: 0;
  background: rgba(4, 7, 14, 0.72);
  display: flex;
  align-items: flex-end;
  z-index: 50;
}
.sheet__panel {
  width: 100%;
  max-width: 780px;
  margin: 0 auto;
  background: linear-gradient(180deg, #1a1738, #0c0a20);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  border-top: 1px solid var(--border-strong);
  box-shadow: 0 -20px 60px rgba(112, 0, 220, 0.22);
  padding: 10px 14px calc(20px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 90dvh;
  overflow-y: auto;
  animation: rise 0.18s ease-out;
}
@keyframes rise {
  from { transform: translateY(16px); opacity: 0.6; }
  to { transform: translateY(0); opacity: 1; }
}
.sheet__grip {
  width: 38px;
  height: 4px;
  border-radius: 999px;
  background: var(--border);
  margin: 0 auto 4px;
}
.sheet__head { display: grid; grid-template-columns: 138px 1fr; gap: 14px; align-items: start; }
.sheet__tile { pointer-events: none; }

.rankline { display: flex; align-items: baseline; gap: 6px; margin: 0; }
.rankline__value {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  background: var(--gradient-brand);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.facts { display: grid; gap: 4px; margin: 0; }
.facts div { display: flex; justify-content: space-between; gap: 10px; }
.facts dt { color: var(--text-dim); margin: 0; }
.facts dd { margin: 0; }

.bar { display: grid; grid-template-columns: 34px 1fr 28px; align-items: center; gap: 8px; }
.bar__label { font-size: 11px; color: var(--text-dim); letter-spacing: 0.04em; }
.bar__track { height: 7px; border-radius: 999px; background: var(--input); overflow: hidden; }
.bar__fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--gradient-brand);
  box-shadow: 0 0 12px rgba(164, 67, 255, 0.4);
  transition: width 0.4s cubic-bezier(0.2, 0.8, 0.3, 1);
}
.bar__value { font-size: 12px; font-variant-numeric: tabular-nums; text-align: right; }

.record { display: flex; flex-wrap: wrap; gap: 10px; }
.record .win { color: var(--success); }
.record .loss { color: var(--danger); }
.forever { color: var(--rarity-legendary); font-weight: 700; }
.clubline { display: flex; align-items: center; gap: 8px; }
.clubline__crest { width: 22px; height: 24px; object-fit: contain; }
</style>
