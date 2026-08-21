import { useState } from 'react'
import { ApiError, markRanOut } from '../api'
import type { UsedPantryItem } from '../types'
import './RanOut.css'

export default function RanOut({
  usedItems,
  onDone,
  onFlash,
}: {
  usedItems: UsedPantryItem[]
  onDone: () => void
  onFlash: (msg: string) => void
}) {
  const [checked, setChecked] = useState<Set<number>>(new Set())
  const [saving, setSaving] = useState(false)

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
