<template>
  <button
    class="fut"
    :class="[`fut--${rarity.toLowerCase()}`, { 'fut--selected': selected, 'fut--team': isTeam }]"
    @click="$emit('select', card)"
  >
    <span class="fut__shine" aria-hidden="true" />

    <span class="fut__top">
      <span class="fut__ovr">
        <span class="fut__ovr-value">{{ ovr || '—' }}</span>
        <span class="fut__ovr-pos">{{ isTeam ? 'CLUB' : positionLabel(template.position) }}</span>
      </span>

      <span class="fut__art">
        <img v-if="image" :src="image" :alt="template.name" loading="lazy" @error="broken = true" />
        <span v-else class="fut__mono" :style="{ background: teamColor }">{{ monogram(template.name) }}</span>
      </span>

      <span v-if="rank" class="fut__rank">#{{ rank }}</span>
    </span>

    <span class="fut__name">{{ template.name }}</span>

    <span class="fut__meta">
      <span class="fut__cc">{{ countryCode(country) }}</span>
      <img v-if="crest" class="fut__crest" :src="crest" alt="" loading="lazy" />
      <span class="fut__club" :style="{ color: teamColor }">{{ clubLabel }}</span>
      <span v-if="shirt" class="fut__shirt">#{{ shirt }}</span>
    </span>

    <span class="fut__stats">
      <span v-for="key in ATTRIBUTE_ORDER" :key="key" class="fut__stat" :title="ATTRIBUTE_TITLES[key]">
        <b>{{ template.attributes?.[key] ?? '—' }}</b>
        <i>{{ ATTRIBUTE_LABELS[key] }}</i>
      </span>
    </span>

    <span v-if="card" class="fut__life" :title="lifeTitle">
      <template v-if="card.is_permanent">
        <span class="fut__forever">∞ вечная</span>
      </template>
      <template v-else>
        <i v-for="n in LIFESPAN" :key="n" class="pip" :class="{ spent: n > (card.runs_left ?? 0) }" />
      </template>
    </span>

    <span class="fut__flags">
      <span class="fut__rarity">{{ RARITY_LABELS[rarity] ?? rarity }}</span>
      <span v-if="card?.in_squad" class="flag flag--squad">в составе</span>
      <span v-if="card?.locked_by_trade" class="flag flag--locked">в обмене</span>
    </span>
  </button>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  ATTRIBUTE_LABELS,
  ATTRIBUTE_ORDER,
  ATTRIBUTE_TITLES,
  RARITY_LABELS,
  countryCode,
  monogram,
  positionLabel,
} from '@/lib/format'
import type { CardTemplate, UserCard } from '@/types'

const LIFESPAN = 6

const props = defineProps<{
  card?: UserCard
  template?: CardTemplate
  selected?: boolean
}>()

defineEmits<{ select: [card: UserCard | undefined] }>()

const broken = ref(false)
const template = computed(() => (props.card?.template ?? props.template) as CardTemplate)
const rarity = computed(() => template.value.rarity)
const isTeam = computed(() => template.value.card_type === 'TEAM')
const ovr = computed(() => template.value.ovr)
const rank = computed(() => template.value.rank)
const image = computed(() =>
  broken.value ? null : (template.value.player?.photo_url ?? template.value.image_url),
)
const country = computed(() => template.value.player?.country ?? template.value.team?.country)
const shirt = computed(() => template.value.player?.jersey_number)
const teamColor = computed(
  () => template.value.player?.team?.color ?? template.value.team?.color ?? 'var(--accent)',
)
const clubLabel = computed(() => {
  const team = template.value.player?.team ?? template.value.team
  return team?.short_title ?? team?.title ?? '—'
})
const crest = computed(() => {
  // a team card already shows its crest as the main art
  if (isTeam.value) return null
  return template.value.player?.team?.logo_url ?? null
})
const lifeTitle = computed(() => {
  const c = props.card
  if (!c) return ''
  if (c.is_permanent) return 'Коллекционная карточка — не изнашивается'
  return `Осталось турниров: ${c.runs_left ?? 0} из ${LIFESPAN}`
})
</script>

<style scoped>
.fut {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 5px;
  width: 100%;
  padding: 9px 9px 10px;
  min-height: auto;
  text-align: center;
  overflow: hidden;
  border-radius: var(--radius);
  color: #f4f7ff;
  background: var(--frame, linear-gradient(165deg, #2a2c47, #14162b));
  border: 1px solid var(--edge, rgba(255, 255, 255, 0.16));
  box-shadow: var(--shadow-card);
  transition: transform 0.12s ease, box-shadow 0.2s ease;
}
.fut:hover { transform: translateY(-2px); }
.fut:active { transform: scale(0.975); }
.fut--selected {
  outline: 2px solid transparent;
  outline-offset: -2px;
  box-shadow: 0 0 0 2px var(--brand-cyan), 0 0 0 6px rgba(1, 160, 234, 0.22), var(--shadow-card);
}

/* rarity frames, keyed to the brand ramp: grey -> cyan -> violet -> gold */
.fut--common {
  --frame: linear-gradient(165deg, #2a2c47, #14162b);
  --edge: rgba(143, 155, 194, 0.35);
  --accent-ink: #c6cee8;
}
.fut--rare {
  --frame: linear-gradient(165deg, #06456e, #041c33);
  --edge: rgba(1, 160, 234, 0.6);
  --accent-ink: #7fd3ff;
  box-shadow: 0 8px 24px rgba(1, 160, 234, 0.18), var(--shadow-card);
}
.fut--epic {
  --frame: linear-gradient(165deg, #4b1088, #22063f);
  --edge: rgba(164, 67, 255, 0.65);
  --accent-ink: #d7aeff;
  box-shadow: 0 8px 26px rgba(164, 67, 255, 0.26), var(--shadow-card);
}
.fut--legendary {
  --frame: linear-gradient(160deg, #6d4a06 0%, #2a1c02 45%, #7a5a10 100%);
  --edge: rgba(255, 201, 77, 0.8);
  --accent-ink: #ffd77a;
  box-shadow: 0 10px 30px rgba(255, 193, 7, 0.3), var(--shadow-card);
}
.fut--team {
  --frame: linear-gradient(165deg, #17224a, #0a0f22);
  --edge: rgba(1, 160, 234, 0.4);
}

.fut__shine {
  position: absolute;
  inset: -40% -60%;
  background: linear-gradient(
    72deg,
    transparent 42%,
    rgba(255, 255, 255, 0.16) 50%,
    transparent 58%
  );
  pointer-events: none;
}
.fut--legendary .fut__shine {
  background: linear-gradient(
    72deg,
    transparent 38%,
    rgba(255, 226, 150, 0.3) 50%,
    transparent 62%
  );
  animation: sweep 4.5s ease-in-out infinite;
}
@keyframes sweep {
  0%, 100% { transform: translateX(-14%); }
  50% { transform: translateX(14%); }
}

.fut__top {
  position: relative;
  display: grid;
  grid-template-columns: 30px 1fr 30px;
  align-items: start;
  gap: 2px;
}
.fut__ovr { display: flex; flex-direction: column; align-items: center; line-height: 1; }
.fut__ovr-value {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--accent-ink, #fff);
}
.fut__ovr-pos {
  font-size: 8px;
  letter-spacing: 0.08em;
  opacity: 0.75;
  margin-top: 2px;
}
.fut__rank {
  font-size: 9px;
  font-weight: 700;
  opacity: 0.7;
  justify-self: end;
}

.fut__art {
  display: grid;
  place-items: center;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.25);
  box-shadow: inset 0 0 0 1px var(--edge, rgba(255, 255, 255, 0.2));
}
.fut__art img { width: 100%; height: 100%; object-fit: cover; }
.fut__mono {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  font-size: 18px;
  font-weight: 800;
  color: var(--bg-deep);
}

.fut__name {
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-top: 1px solid var(--edge, rgba(255, 255, 255, 0.18));
  padding-top: 5px;
}

.fut__meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 10px;
  opacity: 0.9;
}
.fut__cc {
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  flex: none;
}
.fut__crest { width: 13px; height: 14px; object-fit: contain; flex: none; }
.fut__club { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fut__shirt { opacity: 0.6; }

.fut__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px 4px;
  border-top: 1px solid var(--edge, rgba(255, 255, 255, 0.18));
  padding-top: 5px;
}
.fut__stat { display: flex; flex-direction: column; line-height: 1.1; }
.fut__stat b { font-family: var(--font-display); font-size: 12px; font-weight: 600; }
.fut__stat i { font-style: normal; font-size: 8px; opacity: 0.65; letter-spacing: 0.04em; }

.fut__life { display: flex; align-items: center; justify-content: center; gap: 3px; min-height: 9px; }
.pip {
  width: 9px;
  height: 3px;
  border-radius: 999px;
  background: var(--success);
}
.pip.spent { background: rgba(255, 255, 255, 0.18); }
.fut__forever {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--rarity-legendary);
}

.fut__flags { display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; }
.fut__rarity {
  font-size: 8px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent-ink, #fff);
  opacity: 0.85;
}
.flag {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.35);
}
.flag--squad { color: var(--success); }
.flag--locked { color: var(--danger); }
</style>
