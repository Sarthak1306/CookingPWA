import { useEffect, useRef, useState } from 'react'
import Login from './pages/Login'
import Pantry from './pages/Pantry'
import AddEditItem from './pages/AddEditItem'
import BottomNav from './components/BottomNav'
import Toast from './components/Toast'
import { getMe, logout } from './api'
import type { PantryItem } from './types'
import './App.css'

type AuthState = { status: 'checking' } | { status: 'anonymous' } | { status: 'signedIn'; username: string }
type Screen = { name: 'pantry' } | { name: 'addEdit'; item: PantryItem | null }

function App() {
  const [auth, setAuth] = useState<AuthState>({ status: 'checking' })
  const [screen, setScreen] = useState<Screen>({ name: 'pantry' })
  const [toast, setToast] = useState('')
  const [pantryVersion, setPantryVersion] = useState(0)
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    getMe()
      .then(({ username }) => setAuth({ status: 'signedIn', username }))
      .catch(() => setAuth({ status: 'anonymous' }))
  }, [])

  function flash(msg: string) {
    setToast(msg)
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(''), 2000)
  }

  if (auth.status === 'checking') {
    return <div className="app-shell" />
  }

  if (auth.status === 'anonymous') {
    return (
      <div className="app-shell">
        <Login onSignedIn={(username) => setAuth({ status: 'signedIn', username })} />
      </div>
    )
  }

  return (
    <div className="app-shell app-shell--app">
      {screen.name === 'pantry' && (
        <>
          <div className="app-shell__signout-row">
            <button className="app-shell__signout" onClick={() => logout().then(() => setAuth({ status: 'anonymous' }))}>
              Sign out
            </button>
          </div>
          <Pantry
            key={pantryVersion}
            onOpenAdd={() => setScreen({ name: 'addEdit', item: null })}
            onOpenEdit={(item) => setScreen({ name: 'addEdit', item })}
            onFlash={flash}
          />
          <BottomNav active="pantry" />
        </>
      )}

      {screen.name === 'addEdit' && (
        <AddEditItem
          item={screen.item}
          onBack={() => setScreen({ name: 'pantry' })}
          onSaved={() => {
            setPantryVersion((v) => v + 1)
            setScreen({ name: 'pantry' })
          }}
          onFlash={flash}
        />
      )}

      <Toast message={toast} />
    </div>
  )
}

export default App
