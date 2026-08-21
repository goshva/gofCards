import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import { configureClient } from './api/client'
import { useAuthStore } from './stores/auth'
import './styles/main.css'

const app = createApp(App)
app.use(createPinia())

// The client is wired to the store before the router boots, so a stale token
// bounces the user to the login screen instead of failing silently.
const auth = useAuthStore()
configureClient(
  () => auth.token,
  () => {
    auth.logout()
    router.push('/login')
  },
)

app.use(router)
app.mount('#app')

// PWA: registered after mount so it never delays first paint
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* offline support is a bonus, not a requirement */
    })
  })
}
