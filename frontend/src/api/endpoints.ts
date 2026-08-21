import { api } from './client'
import type {
  CardTemplate,
  CollectionStats,
  LeaderboardRow,
  Match,
  Pack,
  Page,
  Checkout,
  Payment,
  PerfectFive,
  Product,
  Quest,
  QuestBoard,
  RankingRow,
  PlayerBrief,
  Squad,
  TeamBrief,
  TournamentEntry,
  TournamentPreview,
  TradeOffer,
  User,
  UserCard,
  UserPublic,
  ValidationResult,
} from '@/types'

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export const auth = {
  register: (username: string, email: string, password: string, referralCode?: string | null) =>
    api.post<{ token: TokenResponse; welcome_cards: number; referral_bonus: number }>(
      '/auth/register',
      { username, email, password, referral_code: referralCode || null },
    ),
  login: (username: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { username, password }),
  me: () => api.get<User>('/auth/me'),
}

export const cards = {
  templates: (params: Record<string, string | number | undefined> = {}) =>
    api.get<Page<CardTemplate>>(`/cards/templates?${query(params)}`),
  collection: (params: Record<string, string | number | undefined> = {}) =>
    api.get<Page<UserCard>>(`/cards/my-collection?${query(params)}`),
  stats: () => api.get<CollectionStats>('/cards/my-collection/stats'),
  packs: () => api.get<Pack[]>('/cards/packs'),
  ranking: (params: Record<string, string | number | undefined> = {}) =>
    api.get<RankingRow[]>(`/cards/ranking?${query(params)}`),
  openPack: (packId: number) =>
    api.post<{
      opening_id: string
      pack_id: number
      coins_spent: number
      coins_left: number
      cards: UserCard[]
    }>('/cards/open-pack', { pack_id: packId }),
}

export const trades = {
  searchUsers: (q: string) => api.get<UserPublic[]>(`/trades/users?q=${encodeURIComponent(q)}`),
  userCards: (userId: string) => api.get<UserCard[]>(`/trades/users/${userId}/cards`),
  incoming: () => api.get<TradeOffer[]>('/trades/incoming?status=PENDING'),
  outgoing: () => api.get<TradeOffer[]>('/trades/outgoing?status=PENDING'),
  history: () => api.get<TradeOffer[]>('/trades/history'),
  create: (payload: {
    receiver_id: string
    sender_cards: string[]
    receiver_cards: string[]
    sender_coins?: number
    message?: string | null
  }) => api.post<TradeOffer>('/trades/offer', payload),
  accept: (id: string) => api.post<TradeOffer>(`/trades/${id}/accept`),
  decline: (id: string) => api.post<TradeOffer>(`/trades/${id}/decline`),
  cancel: (id: string) => api.post<TradeOffer>(`/trades/${id}/cancel`),
  counter: (
    id: string,
    payload: { sender_cards: string[]; receiver_cards: string[]; sender_coins?: number; message?: string | null },
  ) => api.post<TradeOffer>(`/trades/${id}/counter`, payload),
}

export const squad = {
  current: (matchId?: number | null) =>
    api.get<Squad>(`/squad/current${matchId ? `?match_id=${matchId}` : ''}`),
  select: (userCardId: string, slot: string, matchId?: number | null) =>
    api.post<Squad>('/squad/select', {
      user_card_id: userCardId,
      position_slot: slot,
      match_id: matchId ?? null,
    }),
  remove: (slot: string, matchId?: number | null) =>
    api.del<Squad>(`/squad/remove/${slot}${matchId ? `?match_id=${matchId}` : ''}`),
  captain: (entryId: string, vice = false, matchId?: number | null) =>
    api.post<Squad>('/squad/captain', { entry_id: entryId, vice, match_id: matchId ?? null }),
  validate: (matchId?: number | null) =>
    api.post<ValidationResult>(`/squad/validate${matchId ? `?match_id=${matchId}` : ''}`),
  lock: (matchId: number) => api.post<Squad>(`/squad/lock/${matchId}`),
  perfectFive: (matchId: number) => api.get<PerfectFive>(`/squad/perfect-xi/${matchId}`),
  lineups: (matchId: number) =>
    api.get<{ match_id: number; source: string | null; home: PlayerBrief[]; away: PlayerBrief[] }>(
      `/squad/lineups/${matchId}`,
    ),
}

export const matches = {
  list: (params: Record<string, string | number | undefined> = {}) =>
    api.get<Page<Match>>(`/matches?${query(params)}`),
  live: () => api.get<Match[]>('/matches/live'),
  upcoming: () => api.get<Match[]>('/matches/upcoming'),
  one: (id: number) => api.get<Match>(`/matches/${id}`),
  teams: () => api.get<TeamBrief[]>('/teams'),
  teamPlayers: (teamId: number) => api.get<PlayerBrief[]>(`/teams/${teamId}/players`),
}

export const store = {
  products: () => api.get<Product[]>('/store/products'),
  checkout: (sku: string) => api.post<Checkout>('/store/checkout', { sku }),
  confirm: (paymentId: string, outcome: 'success' | 'failure' = 'success') =>
    api.post<Payment>(`/store/payments/${paymentId}/confirm`, { outcome }),
  payments: () => api.get<Payment[]>('/store/payments'),
}

export const quests = {
  board: () => api.get<QuestBoard>('/quests'),
  start: (key: string) => api.post<QuestBoard>(`/quests/${key}/start`, {}),
  claim: (key: string) =>
    api.post<{ quest: Quest; reward: number; coins: number }>(`/quests/${key}/claim`, {}),
}

export const tournament = {
  preview: () => api.get<TournamentPreview>('/tournament/preview'),
  enter: () => api.post<TournamentEntry>('/tournament/enter', {}),
  entries: () => api.get<TournamentEntry[]>('/tournament/entries'),
  entry: (id: string) => api.get<TournamentEntry>(`/tournament/entries/${id}`),
}

export const leaderboard = {
  top: (limit = 100, offset = 0) =>
    api.get<LeaderboardRow[]>(`/leaderboard?limit=${limit}&offset=${offset}`),
  me: () =>
    api.get<{ rank: number | null; total_users: number; row: LeaderboardRow | null }>(
      '/leaderboard/me',
    ),
  history: () =>
    api.get<
      Array<{
        match_id: number
        match_slug: string
        points: number
        is_perfect_xi: boolean
        breakdown: Record<string, any>
        created_at: string
      }>
    >('/leaderboard/me/history'),
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value))
  }
  return search.toString()
}
