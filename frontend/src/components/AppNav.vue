<template>
  <nav class="nav">
    <RouterLink v-for="tab in tabs" :key="tab.to" :to="tab.to" class="tab">
      <span class="tab__glow" aria-hidden="true" />
      <span class="tab__icon" aria-hidden="true">{{ tab.icon }}</span>
      <span class="tab__label">{{ tab.label }}</span>
      <span v-if="tab.badge" class="tab__badge">{{ tab.badge > 9 ? '9+' : tab.badge }}</span>
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
defineProps<{
  tabs: Array<{ to: string; label: string; icon: string; badge?: number }>
}>()
</script>

<style scoped>
.nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: calc(var(--nav-height) + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  display: flex;
  background: linear-gradient(0deg, rgba(4, 3, 14, 0.97), rgba(7, 6, 24, 0.86));
  backdrop-filter: blur(18px);
  border-top: 1px solid var(--border);
  z-index: 30;
}

.tab {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  text-decoration: none;
  color: var(--text-faint);
  font-size: 10px;
  font-weight: 500;
  transition: color 0.18s ease;
  min-width: 0;
}
.tab__icon { font-size: 18px; line-height: 1; transition: transform 0.18s ease; }
.tab__label {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 2px;
}

/* the active tab is marked by a brand-coloured bar and a soft bloom */
.tab__glow {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 2px;
  border-radius: 0 0 3px 3px;
  background: var(--gradient-brand);
  transition: width 0.22s ease;
}
.tab.router-link-active { color: var(--text); }
.tab.router-link-active .tab__glow { width: 46%; }
.tab.router-link-active .tab__icon { transform: translateY(-1px) scale(1.08); }
.tab.router-link-active::after {
  content: '';
  position: absolute;
  top: -14px;
  width: 46px;
  height: 30px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(164, 67, 255, 0.4), transparent 70%);
  pointer-events: none;
}

.tab__badge {
  position: absolute;
  top: 7px;
  right: 50%;
  transform: translateX(17px);
  background: var(--danger);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  min-width: 16px;
  height: 16px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  padding: 0 4px;
  box-shadow: 0 2px 8px rgba(255, 77, 109, 0.5);
}
</style>
