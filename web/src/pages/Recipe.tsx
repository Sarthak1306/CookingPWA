import { useEffect, useState } from 'react'
import { addToShoppingList, ApiError, getRecipe } from '../api'
import type { RecipeDetail, RecipeStep } from '../types'
import './Recipe.css'

const STEP_PREVIEW_COUNT = 3

function scaleQty(qty: string, ratio: number): string {
  const n = parseFloat(qty)
  if (Number.isNaN(n)) return qty
  const scaled = Math.round(n * ratio * 100) / 100
  const rest = qty.slice(String(n).length)
  return `${scaled}${rest}`
}

export default function Recipe({
  recipeId,
  onBack,
  onStartCook,
  onFlash,
}: {
  recipeId: number
  onBack: () => void
  onStartCook: (recipeId: number, steps: RecipeStep[]) => void
  onFlash: (msg: string) => void
}) {
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null)
  const [error, setError] = useState('')
  const [servings, setServings] = useState<number | null>(null)
  const [addingIds, setAddingIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    setRecipe(null)
    setError('')
    getRecipe(recipeId)
      .then((r) => {
        setRecipe(r)
        setServings(r.base_servings)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load that recipe."))
  }, [recipeId])

  async function handleAdd(ingredientId: number) {
    if (addingIds.has(ingredientId)) return
    setAddingIds((s) => new Set(s).add(ingredientId))
    try {
      await addToShoppingList(ingredientId)
      setRecipe((r) =>
        r
          ? {
              ...r,
              ingredients: r.ingredients.map((i) =>
                i.ingredient_id === ingredientId ? { ...i, on_shopping_list: true } : i,
              ),
            }
          : r,
      )
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't add that.")
    } finally {
      setAddingIds((s) => {
        const next = new Set(s)
        next.delete(ingredientId)
        return next
      })
    }
  }

  async function handleAddAll() {
    if (!recipe) return
    const missing = recipe.ingredients.filter((i) => !i.have && !i.on_shopping_list)
    await Promise.all(missing.map((i) => handleAdd(i.ingredient_id)))
    onFlash('Added to shopping list')
  }

  function handleStartCook() {
    if (!recipe || recipe.steps.length === 0) return
    onStartCook(recipe.id, recipe.steps)
  }

  if (error) {
    return (
      <div className="recipe">
        <div className="recipe__header">
          <button className="recipe__back" onClick={onBack} aria-label="Back">
            ‹
          </button>
        </div>
        <div className="recipe__empty">{error}</div>
      </div>
    )
  }

  if (!recipe || servings === null) {
    return (
      <div className="recipe">
        <div className="recipe__header">
          <button className="recipe__back" onClick={onBack} aria-label="Back">
            ‹
          </button>
        </div>
        <div className="recipe__empty">Loading…</div>
      </div>
    )
  }

  const ratio = servings / recipe.base_servings
  const missingToAdd = recipe.ingredients.filter((i) => !i.have && !i.on_shopping_list)
  const previewSteps = recipe.steps.slice(0, STEP_PREVIEW_COUNT)
  const moreSteps = recipe.steps.length - previewSteps.length

  return (
    <div className="recipe">
      <div className="recipe__header">
        <button className="recipe__back" onClick={onBack} aria-label="Back">
          ‹
        </button>
      </div>
      <div className="recipe__scroll sc">
        <div className="recipe__title">{recipe.title}</div>
        <div className="recipe__meta">
          {recipe.est_minutes != null && `${recipe.est_minutes} min · `}
          {servings} servings · <span className="recipe__difficulty">{recipe.difficulty}</span>
        </div>

        <div className="recipe__servings-row">
          <span className="recipe__servings-label">Servings</span>
          <div className="recipe__servings-control">
            <button
              className="recipe__servings-btn"
              onClick={() => setServings((s) => Math.max(1, (s ?? 1) - 1))}
            >
              −
            </button>
            <span className="recipe__servings-value">{servings}</span>
            <button
              className="recipe__servings-btn"
              onClick={() => setServings((s) => Math.min(8, (s ?? 1) + 1))}
            >
              +
            </button>
          </div>
        </div>

        <div className="recipe__section-label">Ingredients</div>
        <div className="recipe__ingredients">
          {recipe.ingredients.map((ing) => (
            <div className="recipe__ingredient" key={ing.ingredient_id}>
              {ing.have ? (
                <span className="recipe__check recipe__check--have">✓</span>
              ) : (
                <span className="recipe__check recipe__check--missing" />
              )}
              <span className="recipe__ingredient-name">{ing.name}</span>
              <span className="recipe__ingredient-qty">
                {scaleQty(ing.qty, ratio)} {ing.unit}
              </span>
              {!ing.have && (
                <button
                  className="recipe__add-missing"
                  disabled={ing.on_shopping_list || addingIds.has(ing.ingredient_id)}
                  onClick={() => handleAdd(ing.ingredient_id)}
                >
                  {ing.on_shopping_list ? 'On list' : 'Add'}
                </button>
              )}
            </div>
          ))}
        </div>
        {missingToAdd.length > 0 && (
          <button className="recipe__add-all" onClick={handleAddAll}>
            Add all {missingToAdd.length} missing to shopping list
          </button>
        )}

        <div className="recipe__section-label">Steps</div>
        <div className="recipe__steps">
          {previewSteps.map((s) => (
            <div className="recipe__step" key={s.position}>
              <span className="recipe__step-n">{s.position + 1}</span>
              <span className="recipe__step-text">{s.text}</span>
            </div>
          ))}
        </div>
        {moreSteps > 0 && <div className="recipe__more-steps">+ {moreSteps} more steps</div>}
      </div>
      <div className="recipe__footer">
        <button className="recipe__start-cook" onClick={handleStartCook} disabled={recipe.steps.length === 0}>
          Start cooking
        </button>
      </div>
    </div>
  )
}
