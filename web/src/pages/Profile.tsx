import { useEffect, useState } from 'react'
import { ApiError, getTasteProfile, updateTasteProfile } from '../api'
import './Profile.css'

const EFFORT_OPTIONS = ['Under 20 min', 'Weeknight, 30–40 min', 'An hour is fine', 'All afternoon']

const TASTE_TAGS = [
  'Sharp & lemony',
  'Herby',
  'One-pan',
  'Chilli heat',
  'Rich & creamy',
  'Sweet mains',
  'Slow-cooked',
  'Raw & cold',
]

export default function Profile({ onFlash }: { onFlash: (msg: string) => void }) {
  const [effort, setEffort] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [bodyText, setBodyText] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getTasteProfile()
      .then((p) => {
        setEffort(p.effort)
        setTags(p.tags)
        setBodyText(p.body_text)
      })
      .catch((err) => onFlash(err instanceof ApiError ? err.message : "Couldn't load your profile."))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function toggleTag(tag: string) {
    setTags((t) => (t.includes(tag) ? t.filter((x) => x !== tag) : [...t, tag]))
  }

  async function save() {
    if (saving) return
    setSaving(true)
    try {
      await updateTasteProfile({ effort, tags, body_text: bodyText })
      onFlash('Profile saved')
    } catch (err) {
      onFlash(err instanceof ApiError ? err.message : "Couldn't save your profile.")
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="profile">
        <div className="profile__header">
          <div className="profile__title">Profile</div>
        </div>
        <div className="profile__empty">Loading…</div>
      </div>
    )
  }

  return (
    <div className="profile">
      <div className="profile__header">
        <div className="profile__title">Profile</div>
      </div>

      <div className="profile__scroll sc">
        <div className="profile__section-label">Effort</div>
        <div className="profile__effort-list">
          {EFFORT_OPTIONS.map((option) => (
            <button
              key={option}
              className={`profile__effort-btn${effort === option ? ' profile__effort-btn--active' : ''}`}
              onClick={() => setEffort(option)}
            >
              {option}
            </button>
          ))}
        </div>

        <div className="profile__section-label">What you like</div>
        <div className="profile__tag-grid">
          {TASTE_TAGS.map((tag) => (
            <button
              key={tag}
              className={`profile__tag${tags.includes(tag) ? ' profile__tag--active' : ''}`}
              onClick={() => toggleTag(tag)}
            >
              {tag}
            </button>
          ))}
        </div>

        <div className="profile__section-label">In your own words</div>
        <textarea
          className="profile__body-text"
          value={bodyText}
          onChange={(e) => setBodyText(e.target.value)}
          placeholder="Anything else worth knowing about what you like to cook and eat…"
        />
        <div className="profile__note">
          This part also rewrites itself over time from what you cook and rate.
        </div>
      </div>

      <div className="profile__footer">
        <button className="profile__save" onClick={save} disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  )
}
