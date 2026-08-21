import { useEffect, useRef, useState } from 'react'
import { ApiError, createSuggestJob, getJob, searchIngredients } from '../api'
import type { IngredientSuggestion, RecipeSummary } from '../types'
import './Suggest.css'

type Status = 'idle' | 'loading' | 'error' | 'results'

export default function Suggest({ onOpenRecipe }: { onOpenRecipe: (id: number) => void }) {
  const [query, setQuery] = useState('')
  const [avoid, setAvoid] = useState<string[]>([])
  const [addingAvoid, setAddingAvoid] = useState(false)
  const [avoidTyped, setAvoidTyped] = useState('')
  const [avoidSuggestions, setAvoidSuggestions] = useState<IngredientSuggestion[]>([])
  const [status, setStatus] = useState<Status>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [results, setResults] = useState<RecipeSummary[]>([])
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  useEffect(() => {
    const typed = avoidTyped.trim()
    if (!typed) {
      setAvoidSuggestions([])
      return
    }
    const t = setTimeout(() => {
      searchIngredients(typed)
        .then(setAvoidSuggestions)
        .catch(() => setAvoidSuggestions([]))
    }, 200)
    return () => clearTimeout(t)
  }, [avoidTyped])

  function addAvoid(name: string) {
    if (!avoid.includes(name)) setAvoid((a) => [...a, name])
    setAddingAvoid(false)
    setAvoidTyped('')
    setAvoidSuggestions([])
  }

  function removeAvoid(name: string) {
    setAvoid((a) => a.filter((x) => x !== name))
  }

  async function runSuggest() {
    if (pollRef.current) clearInterval(pollRef.current)
    setStatus('loading')
    setErrorMsg('')
    setResults([])
    try {
      const { job_id } = await createSuggestJob({ query, avoid })
      pollRef.current = setInterval(async () => {
        try {
          const job = await getJob(job_id)
          if (job.status === 'done') {
            if (pollRef.current) clearInterval(pollRef.current)
            setResults(job.recipes ?? [])
            setStatus('results')
          } else if (job.status === 'error') {
            if (pollRef.current) clearInterval(pollRef.current)
            setErrorMsg(job.error || 'Something went wrong.')
            setStatus('error')
          }
        } catch (err) {
          if (pollRef.current) clearInterval(pollRef.current)
          setErrorMsg(err instanceof ApiError ? err.message : 'Something went wrong.')
          setStatus('error')
        }
      }, 1200)
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Something went wrong.')
      setStatus('error')
    }
  }

  const haveGroup = results.filter((r) => r.missing_count === 0)
  const shopGroup = results.filter((r) => r.missing_count > 0)

  return (
    <div className="suggest">
      <div className="suggest__header">
        <div className="suggest__title">Suggest</div>
        <input
          className="suggest__input"
          placeholder="chicken · something light · quick"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="suggest__avoid-row">
          <span className="suggest__avoid-label">Avoid</span>
          {avoid.map((name) => (
            <button key={name} className="suggest__avoid-chip" onClick={() => removeAvoid(name)}>
              <span>{name}</span>
              <span className="suggest__avoid-x">×</span>
            </button>
          ))}
          {!addingAvoid && (
            <button className="suggest__avoid-add" onClick={() => setAddingAvoid(true)}>
              + add
            </button>
          )}
        </div>
        {addingAvoid && (
          <div className="suggest__avoid-picker">
            <input
              className="suggest__avoid-picker-input"
              placeholder="Ingredient to avoid"
              value={avoidTyped}
              autoFocus
              onChange={(e) => setAvoidTyped(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && avoidTyped.trim()) addAvoid(avoidTyped.trim())
                if (e.key === 'Escape') setAddingAvoid(false)
              }}
            />
            {avoidSuggestions.length > 0 && (
              <div className="suggest__avoid-suggestions">
                {avoidSuggestions.map((s) => (
                  <button key={s.id} className="suggest__avoid-suggestion" onClick={() => addAvoid(s.name)}>
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        <button className="suggest__run" onClick={runSuggest} disabled={status === 'loading'}>
          Find something
        </button>
      </div>

      <div className="suggest__scroll sc">
        {status === 'loading' && (
          <div className="suggest__loading">
            <div className="suggest__loading-row">
              <span className="suggest__spinner" />
              <span>Reading your pantry…</span>
            </div>
            <div className="suggest__skeleton" style={{ opacity: 0.75 }} />
            <div className="suggest__skeleton" style={{ opacity: 0.5 }} />
            <div className="suggest__skeleton" style={{ opacity: 0.3 }} />
          </div>
        )}

        {status === 'error' && (
          <div className="suggest__error-card">
            <div className="suggest__error-title">Couldn't get suggestions</div>
            <div className="suggest__error-body">{errorMsg} Your pantry is unchanged.</div>
            <div className="suggest__error-actions">
              <button className="suggest__error-retry" onClick={runSuggest}>
                Try again
              </button>
            </div>
          </div>
        )}

        {status === 'results' && results.length === 0 && (
          <div className="suggest__empty">No matches. Try a different search or fewer avoids.</div>
        )}

        {status === 'results' && (
          <div className="suggest__results">
            {haveGroup.length > 0 && (
              <ResultGroup label="From your pantry" items={haveGroup} onOpen={onOpenRecipe} />
            )}
            {shopGroup.length > 0 && (
              <ResultGroup label="Worth a shop" items={shopGroup} onOpen={onOpenRecipe} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ResultGroup({
  label,
  items,
  onOpen,
}: {
  label: string
  items: RecipeSummary[]
  onOpen: (id: number) => void
}) {
  return (
    <div className="suggest__group">
      <div className="suggest__group-label">{label}</div>
      <div className="suggest__group-items">
        {items.map((r) => (
          <button key={r.id} className="suggest__result" onClick={() => onOpen(r.id)}>
            <span className="suggest__result-title">{r.title}</span>
            <span className="suggest__result-meta">
              {r.est_minutes != null && <span>{r.est_minutes} min</span>}
              <span className="suggest__result-have">{r.have_count} have</span>
              {r.missing_count > 0 && (
                <span className="suggest__result-missing">{r.missing_count} missing</span>
              )}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
