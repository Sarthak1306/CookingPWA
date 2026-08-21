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

const RING_RADIUS = 104
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS

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

function ExitIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  )
}

function AwakeIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
      <circle cx="12" cy="12" r="4" />
    </svg>
  )
}

function PlayIcon() {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5.5v13l11-6.5z" />
    </svg>
  )
}

function PauseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5h3v14H8zM13 5h3v14h-3z" />
    </svg>
  )
}

function ExtendIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v5l3 2" />
      <path d="M3.5 8.5A9 9 0 1 1 3 13" />
      <path d="M2 4v5h5" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  )
}

function PrevIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 12H6M11 6l-6 6 6 6" />
    </svg>
  )
}

function NextIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h13M13 6l6 6-6 6" />
    </svg>
  )
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

  function extendTimer(seconds: number) {
    if (!hasTimer) return
    if (timer.status === 'running') {
      setTimer((t) => ({ ...t, endsAt: (t.endsAt ?? Date.now()) + seconds * 1000 }))
    } else if (timer.status === 'done') {
      setTimer({ status: 'running', endsAt: Date.now() + seconds * 1000, remainingWhenPaused: null })
    } else if (timer.status === 'paused') {
      setTimer((t) => ({ ...t, remainingWhenPaused: (t.remainingWhenPaused ?? 0) + seconds }))
    }
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

  const futureStepsSeconds = steps.slice(stepIndex + 1).reduce((sum, s) => sum + (s.timer_seconds ?? 0), 0)
  const minutesLeft = Math.ceil((remaining + futureStepsSeconds) / 60)

  return (
    <div className="cook">
      <div className="cook__topbar">
        <button className="cook__exit" onClick={onExit} aria-label="Exit cook mode">
          <ExitIcon />
        </button>
        <div className="cook__topbar-text">
          <span className="cook__step-counter">
            Step {stepIndex + 1} of {steps.length}
            {minutesLeft > 0 && ` · about ${minutesLeft} min left`}
          </span>
        </div>
        <span className="cook__awake-pill">
          <AwakeIcon />
          Screen awake
        </span>
      </div>

      <div className="cook__progress">
        <div className="cook__progress-track">
          {steps.map((s, i) => (
            <span
              key={s.position}
              className={`cook__progress-seg${
                i < stepIndex ? ' cook__progress-seg--done' : i === stepIndex ? ' cook__progress-seg--current' : ''
              }`}
              style={{ flex: i === stepIndex ? 1.6 : 1 }}
            />
          ))}
        </div>
        <div className="cook__progress-dots">
          {steps.map((s, i) => (
            <span key={s.position} className="cook__progress-dot-cell" style={{ flex: i === stepIndex ? 1.6 : 1 }}>
              {s.timer_seconds != null && (
                <span className={`cook__progress-dot${i === stepIndex ? ' cook__progress-dot--current' : ''}`} />
              )}
            </span>
          ))}
        </div>
      </div>

      <div className="cook__body sc">
        <div className="cook__step-row">
          <span className="cook__step-n">{stepIndex + 1}</span>
          <span className="cook__step-text">{step.text}</span>
        </div>

        {hasTimer && (
          <div className="cook__timer">
            <div className={`cook__ring cook__ring--${timer.status}`}>
              {timer.status === 'done' && <span className="cook__ring-halo" />}
              <svg width="236" height="236" viewBox="0 0 236 236" className="cook__ring-svg">
                <circle cx="118" cy="118" r={RING_RADIUS} fill="none" stroke="var(--ring-track)" strokeWidth="14" />
                {(timer.status === 'running' || timer.status === 'paused') && (
                  <circle
                    cx="118"
                    cy="118"
                    r={RING_RADIUS}
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="14"
                    strokeLinecap="round"
                    strokeDasharray={RING_CIRCUMFERENCE}
                    strokeDashoffset={RING_CIRCUMFERENCE * (1 - remaining / step.timer_seconds!)}
                    className="cook__ring-progress"
                  />
                )}
                {timer.status === 'done' && (
                  <circle cx="118" cy="118" r={RING_RADIUS} fill="none" stroke="var(--accent-2)" strokeWidth="14" />
                )}
              </svg>
              <div className="cook__ring-center">
                {timer.status === 'done' ? (
                  <>
                    <span className="cook__ring-check">
                      <CheckIcon />
                    </span>
                    <span className="cook__ring-done-text">Time's up</span>
                    <span className="cook__ring-caption">{Math.round(step.timer_seconds! / 60)} min timer</span>
                  </>
                ) : (
                  <>
                    <span className={`cook__ring-time${timer.status === 'idle' ? ' cook__ring-time--idle' : ''}`}>
                      {formatMMSS(remaining)}
                    </span>
                    <span className="cook__ring-caption">
                      {timer.status === 'idle' ? 'Timer ready' : timer.status === 'paused' ? 'Paused' : 'Running'}
                    </span>
                  </>
                )}
              </div>
            </div>

            {(timer.status === 'idle' || timer.status === 'paused') && (
              <button className="cook__timer-btn cook__timer-btn--start" onClick={startTimer}>
                <PlayIcon />
                {timer.status === 'paused' ? 'Resume' : `Start ${Math.round(step.timer_seconds! / 60)} min timer`}
              </button>
            )}
            {timer.status === 'running' && (
              <div className="cook__timer-actions">
                <button className="cook__timer-btn cook__timer-btn--secondary" onClick={pauseTimer}>
                  <PauseIcon />
                  Pause
                </button>
                <button className="cook__timer-btn cook__timer-btn--ghost" onClick={() => extendTimer(60)}>
                  <ExtendIcon />
                  +1 min
                </button>
              </div>
            )}
            {timer.status === 'done' && (
              <button className="cook__timer-btn cook__timer-btn--secondary" onClick={() => extendTimer(120)}>
                <ExtendIcon />
                Give it 2 more min
              </button>
            )}
          </div>
        )}
      </div>

      <div className="cook__nav">
        <button className="cook__prev" onClick={goPrev} disabled={stepIndex === 0} aria-label="Previous step">
          <PrevIcon />
        </button>
        <button className={`cook__next${timer.status === 'done' ? ' cook__next--done' : ''}`} onClick={goNext} disabled={finishing}>
          {finishing ? 'Finishing…' : isLast ? 'Finish' : 'Next step'}
          {!finishing && <NextIcon />}
        </button>
      </div>
    </div>
  )
}
