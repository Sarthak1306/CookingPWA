import { useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, getPantry, restockPantryItem } from '../api'
import type { PantryItem } from '../types'
import './Pantry.css'

export const CATEGORIES = ['Produce', 'Dairy', 'Grains', 'Spices', 'Proteins', 'Other']

export default function Pantry({
  onOpenAdd,
  onOpenEdit,
  onFlash,
}: {
  onOpenAdd: () => void
  onOpenEdit: (item: PantryItem) => void
  onFlash: (msg: string) => void
}) {
  const [items, setItems] = useState<PantryItem[] | null>(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  function reload() {
    setError('')
    getPantry()
      .then(setItems)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not load your pantry.'))
  }

  useEffect(reload, [])

  const q = query.trim().toLowerCase()
  const groups = useMemo(() => {
    if (!items) return []
    return CATEGORIES.map((cat) => ({
      label: cat,
      items: items.filter(
        (i) => i.category === cat && (!q || i.name.toLowerCase().includes(q)),
      ),
    })).filter((g) => g.items.length > 0)
  }, [items, q])

  const chips = useMemo(() => {
    if (!items) return []
    const present = new Set(items.map((i) => i.category))
    return CATEGORIES.filter((c) => present.has(c))
  }, [items])

  function jumpTo(cat: string) {
    const el = scrollRef.current?.querySelector<HTMLElement>(`#cat-${cat}`)
    if (el && scrollRef.current) scrollRef.current.scrollTop = el.offsetTop - 4
  }

  async function handleRestock(item: PantryItem) {
    try {
      const updated = await restockPantryItem(item.id)
      setItems((prev) => prev?.map((i) => (i.id === updated.id ? updated : i)) ?? null)
      onFlash(`Restocked ${updated.name} — ${updated.pack || 'pack'}`)
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't restock that.")
    }
  }

  return (
    <div className="pantry">
      <div className="pantry__header">
        <div className="pantry__title-row">
          <div className="pantry__title">Pantry</div>
          <button className="pantry__add" onClick={onOpenAdd} aria-label="Add item">
            +
          </button>
        </div>
        <input
          className="pantry__search"
          placeholder="Search pantry"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {chips.length > 1 && (
          <div className="pantry__chips sc">
            {chips.map((cat) => (
              <button key={cat} className="pantry__chip" onClick={() => jumpTo(cat)}>
                {cat}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="pantry__scroll sc" ref={scrollRef}>
        {error && <div className="pantry__empty">{error}</div>}

        {!error && items === null && <div className="pantry__empty">Loading…</div>}

        {!error &&
          items !== null &&
          groups.map((group) => (
            <div key={group.label} id={`cat-${group.label}`}>
              <div className="pantry__group-label">{group.label}</div>
              <div className="pantry__group-items">
                {group.items.map((item) => (
                  <div className="pantry__row" key={item.id}>
                    <button
                      className="pantry__item"
                      style={{ background: item.color }}
                      onClick={() => onOpenEdit(item)}
                    >
                      {item.emoji && <span className="pantry__item-emoji">{item.emoji}</span>}
                      <div className="pantry__item-text">
                        <div className="pantry__item-name">{item.name}</div>
                        <div className="pantry__item-qty">{item.qty_label || 'no label yet'}</div>
                      </div>
                      {item.is_low && <span className="pantry__low-badge">Low</span>}
                    </button>
                    <button
                      className="pantry__restock"
                      onClick={() => handleRestock(item)}
                      aria-label={`Restock ${item.name}`}
                    >
                      <span className="pantry__restock-plus">Restock</span>
                      <span className="pantry__restock-pack">{item.pack || 'pack'}</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}

        {!error && items !== null && groups.length === 0 && (
          <div className="pantry__empty">
            {items.length === 0 ? (
              <>Nothing here yet. Tap + to add your first item.</>
            ) : (
              <>Nothing matching “{query}”.</>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
