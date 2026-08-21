<template>
  <Teleport to="body">
    <div v-if="cards.length" class="reveal" @click="revealNext">
      <p class="reveal__hint small muted">
        {{ allShown ? 'Нажмите, чтобы закрыть' : 'Нажмите, чтобы перевернуть' }}
      </p>
      <div class="reveal__grid">
        <div
          v-for="(card, index) in cards"
          :key="card.id"
          class="flip"
          :class="{ 'flip--open': index < shown }"
        >
          <div class="flip__inner">
            <div class="flip__back" />
            <div class="flip__front">
              <CardTile :card="card" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import CardTile from './CardTile.vue'
import type { UserCard } from '@/types'

const props = defineProps<{ cards: UserCard[] }>()
const emit = defineEmits<{ close: [] }>()

const shown = ref(0)
const allShown = computed(() => shown.value >= props.cards.length)

watch(
  () => props.cards,
  () => {
    shown.value = 0
  },
)

function revealNext() {
  if (allShown.value) {
    emit('close')
    return
  }
  shown.value += 1
}
</script>

<style scoped>
.reveal {
  position: fixed;
  inset: 0;
  z-index: 60;
  background:
    radial-gradient(60% 45% at 50% 22%, rgba(164, 67, 255, 0.35), transparent 70%),
    radial-gradient(70% 55% at 50% 78%, rgba(1, 160, 234, 0.22), transparent 72%),
    #04030e;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 20px;
}
.reveal__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(104px, 1fr));
  gap: 10px;
  width: 100%;
  max-width: 420px;
}
.flip { perspective: 800px; }
.flip__inner {
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.45s cubic-bezier(0.3, 0.9, 0.4, 1);
  aspect-ratio: 3 / 4.6;
}
.flip--open .flip__inner { transform: rotateY(180deg); }
.flip__back,
.flip__front {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  border-radius: 12px;
  overflow: hidden;
}
.flip__back {
  background: var(--gradient-brand-v);
  border: 1px solid rgba(255, 255, 255, 0.18);
  position: relative;
  overflow: hidden;
}
/* card back: a brand monogram behind a soft sheen */
.flip__back::before {
  content: '';
  position: absolute;
  inset: 8px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.22);
}
.flip__back::after {
  content: '';
  position: absolute;
  inset: -30%;
  background: linear-gradient(70deg, transparent 42%, rgba(255, 255, 255, 0.28) 50%, transparent 58%);
}
.flip__front { transform: rotateY(180deg); }
.reveal__hint { text-align: center; }
</style>
