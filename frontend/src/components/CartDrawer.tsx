import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, giftCards, GIFT_DISCOUNT_PERCENT, imageSrc, money, type GiftQuote, type GiftReceipt } from '../api'
import { useAuth } from '../auth'
import { useShop } from '../store'

// Paying with a gift certificate: enter the code, see the 10% off, pay. (The shop takes no other payment yet.)
function GiftPay({ onPaid }: { onPaid: (receipt: GiftReceipt) => void }) {
  const { items } = useShop()
  const { user } = useAuth()
  const [code, setCode] = useState('')
  const [quote, setQuote] = useState<GiftQuote | null>(null)
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  const lines = items.map((i) => ({ product_id: i.productId, size: i.size, quantity: i.quantity }))

  async function run(action: () => Promise<void>) {
    setBusy(true)
    setProblem('')
    try {
      await action()
    } catch (err) {
      setProblem((err as ApiError).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="gift-pay">
      <p className="gift-pay-title">
        Have a gift certificate? <span>Everything is {GIFT_DISCOUNT_PERCENT}% off.</span>
      </p>
      <div className="gift-pay-row">
        <input
          value={code}
          onChange={(e) => {
            setCode(e.target.value)
            setQuote(null)
          }}
          placeholder="CC-XXXX-XXXX-XXXX"
          aria-label="Gift certificate code"
          maxLength={40}
          autoComplete="off"
        />
        <button className="btn btn-secondary" disabled={busy || !code.trim()} onClick={() => void run(async () => setQuote(await giftCards.quote(code.trim(), lines)))}>
          Apply
        </button>
      </div>
      {problem && (
        <p className="alert" role="alert">
          {problem}
        </p>
      )}
      {quote && (
        <div className="gift-quote" aria-live="polite">
          <p>
            <span>Subtotal</span> <span>{money(quote.subtotal)}</span>
          </p>
          <p className="gift-off">
            <span>Gift certificate discount ({quote.discount_percent}%)</span> <span>−{money(quote.discount)}</span>
          </p>
          <p className="gift-total">
            <span>You pay</span> <strong>{money(quote.total)}</strong>
          </p>
          <p className="gift-balance">Certificate balance: {money(quote.balance)}</p>
          {!quote.enough && <p className="alert">This certificate doesn’t cover the whole order. Remove something and try again.</p>}
          {user ? (
            <button
              className="btn btn-primary btn-block"
              disabled={busy || !quote.enough}
              onClick={() => void run(async () => onPaid(await giftCards.pay(code.trim(), lines)))}
            >
              Pay {money(quote.total)} with gift certificate
            </button>
          ) : (
            <p className="notice">
              <Link to="/login">Log in</Link> or <Link to="/create-account">create an account</Link> to pay, so your purchase is saved to your account.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function CartDrawer() {
  const { items, subtotal, cartOpen, setCartOpen, removeItem, clearCart } = useShop()
  const [receipt, setReceipt] = useState<GiftReceipt | null>(null)
  if (!cartOpen) return null
  const close = () => {
    setCartOpen(false)
    setReceipt(null)
  }
  return (
    <div className="drawer-backdrop" onClick={close}>
      <aside className="drawer" role="dialog" aria-label="Shopping cart" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>Your cart</h2>
          <button className="icon-button" onClick={close} aria-label="Close cart">
            ×
          </button>
        </div>
        {receipt ? (
          <div className="drawer-empty gift-receipt" role="status">
            <h3>Thank you!</h3>
            <p>
              Order {receipt.order_id} is saved to your account. You paid {money(receipt.total)} after {receipt.discount_percent}% off ({money(receipt.discount)} saved).
            </p>
            <p>Gift certificate balance left: {money(receipt.balance_remaining)}</p>
            <Link to="/products" className="btn btn-primary" onClick={close}>
              Keep shopping
            </Link>
          </div>
        ) : items.length === 0 ? (
          <div className="drawer-empty">
            <p>Your cart is empty.</p>
            <Link to="/products" className="btn btn-primary" onClick={close}>
              Browse products
            </Link>
          </div>
        ) : (
          <>
            <ul className="drawer-list">
              {items.map((item) => (
                <li key={item.productId + item.size} className="drawer-item">
                  <img src={imageSrc({ image_url: item.imageUrl })} alt="" />
                  <div>
                    <Link to={`/products/${item.productId}`} onClick={close}>
                      {item.name}
                    </Link>
                    <p>
                      Size {item.size} · Qty {item.quantity}
                    </p>
                    <p className="drawer-price">{money(item.price * item.quantity)}</p>
                  </div>
                  <button className="link-button" onClick={() => removeItem(item.productId, item.size)}>
                    Remove
                  </button>
                </li>
              ))}
            </ul>
            <div className="drawer-foot">
              <p className="drawer-subtotal">
                <span>Subtotal</span>
                <strong>{money(subtotal)}</strong>
              </p>
              <GiftPay
                onPaid={(r) => {
                  setReceipt(r)
                  clearCart()
                }}
              />
              <button className="btn btn-primary btn-block" disabled title="Only gift certificates can pay for now">
                Card checkout (coming soon)
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  )
}
