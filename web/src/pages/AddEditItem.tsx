import { useEffect, useRef, useState } from 'react'
import { addPantryItem, ApiError, editPantryItem, searchIngredients } from '../api'
import type { IngredientSuggestion, PantryItem } from '../types'
import './AddEditItem.css'

export default function AddEditItem({
  item,
  onBack,
  onSaved,
  onFlash,
}: {
  item: PantryItem | null
  onBack: () => void
  onSaved: (item: PantryItem) => void
  onFlash: (msg: string) => void
}) {
  const isEdit = item !== null
  const [name, setName] = useState(item?.name ?? '')
  const [qty, setQty] = useState(item?.qty_label ?? '')
  const [low, setLow] = useState(item?.is_low ?? false)
  const [suggestions, setSuggestions] = useState<IngredientSuggestion[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const typed = name.trim()
    if (!typed) {
      setSuggestions([])
      return
    }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      searchIngredients(typed)
        .then((results) => {
          const exact = results.some((r) => r.name.toLowerCase() === typed.toLowerCase())
          setSuggestions(exact ? [] : results)
        })
        .catch(() => setSuggestions([]))
    }, 200)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [name])

  function pickSuggestion(s: IngredientSuggestion) {
    setName(s.name)
    setQty(s.pack)
    setSuggestions([])
  }

  const packPreset = suggestions.find((s) => s.name.toLowerCase() === name.trim().toLowerCase())?.pack
  const presets = [packPreset, 'half full', 'nearly gone', 'a few left'].filter(
    (p, i, arr): p is string => !!p && arr.indexOf(p) === i,
  )

  async function handleSave() {
    const trimmed = name.trim()
    if (!trimmed || saving) return
    setSaving(true)
    setError('')
    try {
      const saved = isEdit
        ? await editPantryItem(item.id, { name: trimmed, qty_label: qty.trim(), is_low: low })
        : await addPantryItem({ name: trimmed, qty_label: qty.trim(), is_low: low })
      onFlash(isEdit ? 'Saved' : `${saved.name} added`)
      onSaved(saved)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="add-item">
      <div className="add-item__header">
        <button className="add-item__back" onClick={onBack} aria-label="Back">
          ‹
        </button>
        <div className="add-item__title">{isEdit ? 'Edit item' : 'Add item'}</div>
      </div>

      <div className="add-item__body sc">
        <div>
          <label className="add-item__label">Ingredient</label>
          <input
            className="add-item__input"
            placeholder="Start typing"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus={!isEdit}
          />
          {suggestions.length > 0 && (
            <div className="add-item__suggestions">
              {suggestions.map((s) => (
                <button key={s.id} className="add-item__suggestion" onClick={() => pickSuggestion(s)}>
                  <span>{s.name}</span>
                  <span className="add-item__suggestion-pack">{s.pack}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="add-item__label">Quantity label — your words, never counted</label>
          <input
            className="add-item__input"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
          />
          {presets.length > 0 && (
            <div className="add-item__presets sc">
              {presets.map((p) => (
                <button key={p} className="add-item__preset" onClick={() => setQty(p)}>
                  {p}
                </button>
              ))}
            </div>
          )}
        </div>

        <button className="add-item__low-toggle" onClick={() => setLow((v) => !v)}>
          <span className="add-item__low-label">Running low</span>
          <span className={`add-item__switch${low ? ' add-item__switch--on' : ''}`}>
            <span className="add-item__switch-knob" />
          </span>
        </button>

        {error && <div className="add-item__error">{error}</div>}

        <button className="add-item__save" onClick={handleSave} disabled={saving || !name.trim()}>
          {saving ? 'Saving…' : isEdit ? 'Save' : 'Add to pantry'}
        </button>
      </div>
    </div>
  )
}
