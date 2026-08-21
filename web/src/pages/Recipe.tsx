import { useEffect, useMemo, useState } from 'react'
import { addToShoppingList, ApiError, getRecipe } from '../api'
import type { Difficulty, RecipeDetail, RecipeStep } from '../types'
import './Recipe.css'

const STEP_PREVIEW_COUNT = 3
const DIFFICULTY_BARS: Record<Difficulty, number> = { easy: 1, intermediate: 2, advanced: 3 }
const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  easy: 'Easy',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
}

function scaleQty(qty: string, ratio: number): string {
  const n = parseFloat(qty)
  if (Number.isNaN(n)) return qty
  const scaled = Math.round(n * ratio * 100) / 100
  const rest = qty.slice(String(n).length)
  return `${scaled}${rest}`
}

function BackIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}

function DifficultyIcon({ bars }: { bars: number }) {
  return (
    <span className="recipe__difficulty-bars">
      {[1, 2, 3].map((i) => (
        <span key={i} className={`recipe__difficulty-bar${i <= bars ? ' recipe__difficulty-bar--on' : ''}`} style={{ height: 5 + i * 4 }} />
      ))}
    </span>
  )
}

function LeafIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
      <path d="M2 21c0-3 1.85-5.36 5.08-6" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

function MinusIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
      <path d="M5 12h14" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  )
}

function ArrowRightIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h13M13 6l6 6-6 6" />
    </svg>
  )
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
  const [showAllSteps, setShowAllSteps] = useState(false)

  useEffect(() => {
    setRecipe(null)
    setError('')
    setShowAllSteps(false)
    getRecipe(recipeId)
      .then((r) => {
        setRecipe(r)
        setServings(r.base_servings)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load that recipe."))
  }, [recipeId])

  const heroColors = useMemo(() => {
    if (!recipe) return []
    const seen = new Set<string>()
    const colors: string[] = []
    for (const ing of recipe.ingredients) {
      if (!seen.has(ing.color)) {
        seen.add(ing.color)
        colors.push(ing.color)
      }
      if (colors.length === 4) break
    }
    return colors
  }, [recipe])

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

  function handleStartCook() {
    if (!recipe || recipe.steps.length === 0) return
    onStartCook(recipe.id, recipe.steps)
  }

  if (error) {
    return (
      <div className="recipe">
        <div className="recipe__bare-header">
          <button className="recipe__back" onClick={onBack} aria-label="Back">
            <BackIcon />
          </button>
        </div>
        <div className="recipe__empty">{error}</div>
      </div>
    )
  }

  if (!recipe || servings === null) {
    return (
      <div className="recipe">
        <div className="recipe__bare-header">
          <button className="recipe__back" onClick={onBack} aria-label="Back">
            <BackIcon />
          </button>
        </div>
        <div className="recipe__empty">Loading…</div>
      </div>
    )
  }

  const ratio = servings / recipe.base_servings
  const haveIngredients = recipe.ingredients.filter((i) => i.have)
  const missingIngredients = recipe.ingredients.filter((i) => !i.have)
  const timerCount = recipe.steps.filter((s) => s.timer_seconds != null).length
  const visibleSteps = showAllSteps ? recipe.steps : recipe.steps.slice(0, STEP_PREVIEW_COUNT)
  const hiddenStepCount = recipe.steps.length - visibleSteps.length

  return (
    <div className="recipe">
      <div className="recipe__hero">
        <div className="recipe__hero-blooms">
          {heroColors.map((c, i) => (
            <span key={i} className={`recipe__bloom recipe__bloom--${i}`} style={{ background: c }} />
          ))}
        </div>

        <div className="recipe__hero-top">
          <button className="recipe__back" onClick={onBack} aria-label="Back">
            <BackIcon />
          </button>
        </div>

        <div className="recipe__hero-content">
          {recipe.cuisine && <div className="recipe__cuisine">{recipe.cuisine}</div>}
          <h1 className="recipe__title">{recipe.title}</h1>

          <div className="recipe__meta-pills">
            {recipe.est_minutes != null && (
              <span className="recipe__pill">
                <ClockIcon />
                {recipe.est_minutes} min
              </span>
            )}
            <span className="recipe__pill">
              <DifficultyIcon bars={DIFFICULTY_BARS[recipe.difficulty]} />
              {DIFFICULTY_LABEL[recipe.difficulty]}
            </span>
            {recipe.keeps_well && (
              <span className="recipe__pill recipe__pill--accent-2">
                <LeafIcon />
                Keeps well
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="recipe__servings-card">
        <div className="recipe__servings-text">
          <span className="recipe__servings-title">Serves {servings}</span>
          {servings !== recipe.base_servings && (
            <span className="recipe__servings-subtitle">Scaled from {recipe.base_servings} · quantities updated</span>
          )}
        </div>
        <div className="recipe__servings-control">
          <button className="recipe__servings-btn" onClick={() => setServings((s) => Math.max(1, (s ?? 1) - 1))} aria-label="Fewer servings">
            <MinusIcon />
          </button>
          <button className="recipe__servings-btn recipe__servings-btn--primary" onClick={() => setServings((s) => Math.min(8, (s ?? 1) + 1))} aria-label="More servings">
            <PlusIcon />
          </button>
        </div>
      </div>

      <div className="recipe__scroll sc">
        <div className="recipe__section-header">
          <h2 className="recipe__section-title">Ingredients</h2>
          <span className="recipe__section-count">{recipe.ingredients.length} items</span>
        </div>

        {missingIngredients.length > 0 && (
          <>
            <div className="recipe__group-label recipe__group-label--accent">
              <span>To buy</span>
              <span className="recipe__group-badge recipe__group-badge--accent">{missingIngredients.length}</span>
              <span className="recipe__group-rule" />
            </div>
            <div className="recipe__ingredient-list">
              {missingIngredients.map((ing) => (
                <div className="recipe__ingredient recipe__ingredient--buy" key={ing.ingredient_id}>
                  <span className="recipe__swatch" style={{ background: `color-mix(in srgb, ${ing.color} 55%, transparent)` }}>
                    {ing.emoji}
                  </span>
                  <span className="recipe__ingredient-text">
                    <span className="recipe__ingredient-name-row">
                      <span className="recipe__ingredient-name">{ing.name}</span>
                      {ing.optional && <span className="recipe__optional-tag">Optional</span>}
                    </span>
                    {ing.qty && <span className="recipe__ingredient-qty">{scaleQty(ing.qty, ratio)} {ing.unit}</span>}
                  </span>
                  <button
                    className="recipe__list-btn"
                    disabled={ing.on_shopping_list || addingIds.has(ing.ingredient_id)}
                    onClick={() => handleAdd(ing.ingredient_id)}
                  >
                    {ing.on_shopping_list ? 'On list' : <><PlusIcon />List</>}
                  </button>
                </div>
              ))}
            </div>
          </>
        )}

        {haveIngredients.length > 0 && (
          <>
            <div className="recipe__group-label recipe__group-label--accent-2">
              <span>In your pantry</span>
              <span className="recipe__group-badge recipe__group-badge--accent-2">{haveIngredients.length}</span>
              <span className="recipe__group-rule" />
            </div>
            <div className="recipe__ingredient-list">
              {haveIngredients.map((ing) => (
                <div className="recipe__ingredient recipe__ingredient--have" key={ing.ingredient_id}>
                  <span className="recipe__swatch" style={{ background: `color-mix(in srgb, ${ing.color} 55%, transparent)` }}>
                    {ing.emoji}
                  </span>
                  <span className="recipe__ingredient-text">
                    <span className="recipe__ingredient-name">{ing.name}</span>
                    {ing.qty && <span className="recipe__ingredient-qty">{scaleQty(ing.qty, ratio)} {ing.unit}</span>}
                  </span>
                  <span className="recipe__have-check">
                    <CheckIcon />
                  </span>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="recipe__section-header">
          <h2 className="recipe__section-title">Method</h2>
          <span className="recipe__section-count">
            {recipe.steps.length} steps{timerCount > 0 && ` · ${timerCount} timer${timerCount === 1 ? '' : 's'}`}
          </span>
        </div>
        <div className="recipe__steps">
          {visibleSteps.map((s, i) => (
            <div className="recipe__step" key={s.position}>
              <span className="recipe__step-rail">
                <span className="recipe__step-n">{i + 1}</span>
                {i < visibleSteps.length - 1 || hiddenStepCount > 0 ? <span className="recipe__step-line" /> : null}
              </span>
              <span className="recipe__step-body">
                <span className="recipe__step-text">{s.text}</span>
                {s.timer_seconds != null && (
                  <span className="recipe__step-timer">
                    <ClockIcon />
                    {Math.round(s.timer_seconds / 60)} min
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
        {hiddenStepCount > 0 && (
          <button className="recipe__more-steps" onClick={() => setShowAllSteps(true)}>
            Show all {recipe.steps.length} steps
          </button>
        )}
      </div>

      <div className="recipe__footer">
        <button className="recipe__start-cook" onClick={handleStartCook} disabled={recipe.steps.length === 0}>
          Start cooking
          <ArrowRightIcon />
        </button>
      </div>
    </div>
  )
}
