import { useEffect, useRef, useState } from 'react'
import {
  addShoppingItemByName,
  ApiError,
  getShoppingList,
  removeShoppingItem,
  searchIngredients,
  tickShoppingItem,
} from '../api'
import type { IngredientSuggestion, ShoppingItem } from '../types'
import './Shopping.css'

export default function Shopping({
  onFlash,
  onTicked,
}: {
  onFlash: (msg: string) => void
  onTicked: () => void
}) {
  const [items, setItems] = useState<ShoppingItem[] | null>(null)
  const [error, setError] = useState('')
  const [adding, setAdding] = useState(false)
  const [typed, setTyped] = useState('')
  const [suggestions, setSuggestions] = useState<IngredientSuggestion[]>([])
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set())
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function reload() {
    setError('')
    getShoppingList()
      .then(setItems)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load your shopping list."))
  }

  useEffect(reload, [])

  useEffect(() => {
    const t = typed.trim()
    if (!t) {
      setSuggestions([])
      return
    }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      searchIngredients(t)
        .then(setSuggestions)
        .catch(() => setSuggestions([]))
    }, 200)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [typed])

  async function addByName(name: string) {
    const trimmed = name.trim()
    if (!trimmed) return
    setAdding(false)
    setTyped('')
    setSuggestions([])
    try {
      await addShoppingItemByName(trimmed)
      reload()
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't add that.")
    }
  }

  async function handleTick(item: ShoppingItem) {
    if (busyIds.has(item.id)) return
    setBusyIds((s) => new Set(s).add(item.id))
    try {
      await tickShoppingItem(item.id)
      setItems((prev) => prev?.filter((i) => i.id !== item.id) ?? null)
      onFlash(`${item.name} back in the pantry`)
      onTicked()
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't update that.")
      setBusyIds((s) => {
        const next = new Set(s)
        next.delete(item.id)
        return next
      })
    }
  }

  async function handleRemove(item: ShoppingItem) {
    if (busyIds.has(item.id)) return
    setBusyIds((s) => new Set(s).add(item.id))
    try {
      await removeShoppingItem(item.id)
      setItems((prev) => prev?.filter((i) => i.id !== item.id) ?? null)
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't remove that.")
      setBusyIds((s) => {
        const next = new Set(s)
        next.delete(item.id)
        return next
      })
    }
  }

  return (
    <div className="shopping">
      <div className="shopping__header">
        <div className="shopping__title-row">
          <div className="shopping__title">Shopping</div>
          {!adding && (
            <button className="shopping__add" onClick={() => setAdding(true)} aria-label="Add item">
              +
            </button>
          )}
        </div>
        {adding && (
          <div className="shopping__add-row">
            <input
              className="shopping__add-input"
              placeholder="Add an item"
              value={typed}
              autoFocus
              onChange={(e) => setTyped(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && typed.trim()) addByName(typed)
                if (e.key === 'Escape') {
                  setAdding(false)
                  setTyped('')
                }
              }}
            />
            {suggestions.length > 0 && (
              <div className="shopping__suggestions">
                {suggestions.map((s) => (
                  <button key={s.id} className="shopping__suggestion" onClick={() => addByName(s.name)}>
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="shopping__scroll sc">
        {error && <div className="shopping__empty">{error}</div>}

        {!error && items === null && <div className="shopping__empty">Loading…</div>}

        {!error && items !== null && items.length === 0 && (
          <div className="shopping__empty">Nothing on your list.</div>
        )}

        {!error && items !== null && items.length > 0 && (
          <div className="shopping__items">
            {items.map((item) => (
              <div className="shopping__row" key={item.id}>
                <button
                  className="shopping__item"
                  style={{ background: item.color }}
                  onClick={() => handleTick(item)}
                  disabled={busyIds.has(item.id)}
                >
                  {item.emoji && <span className="shopping__item-emoji">{item.emoji}</span>}
                  <span className="shopping__item-name">{item.name}</span>
                </button>
                <button
                  className="shopping__remove"
                  onClick={() => handleRemove(item)}
                  disabled={busyIds.has(item.id)}
                  aria-label={`Remove ${item.name}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
