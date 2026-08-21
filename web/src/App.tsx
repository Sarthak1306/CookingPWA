import { useEffect, useRef, useState } from 'react'
import Login from './pages/Login'
import Pantry from './pages/Pantry'
import AddEditItem from './pages/AddEditItem'
import Suggest from './pages/Suggest'
import Recipe from './pages/Recipe'
import CookMode from './pages/CookMode'
import RanOut from './pages/RanOut'
import Profile from './pages/Profile'
import Shopping from './pages/Shopping'
import BottomNav from './components/BottomNav'
import Toast from './components/Toast'
import { getMe, logout } from './api'
import type { PantryItem, RecipeStep, UsedPantryItem } from './types'
import './App.css'

type AuthState = { status: 'checking' } | { status: 'anonymous' } | { status: 'signedIn'; username: string }
type Screen =
  | { name: 'pantry' }
  | { name: 'addEdit'; item: PantryItem | null }
  | { name: 'suggest' }
  | { name: 'recipe'; recipeId: number; from: 'pantry' | 'suggest' }
  | { name: 'cook'; recipeId: number; steps: RecipeStep[]; from: 'pantry' | 'suggest' }
  | { name: 'ranOut'; usedItems: UsedPantryItem[]; cookLogId: number }
  | { name: 'profile' }
  | { name: 'shopping' }

const NAV_SCREENS = new Set(['pantry', 'suggest', 'shopping', 'profile'])

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
        <div className="app-shell__signout-row">
          <button
            className="app-shell__signout"
            onClick={() => logout().then(() => setAuth({ status: 'anonymous' }))}
          >
            Sign out
          </button>
        </div>
      )}

      {screen.name === 'pantry' && (
        <Pantry
          key={pantryVersion}
          onOpenAdd={() => setScreen({ name: 'addEdit', item: null })}
          onOpenEdit={(item) => setScreen({ name: 'addEdit', item })}
          onFlash={flash}
        />
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

      {screen.name === 'suggest' && (
        <Suggest onOpenRecipe={(recipeId) => setScreen({ name: 'recipe', recipeId, from: 'suggest' })} />
      )}

      {screen.name === 'recipe' && (
        <Recipe
          recipeId={screen.recipeId}
          onBack={() => (screen.from === 'pantry' ? setScreen({ name: 'pantry' }) : setScreen({ name: 'suggest' }))}
          onStartCook={(recipeId, steps) => setScreen({ name: 'cook', recipeId, steps, from: screen.from })}
          onFlash={flash}
        />
      )}

      {screen.name === 'cook' && (
        <CookMode
          recipeId={screen.recipeId}
          steps={screen.steps}
          onExit={() => setScreen({ name: 'recipe', recipeId: screen.recipeId, from: screen.from })}
          onFinished={(_recipeId, usedItems, cookLogId) => setScreen({ name: 'ranOut', usedItems, cookLogId })}
          onFlash={flash}
        />
      )}

      {screen.name === 'ranOut' && (
        <RanOut
          usedItems={screen.usedItems}
          cookLogId={screen.cookLogId}
          onFlash={flash}
          onDone={() => {
            setPantryVersion((v) => v + 1)
            setScreen({ name: 'pantry' })
          }}
        />
      )}

      {screen.name === 'profile' && <Profile onFlash={flash} />}

      {screen.name === 'shopping' && (
        <Shopping onFlash={flash} onTicked={() => setPantryVersion((v) => v + 1)} />
      )}

      {NAV_SCREENS.has(screen.name) && (
        <BottomNav
          active={screen.name}
          onNavigate={(tab) => {
            if (tab === 'pantry') setScreen({ name: 'pantry' })
            else if (tab === 'suggest') setScreen({ name: 'suggest' })
            else if (tab === 'shopping') setScreen({ name: 'shopping' })
            else setScreen({ name: 'profile' })
          }}
        />
      )}

      <Toast message={toast} />
    </div>
  )
}

export default App
