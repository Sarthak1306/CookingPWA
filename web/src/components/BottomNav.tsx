import './BottomNav.css'

const TABS = [
  { id: 'pantry', label: 'Pantry' },
  { id: 'suggest', label: 'Suggest' },
  { id: 'shopping', label: 'Shopping' },
  { id: 'profile', label: 'Profile' },
] as const

const ENABLED = new Set(['pantry', 'suggest', 'profile'])

export default function BottomNav({
  active,
  onNavigate,
}: {
  active: string
  onNavigate: (tab: 'pantry' | 'suggest' | 'profile') => void
}) {
  return (
    <nav className="bottom-nav">
      {TABS.map((tab) => {
        const isActive = tab.id === active
        const isEnabled = ENABLED.has(tab.id)
        return (
          <button
            key={tab.id}
            className={`bottom-nav__tab${isActive ? ' bottom-nav__tab--active' : ''}`}
            disabled={!isEnabled}
            title={isEnabled ? undefined : 'Coming in a later phase'}
            onClick={() => isEnabled && onNavigate(tab.id as 'pantry' | 'suggest' | 'profile')}
          >
            <span className="bottom-nav__dot" />
            <span className="bottom-nav__label">{tab.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
