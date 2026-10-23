import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, giftCards, GIFT_DISCOUNT_PERCENT, money, type GiftPurchased } from '../api'

const AMOUNTS = [25, 50, 100, 200]
const EMAIL = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]{2,}$/

// Parents and loved ones buy a digital gift certificate for a student. The student gets a code by email and uses it
// in the cart: everything paid for with it is 10% off. No payment is taken (this is a class project) and the page says so.
export default function GiftCertificates() {
  const [amount, setAmount] = useState(50)
  const [form, setForm] = useState({ purchaser_name: '', purchaser_email: '', recipient_name: '', recipient_email: '', message: '' })
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<GiftPurchased | null>(null)
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }))

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.purchaser_name.trim() || !form.recipient_name.trim()) return setProblem('Please enter your name and the student’s name.')
    if (!EMAIL.test(form.purchaser_email.trim()) || !EMAIL.test(form.recipient_email.trim())) return setProblem('Please check both email addresses.')
    setProblem('')
    setBusy(true)
    try {
      setDone(await giftCards.buy({ amount, ...form }))
    } catch (err) {
      setProblem((err as ApiError).message)
    } finally {
      setBusy(false)
    }
  }

  if (done)
    return (
      <div className="container page">
        <div className="form-card centered">
          <h1>Your gift certificate is ready</h1>
          <p>
            A {money(done.amount)} gift certificate for <strong>{done.recipient_name}</strong> was emailed to {done.recipient_email}.
          </p>
          <p>Here is the code, shown only this once:</p>
          <p className="gift-code" data-testid="gift-code">
            {done.code}
          </p>
          <p className="notice">
            {done.payment_note} Everything {done.recipient_name} buys with it is {GIFT_DISCOUNT_PERCENT}% off.
          </p>
          <p className="form-switch">
            <button className="link-button" onClick={() => setDone(null)}>
              Send another
            </button>{' '}
            · <Link to="/products">Browse products</Link>
          </p>
        </div>
      </div>
    )

  return (
    <div className="container page">
      <header className="page-head">
        <h1>Gift Certificates</h1>
        <p>
          Send a student a digital gift card so they can pick out the Yale gear they actually want.{' '}
          <strong>Everything they buy with it is {GIFT_DISCOUNT_PERCENT}% off.</strong>
        </p>
      </header>

      <form className="form-card gift-form" onSubmit={onSubmit} noValidate>
        <fieldset className="amounts">
          <legend>Choose an amount</legend>
          <div className="amount-row">
            {AMOUNTS.map((a) => (
              <label key={a} className={`amount ${amount === a ? 'on' : ''}`}>
                <input type="radio" name="amount" checked={amount === a} onChange={() => setAmount(a)} />
                {money(a)}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="two-up">
          <div className="field">
            <label htmlFor="g-from">Your name</label>
            <input id="g-from" value={form.purchaser_name} onChange={set('purchaser_name')} maxLength={50} autoComplete="name" />
          </div>
          <div className="field">
            <label htmlFor="g-from-email">Your email</label>
            <input id="g-from-email" type="email" value={form.purchaser_email} onChange={set('purchaser_email')} autoComplete="email" />
          </div>
          <div className="field">
            <label htmlFor="g-to">Student’s name</label>
            <input id="g-to" value={form.recipient_name} onChange={set('recipient_name')} maxLength={50} />
          </div>
          <div className="field">
            <label htmlFor="g-to-email">Student’s email</label>
            <input id="g-to-email" type="email" value={form.recipient_email} onChange={set('recipient_email')} />
          </div>
        </div>
        <div className="field">
          <label htmlFor="g-msg">A note for them (optional)</label>
          <input id="g-msg" value={form.message} onChange={set('message')} maxLength={300} placeholder="Proud of you! Go Bulldogs!" />
        </div>
        {problem && (
          <p className="alert" role="alert">
            {problem}
          </p>
        )}
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? 'Sending…' : `Send a ${money(amount)} gift certificate`}
        </button>
        <p className="dev-note">
          This is a class project: no payment is taken and no card details are collected. Please don’t type any. The gift certificate itself works in this shop.
        </p>
      </form>
    </div>
  )
}
