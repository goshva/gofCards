export type Rarity = 'COMMON' | 'RARE' | 'EPIC' | 'LEGENDARY'
export type CardType = 'PLAYER' | 'TEAM'
export type Position = 'GOALKEEPER' | 'FIELD'
export type PositionSlot = 'GK' | 'F1' | 'F2' | 'F3' | 'F4' | 'SUB1' | 'SUB2'
export type MatchStatus = 'SCHEDULED' | 'LIVE' | 'COMPLETED' | 'CANCELLED'
export type TradeStatus = 'PENDING' | 'ACCEPTED' | 'DECLINED' | 'CANCELLED' | 'COUNTERED'

export type AttributeKey = 'atk' | 'def' | 'dig' | 'phy' | 'clt' | 'exp'
export type Attributes = Partial<Record<AttributeKey, number>>

export interface TeamBrief {
  id: number
  slug: string
  title: string
  short_title: string | null
  country: string | null
  image_url: string | null
  photo_path: string | null
  logo_url: string | null
  color: string | null
  ovr: number
  rank: number | null
}

export interface PlayerBrief {
  id: number
  slug: string
  nickname: string
  first_name: string | null
  last_name: string | null
  country: string | null
  position: Position
  jersey_number: number | null
  date_of_birth: string | null
  image_url: string | null
  photo_path: string | null
  photo_url: string | null
  age: number | null
  team: TeamBrief | null
  ovr: number
  rank: number | null
  attributes: Attributes
  matches_played: number
  wins: number
  draws: number
  losses: number
  goals_for: number
  goals_against: number
  best_round: number
}

export interface CardTemplate {
  id: number
  card_type: CardType
  rarity: Rarity
  base_price: number
  image_url: string | null
  name: string
  subtitle: string | null
  position: Position | null
  ovr: number
  rank: number | null
  attributes: Attributes
  player: PlayerBrief | null
  team: TeamBrief | null
}

export interface UserCard {
  id: string
  card_type: CardType
  card_template_id: number
  acquired_at: string
  source: string
  locked_by_trade: boolean
  in_squad: boolean
  is_permanent: boolean
  tournaments_used: number
  runs_left: number | null
  template: CardTemplate
}

export interface Pack {
  id: number
  name: string
  description: string | null
  price: number
  contents_json: Record<string, number>
  team_card_chance: number
  grants_permanent: boolean
  guarantees_goalkeeper: boolean
}

export interface User {
  id: string
  username: string
  email: string
  role: 'USER' | 'ADMIN'
  referral_code: string | null
  coins: number
  total_points: number
  created_at: string
}

export interface UserPublic {
  id: string
  username: string
  total_points: number
}

export interface TradeOffer {
  id: string
  status: TradeStatus
  sender: UserPublic
  receiver: UserPublic
  sender_cards: UserCard[]
  receiver_cards: UserCard[]
  sender_coins: number
  message: string | null
  counter_of_id: string | null
  created_at: string
  updated_at: string
}

export interface SquadEntry {
  id: string
  position_slot: PositionSlot
  is_captain: boolean
  is_vice_captain: boolean
  player: PlayerBrief
  card: UserCard
}

export interface Squad {
  match_id: number | null
  locked: boolean
  entries: SquadEntry[]
  filled_slots: number
  required_slots: number
}

export interface ValidationIssue {
  code: string
  message: string
}

export interface ValidationResult {
  valid: boolean
  message: string
  issues: ValidationIssue[]
  is_perfect_five: boolean
  perfect_five_team: string | null
}

export interface PerfectFive {
  match_id: number
  available: boolean
  message: string
  is_perfect: boolean
  matched_team: string | null
  home_matches: number[]
  away_matches: number[]
  user_player_ids: number[]
}

export interface Match {
  id: number
  slug: string
  external_id: string
  tournament_slug: string
  round: number | null
  round_label: string | null
  venue: string | null
  status: MatchStatus
  start_time: string | null
  home_team: TeamBrief | null
  away_team: TeamBrief | null
  home_score: number
  away_score: number
  home_digital: number
  away_digital: number
  home_physical: number
  away_physical: number
  home_shootouts: number
  away_shootouts: number
  winner_team_id: number | null
  has_lineups: boolean
  lineups_source: string | null
  points_calculated: boolean
}

export interface LeaderboardRow {
  rank: number
  user_id: string
  username: string
  total_points: number
  cards_owned: number
  perfect_fives: number
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface CollectionStats {
  total_cards: number
  unique_templates: number
  by_rarity: Record<Rarity, number>
  player_cards: number
  team_cards: number
  templates_total: number
  best_ovr: number
  average_ovr: number
}

export interface RankingRow {
  rank: number
  ovr: number
  player: PlayerBrief
  rarities: Rarity[]
  owned: number
}

export interface RetiredCard {
  nickname: string | null
  ovr: number | null
  slot: string | null
}

export interface TournamentSquadSlot {
  user_card_id: string | null
  is_permanent: boolean
  runs_left: number | null
  slot: string
  player_id: number
  nickname: string
  team: string | null
  rarity: Rarity | null
  ovr: number
  is_captain: boolean
}

export interface ReplacedTeam {
  id: number
  title: string
  ovr: number
  rank: number | null
  record: string
}

export interface TournamentPreview {
  tournament_slug: string
  entry_fee: number
  cooldown_seconds: number
  squad_ovr: number
  squad: TournamentSquadSlot[]
  replaced_team: ReplacedTeam
  first_match: {
    label: string
    opponent: string
    opponent_ovr: number
    win_chance: number | null
  } | null
  coins_per_stage: number
  points_per_stage: number
}

export interface RunSide {
  name: string
  ovr: number
  is_user: boolean
}

export interface RunMatch {
  match_id: number
  label: string
  stage: string
  source: 'real' | 'simulated'
  home: RunSide
  away: RunSide
  home_score: number
  away_score: number
  digital: number[]
  physical: number[]
  shootout: number[] | null
  winner: string
  user_involved: boolean
  user_won: boolean
  user_win_chance: number | null
}

export interface TournamentEntry {
  id: string
  tournament_slug: string
  seed: string
  squad_ovr: number
  squad: TournamentSquadSlot[]
  replaced_team: ReplacedTeam | null
  stage: string
  stage_label: string
  stage_index: number
  played: number
  wins: number
  losses: number
  entry_fee: number
  coins_awarded: number
  points_awarded: number
  coins_net: number
  retired: RetiredCard[]
  my_matches: RunMatch[]
  full_run: RunMatch[]
  created_at: string
}

export type PaymentStatus = 'PENDING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED'

export interface Product {
  sku: string
  title: string
  subtitle: string | null
  price: number
  currency: string
  provider: string
  packId?: number | null
  quantity?: number | null
  coins?: number | null
}

export interface Payment {
  id: string
  sku: string
  title: string
  amount: number
  currency: string
  provider: string
  status: PaymentStatus
  reference: string
  failure_reason: string | null
  delivered: { coins: number; cards: Array<{ id: string; is_permanent: boolean }> } | null
  created_at: string
  completed_at: string | null
}

export interface Checkout {
  payment: Payment
  test_card: { number: string; expiry: string; cvc: string }
  sandbox: boolean
  notice: string
}

export type QuestStatus = 'available' | 'cooldown' | 'done' | 'action_required' | 'referral'

export interface Quest {
  key: string
  title: string
  description: string
  reward: number
  icon: string | null
  url: string | null
  repeatable: boolean
  referral: boolean
  status: QuestStatus
  times_claimed: number
  coins_earned: number
  cooldown_seconds: number
  started: boolean
}

export interface QuestBoard {
  quests: Quest[]
  referral_code: string
  referral_reward: number
  referral_friend_bonus: number
  friends_invited: number
  total_earned: number
}
