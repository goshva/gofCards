<template>
  <header class="header">
    <div class="header__inner">
      <RouterLink to="/" class="brand">
        <span class="brand__mark" aria-hidden="true" />
        <span class="brand__text">
          <b class="gradient-text">GoF</b><span>Cards</span>
        </span>
      </RouterLink>

      <div class="wallet">
        <span class="stat stat--coins" title="Монеты">
          <i aria-hidden="true">◈</i>{{ formatted(coins) }}
        </span>
        <span class="stat stat--points" title="Очки">
          <i aria-hidden="true">★</i>{{ formatted(points) }}
        </span>
        <button class="exit" title="Выйти" @click="$emit('logout')" aria-label="Выйти">⏻</button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ coins: number; points: number }>()
defineEmits<{ logout: [] }>()

function formatted(value: number): string {
  // long balances would push the wallet off a 320px screen
  if (value >= 100_000) return `${Math.round(value / 1000)}k`
  return value.toLocaleString('ru-RU')
}
</script>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: linear-gradient(180deg, rgba(7, 6, 24, 0.94), rgba(7, 6, 24, 0.72));
  backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--border);
  padding-top: env(safe-area-inset-top);
}
.header::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background: var(--gradient-brand);
  opacity: 0.5;
}

.header__inner {
  max-width: 780px;
  margin: 0 auto;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  text-decoration: none;
  /* a link is a tap target: keep it thumb-sized even though the mark is small */
  min-height: var(--tap);
  padding-right: 6px;
}
.brand__mark {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--gradient-brand);
  box-shadow: var(--glow-violet);
  position: relative;
}
.brand__mark::after {
  content: '';
  position: absolute;
  inset: 6px;
  border-radius: 3px;
  background: var(--bg-deep);
}
.brand__text {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 17px;
  letter-spacing: -0.02em;
  color: var(--text);
}
.brand__text span { opacity: 0.85; }

.wallet { display: flex; align-items: center; gap: 7px; }
.stat {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.04);
}
.stat i { font-style: normal; font-size: 11px; }
.stat--coins i { color: var(--warning); }
.stat--points i { color: var(--brand-cyan-soft); }

.exit {
  min-height: 32px;
  width: 32px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1;
  transition: color 0.16s ease, border-color 0.16s ease;
}
.exit:active { color: var(--danger); border-color: var(--danger); }
</style>
