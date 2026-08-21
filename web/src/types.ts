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

export type Difficulty = 'easy' | 'intermediate' | 'advanced'

export type RecipeSummary = {
  id: number
  title: string
  cuisine: string
  est_minutes: number | null
  keeps_well: boolean
  difficulty: Difficulty
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
  pantry_item_id: number | null
  on_shopping_list: boolean
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
  difficulty: Difficulty
  base_servings: number
  servings: number
  ingredients: RecipeIngredient[]
  steps: RecipeStep[]
}

export type UsedPantryItem = {
  pantry_item_id: number
  name: string
}

export type CookResult = {
  cook_log_id: number
  recipe_id: number
  used_pantry_items: UsedPantryItem[]
}

export type TasteProfile = {
  effort: string
  tags: string[]
  body_text: string
  updated_at: string
}

export type ShoppingItem = {
  id: number
  ingredient_id: number
  name: string
  color: string
  emoji: string
  added_from: string
  added_at: string
}
