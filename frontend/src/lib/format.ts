/* Regional-indicator flag emoji do not render on Windows at all — they come out
   as a pair of letters. A plain ISO code reads the same on every platform. */
const CODES: Record<string, string> = {
  Argentina: 'ARG',
  Brazil: 'BRA',
  Cyprus: 'CYP',
  Egypt: 'EGY',
  Guatemala: 'GTM',
  Italy: 'ITA',
  Kazakhstan: 'KAZ',
  Mexico: 'MEX',
  Montenegro: 'MNE',
  Russia: 'RUS',
  'Saudi Arabia': 'SAU',
  'South Africa': 'RSA',
  Spain: 'ESP',
  'United States of America': 'USA',
  Uruguay: 'URU',
  Uzbekistan: 'UZB',
}

export function countryCode(country: string | null | undefined): string {
  if (!country) return '—'
  return CODES[country] ?? country.slice(0, 3).toUpperCase()
}

export const RARITY_LABELS: Record<string, string> = {
  COMMON: 'Обычная',
  RARE: 'Редкая',
  EPIC: 'Эпическая',
  LEGENDARY: 'Легендарная',
}

export const ATTRIBUTE_ORDER = ['atk', 'def', 'dig', 'phy', 'clt', 'exp'] as const

export const ATTRIBUTE_LABELS: Record<string, string> = {
  atk: 'АТК',
  def: 'ЗАЩ',
  dig: 'ЦИФ',
  phy: 'ФИЗ',
  clt: 'ХЛД',
  exp: 'ОПЫ',
}

export const ATTRIBUTE_TITLES: Record<string, string> = {
  atk: 'Атака — голы команды за матч',
  def: 'Защита — пропущенные за матч',
  dig: 'Цифровая часть — разница мячей',
  phy: 'Физическая часть — разница мячей',
  clt: 'Хладнокровие — пенальти и глубина плей-офф',
  exp: 'Опыт — возраст и путь команды по сетке',
}

/** Monogram used in place of the team badge: GoFuture ships none. */
export function monogram(title: string | null | undefined): string {
  if (!title) return '—'
  const words = title.replace(/[^\p{L}\p{N} ]/gu, ' ').split(/\s+/).filter(Boolean)
  if (!words.length) return '—'
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
}

export function positionLabel(position: string | null | undefined): string {
  if (position === 'GOALKEEPER') return 'GK'
  if (position === 'FIELD') return 'FLD'
  return '—'
}

const ROUNDS: Record<number, string> = {
  6: 'финал',
  5: 'матч за 3-е место',
  4: 'полуфинал',
  3: 'четвертьфинал',
  2: 'плей-офф',
  1: 'групповой этап',
}
export function roundLabel(depth: number): string {
  return ROUNDS[depth] ?? '—'
}
