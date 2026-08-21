import type { IngredientSuggestion, PantryItem } from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // no JSON body — keep statusText
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function getMe() {
  return request<{ username: string }>('/api/me')
}

export function login(username: string, password: string) {
  return request<{ username: string }>('/api/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logout() {
  return request<{ ok: boolean }>('/api/logout', { method: 'POST' })
}

export function getPantry() {
  return request<PantryItem[]>('/api/pantry')
}

export function searchIngredients(q: string) {
  return request<IngredientSuggestion[]>(`/api/ingredients?q=${encodeURIComponent(q)}`)
}

export function addPantryItem(body: { name: string; qty_label?: string; is_low?: boolean }) {
  return request<PantryItem>('/api/pantry', { method: 'POST', body: JSON.stringify(body) })
}

export function editPantryItem(
  id: number,
  body: { name: string; qty_label?: string; is_low?: boolean },
) {
  return request<PantryItem>(`/api/pantry/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
}

export function restockPantryItem(id: number) {
  return request<PantryItem>(`/api/pantry/${id}/restock`, { method: 'POST' })
}
