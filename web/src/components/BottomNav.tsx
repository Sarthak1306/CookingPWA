import './BottomNav.css'

function PantryIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M4 10.5L6 4h12l2 6.5M4 10.5h16M4 10.5v7a1.5 1.5 0 0 0 1.5 1.5h13a1.5 1.5 0 0 0 1.5-1.5v-7"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M9 14h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )
}

function SuggestIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 3.5l1.7 4.3 4.3 1.7-4.3 1.7-1.7 4.3-1.7-4.3-4.3-1.7 4.3-1.7L12 3.5z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M18.5 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8.8-2z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ShoppingIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M7 8V6.5a5 5 0 0 1 10 0V8"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M5.5 8h13l.7 11a1.5 1.5 0 0 1-1.5 1.6H6.3a1.5 1.5 0 0 1-1.5-1.6L5.5 8z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ProfileIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="8.5" r="3.5" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M5 20c0-3.6 3.13-6.5 7-6.5s7 2.9 7 6.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  )
}

const TABS = [
  { id: 'pantry', label: 'Pantry', Icon: PantryIcon },
  { id: 'suggest', label: 'Suggest', Icon: SuggestIcon },
  { id: 'shopping', label: 'Shopping', Icon: ShoppingIcon },
  { id: 'profile', label: 'Profile', Icon: ProfileIcon },
] as const

const ENABLED = new Set(['pantry', 'suggest', 'shopping', 'profile'])

export default function BottomNav({
  active,
  onNavigate,
}: {
  active: string
  onNavigate: (tab: 'pantry' | 'suggest' | 'shopping' | 'profile') => void
}) {
  return (
    <nav className="bottom-nav">
      {TABS.map(({ id, label, Icon }) => {
        const isActive = id === active
        const isEnabled = ENABLED.has(id)
        return (
          <button
            key={id}
            className={`bottom-nav__tab${isActive ? ' bottom-nav__tab--active' : ''}`}
            disabled={!isEnabled}
            title={isEnabled ? undefined : 'Coming in a later phase'}
            onClick={() => isEnabled && onNavigate(id as 'pantry' | 'suggest' | 'shopping' | 'profile')}
          >
            <span className="bottom-nav__icon">
              <Icon />
            </span>
            <span className="bottom-nav__label">{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
