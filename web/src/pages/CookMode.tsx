import { useEffect, useRef, useState } from 'react'
import { ApiError, cookRecipe } from '../api'
import type { RecipeStep, UsedPantryItem } from '../types'
import './CookMode.css'

type TimerStatus = 'idle' | 'running' | 'paused' | 'done'

type TimerState = {
  status: TimerStatus
  endsAt: number | null // wall-clock timestamp — the only source of truth for "how long left"
  remainingWhenPaused: number | null
}

function idleTimer(): TimerState {
  return { status: 'idle', endsAt: null, remainingWhenPaused: null }
}

// Always derived from a timestamp, never accumulated tick-by-tick — a
// setInterval elsewhere just forces re-renders so this gets recomputed;
// it is never itself the source of truth. That's what makes it survive
// the screen locking mid-timer instead of drifting or freezing.
function remainingSeconds(timer: TimerState, durationSeconds: number): number {
  if (timer.status === 'idle') return durationSeconds
  if (timer.status === 'done') return 0
  if (timer.status === 'paused') return timer.remainingWhenPaused ?? durationSeconds
  if (timer.status === 'running' && timer.endsAt) {
    return Math.max(0, Math.ceil((timer.endsAt - Date.now()) / 1000))
  }
  return durationSeconds
}

function formatMMSS(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function useWakeLock() {
  useEffect(() => {
    let sentinel: WakeLockSentinel | null = null

    async function acquire() {
      if (!('wakeLock' in navigator)) return
      try {
        sentinel = await navigator.wakeLock.request('screen')
      } catch {
        // Unsupported or denied — cooking still works, the phone just
        // might dim. Not worth surfacing to the user.
      }
    }

    function handleVisibility() {
      if (document.visibilityState === 'visible') acquire()
    }

    acquire()
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility)
      sentinel?.release().catch(() => {})
    }
  }, [])
}

export default function CookMode({
  recipeId,
  steps,
  onExit,
  onFinished,
  onFlash,
}: {
  recipeId: number
  steps: RecipeStep[]
  onExit: () => void
  onFinished: (recipeId: number, usedItems: UsedPantryItem[], cookLogId: number) => void
  onFlash: (msg: string) => void
}) {
  useWakeLock()

  const [stepIndex, setStepIndex] = useState(0)
  const [timer, setTimer] = useState<TimerState>(idleTimer())
  const [finishing, setFinishing] = useState(false)
  const [, forceTick] = useState(0)
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const step = steps[stepIndex]
  const hasTimer = step.timer_seconds != null && step.timer_seconds > 0

  useEffect(() => {
    if (timer.status !== 'running') {
      if (tickRef.current) {
        clearInterval(tickRef.current)
        tickRef.current = null
      }
      return
    }
    tickRef.current = setInterval(() => {
      if (hasTimer && remainingSeconds(timer, step.timer_seconds!) <= 0) {
        setTimer((t) => ({ ...t, status: 'done', endsAt: null }))
      } else {
        forceTick((n) => n + 1)
      }
    }, 250)
    return () => {
      if (tickRef.current) clearInterval(tickRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timer.status, stepIndex])

  function startTimer() {
    if (!hasTimer) return
    const duration = timer.status === 'paused' ? (timer.remainingWhenPaused ?? step.timer_seconds!) : step.timer_seconds!
    setTimer({ status: 'running', endsAt: Date.now() + duration * 1000, remainingWhenPaused: null })
  }

  function pauseTimer() {
    if (!hasTimer) return
    const remaining = remainingSeconds(timer, step.timer_seconds!)
    setTimer({ status: 'paused', endsAt: null, remainingWhenPaused: remaining })
  }

  function goPrev() {
    setTimer(idleTimer())
    setStepIndex((i) => Math.max(0, i - 1))
  }

  async function goNext() {
    if (stepIndex < steps.length - 1) {
      setTimer(idleTimer())
      setStepIndex((i) => i + 1)
      return
    }
    if (finishing) return
    setFinishing(true)
    try {
      const result = await cookRecipe(recipeId)
      onFinished(recipeId, result.used_pantry_items, result.cook_log_id)
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't log that as cooked.")
      setFinishing(false)
    }
  }

  const remaining = hasTimer ? remainingSeconds(timer, step.timer_seconds!) : 0
  const isLast = stepIndex === steps.length - 1

  return (
    <div className="cook">
      <div className="cook__topbar">
        <span className="cook__counter">
          Step {stepIndex + 1} of {steps.length}
        </span>
        <button className="cook__exit" onClick={onExit}>
          Exit
        </button>
      </div>

      <div className="cook__body sc">
        <div className="cook__step-text">{step.text}</div>

        {hasTimer && (
          <div className="cook__timer">
            <div className="cook__timer-display">{formatMMSS(remaining)}</div>
            {timer.status !== 'running' && timer.status !== 'done' && (
              <button className="cook__timer-btn cook__timer-btn--start" onClick={startTimer}>
                {timer.status === 'paused' ? 'Resume' : 'Start timer'}
              </button>
            )}
            {timer.status === 'running' && (
              <button className="cook__timer-btn cook__timer-btn--pause" onClick={pauseTimer}>
                Pause
              </button>
            )}
            {timer.status === 'done' && <div className="cook__timer-done">Time's up</div>}
          </div>
        )}
      </div>

      <div className="cook__nav">
        <button className="cook__prev" onClick={goPrev} disabled={stepIndex === 0} aria-label="Previous step">
          ‹
        </button>
        <button className="cook__next" onClick={goNext} disabled={finishing}>
          {finishing ? 'Finishing…' : isLast ? 'Done' : 'Next'}
        </button>
      </div>
      <div className="cook__awake-note">Screen stays awake</div>
    </div>
  )
}
