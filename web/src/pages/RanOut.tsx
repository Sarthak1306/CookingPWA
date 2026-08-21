import { useState } from 'react'
import { ApiError, markRanOut, rateCookLog } from '../api'
import type { UsedPantryItem } from '../types'
import './RanOut.css'

const RATING_VALUES = [1, 2, 3, 4, 5]

export default function RanOut({
  usedItems,
  cookLogId,
  onDone,
  onFlash,
}: {
  usedItems: UsedPantryItem[]
  cookLogId: number
  onDone: () => void
  onFlash: (msg: string) => void
}) {
  const [checked, setChecked] = useState<Set<number>>(new Set())
  const [saving, setSaving] = useState(false)
  const [rating, setRating] = useState<number | null>(null)

  async function rate(value: number) {
    setRating(value)
    try {
      await rateCookLog(cookLogId, value)
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't save that rating.")
    }
  }

  function toggle(id: number) {
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function confirm() {
    if (saving) return
    setSaving(true)
    try {
      if (checked.size > 0) {
        await markRanOut([...checked])
        onFlash(`${checked.size} moved to shopping list`)
      }
      onDone()
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't update the pantry.")
      setSaving(false)
    }
  }

  function skip() {
    if (saving) return
    onDone()
  }

  return (
    <div className="ran-out">
      <div className="ran-out__header">
        <div className="ran-out__title">Anything run out?</div>
        <div className="ran-out__subtitle">Tap what's finished. Usually nothing.</div>
      </div>

      <div className="ran-out__scroll sc">
        <div className="ran-out__rating">
          <div className="ran-out__rating-label">How was it?</div>
          <div className="ran-out__rating-row">
            {RATING_VALUES.map((value) => (
              <button
                key={value}
                className={`ran-out__rating-btn${rating !== null && value <= rating ? ' ran-out__rating-btn--active' : ''}`}
                onClick={() => rate(value)}
                aria-label={`Rate ${value} out of 5`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>

        {usedItems.length === 0 && (
          <div className="ran-out__empty">Nothing in this recipe was in your pantry to begin with.</div>
        )}
        {usedItems.map((item) => {
          const isChecked = checked.has(item.pantry_item_id)
          return (
            <button
              key={item.pantry_item_id}
              className="ran-out__item"
              onClick={() => toggle(item.pantry_item_id)}
            >
              {isChecked ? (
                <span className="ran-out__check ran-out__check--checked">✓</span>
              ) : (
                <span className="ran-out__check" />
              )}
              <span className="ran-out__item-name">{item.name}</span>
            </button>
          )
        })}
      </div>

      <div className="ran-out__footer">
        <button className="ran-out__confirm" onClick={confirm} disabled={saving}>
          {checked.size > 0 ? `Move ${checked.size} to shopping list` : 'Done'}
        </button>
        <button className="ran-out__skip" onClick={skip} disabled={saving}>
          Nothing ran out
        </button>
      </div>
    </div>
  )
}
