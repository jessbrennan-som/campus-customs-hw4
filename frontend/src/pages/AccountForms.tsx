import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { accounts, ApiError } from '../api'
import { useAuth } from '../auth'
import { brokenRules, RULES, type Who } from '../passwordRules'

const EMAIL = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]{2,}$/

// A password box with a Show/Hide button.
function PasswordField(props: { label: string; value: string; onChange: (v: string) => void; autoComplete: string; error?: string; id: string }) {
  const [show, setShow] = useState(false)
  return (
    <div className="field">
      <label htmlFor={props.id}>{props.label}</label>
      <div className="password-box">
        <input
          id={props.id}
          type={show ? 'text' : 'password'}
          value={props.value}
          onChange={(e) => props.onChange(e.target.value)}
          autoComplete={props.autoComplete}
          aria-invalid={!!props.error}
          aria-describedby={props.error ? `${props.id}-error` : undefined}
        />
        <button type="button" className="show-toggle" onClick={() => setShow((s) => !s)} aria-pressed={show}>
          {show ? 'Hide' : 'Show'}
        </button>
      </div>
      {props.error && (
        <em className="field-error" id={`${props.id}-error`}>
          {props.error}
        </em>
      )}
    </div>
  )
}

function TextField(props: { label: string; value: string; onChange: (v: string) => void; autoComplete: string; type?: string; error?: string; id: string }) {
  return (
    <div className="field">
      <label htmlFor={props.id}>{props.label}</label>
      <input
        id={props.id}
        type={props.type ?? 'text'}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        autoComplete={props.autoComplete}
        aria-invalid={!!props.error}
        aria-describedby={props.error ? `${props.id}-error` : undefined}
      />
      {props.error && (
        <em className="field-error" id={`${props.id}-error`}>
          {props.error}
        </em>
      )}
    </div>
  )
}

// The rules, ticked off as you type.
function Checklist({ password, who }: { password: string; who: Who }) {
  const broken = new Set(brokenRules(password, who).map((r) => r.id))
  return (
    <div className="rules" aria-live="polite">
      <p>Your password needs:</p>
      <ul>
        {RULES.map((r) => (
          <li key={r.id} className={password ? (broken.has(r.id) ? 'bad' : 'good') : ''}>
            <span aria-hidden="true">{password ? (broken.has(r.id) ? '✗' : '✓') : '•'}</span> {r.label}
            <span className="sr-only">{password ? (broken.has(r.id) ? ' (not yet)' : ' (done)') : ''}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Alert({ children }: { children: ReactNode }) {
  return (
    <p className="alert" role="alert">
      {children}
    </p>
  )
}

// ---------- Create Account ----------
export function CreateAccount() {
  const { setUser } = useAuth()
  const [f, setF] = useState({ first_name: '', last_name: '', email: '', password: '', confirm_password: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [problem, setProblem] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)
  const [welcome, setWelcome] = useState<string | null>(null)
  const set = (k: keyof typeof f) => (v: string) => setF((cur) => ({ ...cur, [k]: v }))
  const who: Who = { email: f.email, first: f.first_name, last: f.last_name }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const next: Record<string, string> = {}
    if (!f.first_name.trim()) next.first_name = 'Enter your first name.'
    if (!f.last_name.trim()) next.last_name = 'Enter your last name.'
    if (!EMAIL.test(f.email.trim())) next.email = 'Enter a valid email address.'
    if (brokenRules(f.password, who).length) next.password = 'Please meet every rule in the list below.'
    if (f.password !== f.confirm_password) next.confirm_password = "The two passwords don't match."
    setErrors(next)
    setProblem(null)
    if (Object.keys(next).length) return
    setBusy(true)
    try {
      const user = await accounts.register({ ...f, email: f.email.trim() })
      setUser(user)
      setWelcome(user.first_name)
    } catch (err) {
      setProblem(err as ApiError)
    } finally {
      setBusy(false)
    }
  }

  if (welcome)
    return (
      <div className="container narrow page">
        <div className="form-card centered">
          <h1>Welcome, {welcome}!</h1>
          <p>Your account is ready and you're logged in. Lux et Veritas!</p>
          <Link to="/products" className="btn btn-primary btn-large">
            Start shopping
          </Link>
        </div>
      </div>
    )

  return (
    <div className="container narrow page">
      <div className="form-card">
        <h1>Create Account</h1>
        <form onSubmit={onSubmit} noValidate>
          <div className="two-up">
            <TextField id="first" label="First name" value={f.first_name} onChange={set('first_name')} autoComplete="given-name" error={errors.first_name} />
            <TextField id="last" label="Last name" value={f.last_name} onChange={set('last_name')} autoComplete="family-name" error={errors.last_name} />
          </div>
          <TextField id="email" label="Email" type="email" value={f.email} onChange={set('email')} autoComplete="email" error={errors.email} />
          <PasswordField id="password" label="Password" value={f.password} onChange={set('password')} autoComplete="new-password" error={errors.password} />
          <Checklist password={f.password} who={who} />
          <PasswordField
            id="confirm"
            label="Confirm password"
            value={f.confirm_password}
            onChange={set('confirm_password')}
            autoComplete="new-password"
            error={errors.confirm_password}
          />
          {problem && (
            <Alert>
              {problem.message}
              {problem.status === 409 && (
                <>
                  {' '}
                  <Link to="/login">Log in</Link>
                </>
              )}
            </Alert>
          )}
          <button className="btn btn-primary btn-block btn-large" disabled={busy}>
            {busy ? 'Creating your account…' : 'Create Account'}
          </button>
        </form>
        <p className="form-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  )
}

// ---------- Log In ----------
export function LogIn() {
  const { setUser } = useAuth()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const next: Record<string, string> = {}
    if (!EMAIL.test(email.trim())) next.email = 'Enter a valid email address.'
    if (!password) next.password = 'Enter your password.'
    setErrors(next)
    setProblem(null)
    if (Object.keys(next).length) return
    setBusy(true)
    try {
      setUser(await accounts.login(email.trim(), password))
      navigate(from, { replace: true })
    } catch (err) {
      setProblem((err as ApiError).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container narrow page">
      <div className="form-card">
        <h1>Log In</h1>
        <form onSubmit={onSubmit} noValidate>
          <TextField id="email" label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" error={errors.email} />
          <PasswordField id="password" label="Password" value={password} onChange={setPassword} autoComplete="current-password" error={errors.password} />
          <p className="forgot">
            <Link to="/forgot-password">Forgot your password?</Link>
          </p>
          {problem && <Alert>{problem}</Alert>}
          <button className="btn btn-primary btn-block btn-large" disabled={busy}>
            {busy ? 'Logging in…' : 'Log In'}
          </button>
        </form>
        <p className="form-switch">
          New to Campus Customs? <Link to="/create-account">Create an account</Link>
        </p>
      </div>
    </div>
  )
}

// ---------- Forgot password ----------
export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!EMAIL.test(email.trim())) return setError('Enter the email address on your account.')
    setBusy(true)
    try {
      setSent((await accounts.forgotPassword(email.trim())).message)
    } catch (err) {
      setError((err as ApiError).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container narrow page">
      <div className="form-card">
        <h1>Reset your password</h1>
        {sent ? (
          <>
            <p className="notice" role="status">
              {sent}
            </p>
            {import.meta.env.DEV && (
              <p className="dev-note">
                Developing? No email server is set up, so the email was saved as a text file in <code>backend/outbox/</code>. Open it and use the link inside.
              </p>
            )}
            <p className="form-switch">
              <Link to="/login">Back to log in</Link>
            </p>
          </>
        ) : (
          <form onSubmit={onSubmit} noValidate>
            <p>Enter the email address on your account and we'll send you a link to choose a new password.</p>
            <TextField id="email" label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
            {error && <Alert>{error}</Alert>}
            <button className="btn btn-primary btn-block btn-large" disabled={busy}>
              {busy ? 'Sending…' : 'Send reset link'}
            </button>
            <p className="form-switch">
              <Link to="/login">Back to log in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}

// ---------- Reset password (the page the email link opens) ----------
export function ResetPassword() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [problem, setProblem] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const next: Record<string, string> = {}
    if (brokenRules(password).length) next.password = 'Please meet every rule in the list below.'
    if (password !== confirm) next.confirm = "The two passwords don't match."
    setErrors(next)
    setProblem(null)
    if (Object.keys(next).length) return
    setBusy(true)
    try {
      setDone((await accounts.resetPassword(token, password, confirm)).message)
    } catch (err) {
      setProblem((err as ApiError).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container narrow page">
      <div className="form-card">
        <h1>Choose a new password</h1>
        {!token ? (
          <>
            <Alert>This page needs the link from your reset email.</Alert>
            <Link to="/forgot-password" className="btn btn-primary">
              Get a new link
            </Link>
          </>
        ) : done ? (
          <>
            <p className="notice" role="status">
              {done}
            </p>
            <Link to="/login" className="btn btn-primary btn-large btn-block">
              Log In
            </Link>
          </>
        ) : (
          <form onSubmit={onSubmit} noValidate>
            <PasswordField id="password" label="New password" value={password} onChange={setPassword} autoComplete="new-password" error={errors.password} />
            <Checklist password={password} who={{}} />
            <PasswordField id="confirm" label="Confirm new password" value={confirm} onChange={setConfirm} autoComplete="new-password" error={errors.confirm} />
            {problem && (
              <Alert>
                {problem}{' '}
                <Link to="/forgot-password">Get a new link</Link>
              </Alert>
            )}
            <button className="btn btn-primary btn-block btn-large" disabled={busy}>
              {busy ? 'Saving…' : 'Save new password'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

// ---------- My Account (logged in): see your details and change your password ----------
export function MyAccount() {
  const { user, ready } = useAuth()
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [problem, setProblem] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!ready) return <p className="container status page">Loading…</p>
  if (!user) return <Navigate to="/login" state={{ from: '/account' }} replace />
  const who: Who = { email: user.email, first: user.first_name, last: user.last_name }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const next: Record<string, string> = {}
    if (!current) next.current = 'Enter your current password.'
    if (brokenRules(password, who).length) next.password = 'Please meet every rule in the list below.'
    else if (password === current) next.password = "Please choose a password that's different from your current one."
    if (password !== confirm) next.confirm = "The two passwords don't match."
    setErrors(next)
    setProblem(null)
    setDone(null)
    if (Object.keys(next).length) return
    setBusy(true)
    try {
      setDone((await accounts.changePassword(current, password, confirm)).message)
      setCurrent('')
      setPassword('')
      setConfirm('')
    } catch (err) {
      setProblem((err as ApiError).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container narrow page">
      <h1>My Account</h1>
      <div className="form-card account-details">
        <h2>Your details</h2>
        <dl>
          <div>
            <dt>Name</dt>
            <dd>
              {user.first_name} {user.last_name}
            </dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{user.email}</dd>
          </div>
        </dl>
      </div>

      <div className="form-card">
        <h2>Change your password</h2>
        <form onSubmit={onSubmit} noValidate>
          <PasswordField id="current" label="Current password" value={current} onChange={setCurrent} autoComplete="current-password" error={errors.current} />
          <PasswordField id="password" label="New password" value={password} onChange={setPassword} autoComplete="new-password" error={errors.password} />
          <Checklist password={password} who={who} />
          <PasswordField id="confirm" label="Confirm new password" value={confirm} onChange={setConfirm} autoComplete="new-password" error={errors.confirm} />
          {problem && <Alert>{problem}</Alert>}
          {done && (
            <p className="notice" role="status">
              {done}
            </p>
          )}
          <button className="btn btn-primary btn-block btn-large" disabled={busy}>
            {busy ? 'Saving…' : 'Change password'}
          </button>
        </form>
        <p className="form-switch">
          Forgot your current password? <Link to="/forgot-password">Reset it by email</Link>
        </p>
      </div>
    </div>
  )
}
