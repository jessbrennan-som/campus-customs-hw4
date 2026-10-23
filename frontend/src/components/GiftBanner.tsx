import { useState } from 'react'
import { Link } from 'react-router-dom'
import { GIFT_DISCOUNT_PERCENT } from '../api'

const KEY = 'cc-gift-banner-closed'

// A thin banner above the header on every page: paying with a gift certificate takes 10% off.
// "×" hides it for the rest of this visit.
export default function GiftBanner() {
  const [closed, setClosed] = useState(() => sessionStorage.getItem(KEY) === '1')
  if (closed) return null
  return (
    <aside className="gift-banner" aria-label="Gift certificate offer">
      <p>
        <strong>Give the gift of Yale gear:</strong> everything bought with a gift certificate is {GIFT_DISCOUNT_PERCENT}% off.{' '}
        <Link to="/gift-certificates">Send one to a student →</Link>
      </p>
      <button
        className="gift-banner-close"
        aria-label="Hide this offer"
        onClick={() => {
          sessionStorage.setItem(KEY, '1')
          setClosed(true)
        }}
      >
        ×
      </button>
    </aside>
  )
}
