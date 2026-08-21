import { useEffect, useState } from 'react'
import Login from './pages/Login'
import { getMe, logout } from './api'
import './App.css'

type AuthState = { status: 'checking' } | { status: 'anonymous' } | { status: 'signedIn'; username: string }

function App() {
  const [auth, setAuth] = useState<AuthState>({ status: 'checking' })

  useEffect(() => {
    getMe()
      .then(({ username }) => setAuth({ status: 'signedIn', username }))
      .catch(() => setAuth({ status: 'anonymous' }))
  }, [])

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
    <div className="app-shell app-shell--placeholder">
      <div className="placeholder">
        <div className="placeholder__wordmark">Kitchen</div>
        <p>Signed in as {auth.username}.</p>
        <p className="placeholder__note">
          The pantry, suggest, and cook screens land in later phases.
        </p>
        <button
          className="placeholder__signout"
          onClick={() => logout().then(() => setAuth({ status: 'anonymous' }))}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}

export default App
