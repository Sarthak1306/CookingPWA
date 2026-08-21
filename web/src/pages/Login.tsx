import { useState, type FormEvent } from 'react'
import { ApiError, login } from '../api'
import './Login.css'

export default function Login({ onSignedIn }: { onSignedIn: (username: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (submitting) return
    setError('')
    setSubmitting(true)
    try {
      const { username: signedInAs } = await login(username, password)
      onSignedIn(signedInAs)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="login" onSubmit={handleSubmit}>
      <div className="login__wordmark">Kitchen</div>
      <div className="login__fields">
        <label className="login__field">
          <span className="login__label">Username</span>
          <input
            className="login__input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
          />
        </label>
        <label className="login__field">
          <span className="login__label">Password</span>
          <input
            className="login__input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
      </div>
      {error && <div className="login__error">{error}</div>}
      <button className="login__submit" type="submit" disabled={submitting}>
        {submitting ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  )
}
