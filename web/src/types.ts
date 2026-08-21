export type PantryItem = {
  id: number
  ingredient_id: number
  name: string
  category: string
  qty_label: string
  is_low: boolean
  pack: string
  updated_at: string
}

export type IngredientSuggestion = {
  id: number
  name: string
  category: string
  pack: string
}
