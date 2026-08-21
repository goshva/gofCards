import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', redirect: '/collection' },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/collection', name: 'collection', component: () => import('@/views/CollectionView.vue') },
  { path: '/shop', name: 'shop', component: () => import('@/views/ShopView.vue') },
  { path: '/squad', name: 'squad', component: () => import('@/views/SquadView.vue') },
  { path: '/trades', name: 'trades', component: () => import('@/views/TradesView.vue') },
  { path: '/trades/new', name: 'trade-new', component: () => import('@/views/TradeCreateView.vue') },
  { path: '/quests', name: 'quests', component: () => import('@/views/QuestsView.vue') },
  { path: '/tournament', name: 'tournament', component: () => import('@/views/TournamentView.vue') },
  { path: '/ranking', name: 'ranking', component: () => import('@/views/RankingView.vue') },
  { path: '/matches', name: 'matches', component: () => import('@/views/MatchesView.vue') },
  { path: '/matches/:id', name: 'match', component: () => import('@/views/MatchDetailView.vue') },
  { path: '/leaderboard', name: 'leaderboard', component: () => import('@/views/LeaderboardView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/collection' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) return { name: 'login' }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'collection' }
  return true
})
