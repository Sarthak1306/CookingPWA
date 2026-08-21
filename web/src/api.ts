import type {
  CookResult,
  IngredientSuggestion,
  JobStatus,
  PantryItem,
  RecipeDetail,
  ShoppingItem,
  TasteProfile,
} from './types'

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

export function markOutOfStock(id: number) {
  return request<{ ok: boolean }>(`/api/pantry/${id}/out-of-stock`, { method: 'POST' })
}

export function createSuggestJob(body: { query: string; avoid: string[] }) {
  return request<{ job_id: number }>('/api/suggest', { method: 'POST', body: JSON.stringify(body) })
}

export function getJob(id: number) {
  return request<JobStatus>(`/api/jobs/${id}`)
}

export function getRecipe(id: number, servings?: number) {
  const qs = servings ? `?servings=${servings}` : ''
  return request<RecipeDetail>(`/api/recipes/${id}${qs}`)
}

export function cookRecipe(id: number) {
  return request<CookResult>(`/api/recipes/${id}/cook`, { method: 'POST' })
}

export function markRanOut(pantryItemIds: number[]) {
  return request<{ moved: { ingredient_id: number; name: string }[] }>('/api/pantry/ran-out', {
    method: 'POST',
    body: JSON.stringify({ pantry_item_ids: pantryItemIds }),
  })
}

export function addToShoppingList(ingredientId: number, addedFrom: string = 'recipe') {
  return request<{ ingredient_id: number; name: string; on_list: boolean }>('/api/shopping', {
    method: 'POST',
    body: JSON.stringify({ ingredient_id: ingredientId, added_from: addedFrom }),
  })
}

export function getShoppingList() {
  return request<ShoppingItem[]>('/api/shopping')
}

export function addShoppingItemByName(name: string) {
  return request<{ ingredient_id: number; name: string; on_list: boolean }>('/api/shopping', {
    method: 'POST',
    body: JSON.stringify({ name, added_from: 'manual' }),
  })
}

export function tickShoppingItem(id: number) {
  return request<{ ingredient_id: number; name: string; qty_label: string; pantry_item_id: number }>(
    `/api/shopping/${id}/tick`,
    { method: 'POST' },
  )
}

export function removeShoppingItem(id: number) {
  return request<{ ok: boolean }>(`/api/shopping/${id}`, { method: 'DELETE' })
}

export function rateCookLog(cookLogId: number, rating: number) {
  return request<{ ok: boolean }>(`/api/cook-log/${cookLogId}/rate`, {
    method: 'POST',
    body: JSON.stringify({ rating }),
  })
}

export function getTasteProfile() {
  return request<TasteProfile>('/api/taste-profile')
}

export function updateTasteProfile(body: { effort?: string; tags?: string[]; body_text?: string }) {
  return request<TasteProfile>('/api/taste-profile', { method: 'PATCH', body: JSON.stringify(body) })
}
