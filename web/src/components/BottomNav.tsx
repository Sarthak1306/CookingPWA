import './BottomNav.css'

const TABS = [
  { id: 'pantry', label: 'Pantry' },
  { id: 'suggest', label: 'Suggest' },
  { id: 'shopping', label: 'Shopping' },
  { id: 'profile', label: 'Profile' },
] as const

export default function BottomNav({ active }: { active: string }) {
  return (
    <nav className="bottom-nav">
      {TABS.map((tab) => {
        const isActive = tab.id === active
        const isEnabled = tab.id === 'pantry'
        return (
          <button
            key={tab.id}
            className={`bottom-nav__tab${isActive ? ' bottom-nav__tab--active' : ''}`}
            disabled={!isEnabled}
            title={isEnabled ? undefined : 'Coming in a later phase'}
          >
            <span className="bottom-nav__dot" />
            <span className="bottom-nav__label">{tab.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
