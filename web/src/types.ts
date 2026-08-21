export type PantryItem = {
  id: number
  ingredient_id: number
  name: string
  category: string
  qty_label: string
  is_low: boolean
  pack: string
  color: string
  emoji: string
  updated_at: string
}

export type IngredientSuggestion = {
  id: number
  name: string
  category: string
  pack: string
  color: string
  emoji: string
}

export type RecipeSummary = {
  id: number
  title: string
  cuisine: string
  est_minutes: number | null
  keeps_well: boolean
  have_count: number
  missing_count: number
}

export type JobStatus = {
  id: number
  status: 'pending' | 'running' | 'done' | 'error'
  error: string | null
  recipes: RecipeSummary[] | null
}

export type RecipeIngredient = {
  ingredient_id: number
  name: string
  color: string
  emoji: string
  qty: string
  unit: string
  optional: boolean
  have: boolean
}

export type RecipeStep = {
  position: number
  text: string
  timer_seconds: number | null
}

export type RecipeDetail = {
  id: number
  title: string
  cuisine: string
  est_minutes: number | null
  keeps_well: boolean
  base_servings: number
  servings: number
  ingredients: RecipeIngredient[]
  steps: RecipeStep[]
}
