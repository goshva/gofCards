const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

let tokenGetter: () => string | null = () => null
let onUnauthorized: () => void = () => {}

export function configureClient(getToken: () => string | null, unauthorized: () => void) {
  tokenGetter = getToken
  onUnauthorized = unauthorized
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    // FastAPI validation errors arrive as a list of objects
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string }
      if (first?.msg) return first.msg
    }
  }
  return fallback
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  const token = tokenGetter()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const resp = await fetch(`${BASE}${path}`, { ...init, headers })
  if (resp.status === 401) {
    onUnauthorized()
    throw new ApiError('Требуется вход', 401)
  }
  if (!resp.ok) {
    let body: unknown = null
    try {
      body = await resp.json()
    } catch {
      /* non-json error body */
    }
    throw new ApiError(detailOf(body, `Ошибка запроса (${resp.status})`), resp.status)
  }
  if (resp.status === 204) return undefined as T
  return (await resp.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
