<template>
  <div class="page auth">
    <div class="hero">
      <span class="hero__badge">Games of the Future · Astana 2026</span>
      <h1 class="hero__title">
        Собери свою<br /><span class="gradient-text">пятёрку</span>
      </h1>
      <p class="hero__lead">
        Коллекционные карточки Phygital Football: открывай бустеры, меняйся с другими
        менеджерами и заводи команду в реальную турнирную сетку.
      </p>
      <div class="hero__facts">
        <span><b>127</b> атлетов</span>
        <span><b>16</b> клубов</span>
        <span><b>28</b> матчей</span>
      </div>
    </div>

    <div class="card-surface stack">
      <div class="switch">
        <button :class="{ on: mode === 'login' }" @click="mode = 'login'">Вход</button>
        <button :class="{ on: mode === 'register' }" @click="mode = 'register'">Регистрация</button>
      </div>

      <form class="stack" @submit.prevent="submit">
        <label class="stack small">
          <span class="muted">Имя пользователя</span>
          <input v-model.trim="username" autocomplete="username" required minlength="3" />
        </label>

        <label v-if="mode === 'register'" class="stack small">
          <span class="muted">Email</span>
          <input v-model.trim="email" type="email" autocomplete="email" required />
        </label>

        <label v-if="mode === 'register'" class="stack small">
          <span class="muted">Код друга <i class="muted">(необязательно)</i></span>
          <input v-model.trim="referral" maxlength="16" placeholder="ABC123" style="text-transform: uppercase" />
        </label>

        <label class="stack small">
          <span class="muted">Пароль</span>
          <input v-model="password" type="password" autocomplete="current-password" required minlength="8" />
        </label>

        <p v-if="error" class="alert alert--error">{{ error }}</p>
        <p v-if="notice" class="alert alert--success">{{ notice }}</p>

        <button class="btn btn--block" type="submit" :disabled="busy">
          {{ busy ? 'Подождите…' : mode === 'login' ? 'Войти' : 'Создать аккаунт' }}
        </button>
      </form>

      <p class="small muted center">
        При регистрации выдаётся 1000 монет. Игроков нужно купить в бустерах — в стартовом
        вратарь гарантирован.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const email = ref('')
const password = ref('')
const referral = ref('')
const busy = ref(false)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)

onMounted(() => {
  // an invite link lands here as /login?ref=CODE
  const code = route.query.ref
  if (typeof code === 'string' && code) {
    referral.value = code.toUpperCase()
    mode.value = 'register'
  }
})

async function submit() {
  busy.value = true
  error.value = null
  notice.value = null
  try {
    if (mode.value === 'login') {
      await auth.login(username.value, password.value)
    } else {
      const bonus = await auth.register(
        username.value,
        email.value,
        password.value,
        referral.value || null,
      )
      if (bonus) notice.value = `Бонус за код друга: ${bonus} монет`
    }
    await router.push('/collection')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось выполнить вход'
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.auth {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 22px;
  padding-bottom: 32px;
}

.hero { text-align: center; padding: 18px 0 4px; }
.hero__badge {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--brand-cyan-soft);
  border: 1px solid rgba(1, 160, 234, 0.35);
  background: rgba(1, 160, 234, 0.08);
  margin-bottom: 18px;
}
.hero__title {
  font-size: clamp(34px, 11vw, 52px);
  line-height: 1.02;
  letter-spacing: -0.035em;
  margin-bottom: 14px;
}
.hero__lead {
  color: var(--text-dim);
  max-width: 34ch;
  margin: 0 auto;
}
.hero__facts {
  display: flex;
  justify-content: center;
  gap: 22px;
  margin-top: 20px;
  font-size: 12px;
  color: var(--text-faint);
}
.hero__facts b {
  display: block;
  font-family: var(--font-display);
  font-size: 20px;
  color: var(--text);
}

.switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: var(--input);
  border: 1px solid var(--border);
}
.switch button {
  min-height: 38px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-dim);
  transition: background 0.18s ease, color 0.18s ease;
}
.switch button.on {
  background: var(--gradient-brand);
  color: #fff;
  box-shadow: 0 4px 14px rgba(112, 0, 220, 0.3);
}
</style>
