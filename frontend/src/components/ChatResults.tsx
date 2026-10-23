import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useShop } from '../store'
import { NOT_WANTED } from './ChatWidget'
import ProductCard from './ProductCard'

// The product cards the chatbot puts on whatever page the customer is looking at.
// They come from POST /api/chat (the `results` field): the API reads every card's name, price, photo and
// description from the database, and this component only draws them. Each card links to the product's full page.
//
// On a product's own page the results shrink to a slim bar, so the product stays at the top of the screen
// (a customer who just clicked a card should see that product, not the list again). "Show results" opens the
// list again, and new results from the chat always open it.
export default function ChatResults() {
  const { results, setResults, say } = useShop()
  const { pathname } = useLocation()
  const onProductPage = /^\/products\/[^/]+/.test(pathname)
  const [open, setOpen] = useState(true)
  const section = useRef<HTMLElement>(null)

  useEffect(() => setOpen(true), [results]) // new results from the chat: show them in full
  useEffect(() => {
    if (onProductPage) setOpen(false) // arriving on a product page: tuck the list away
  }, [pathname, onProductPage])

  const compact = onProductPage && !open
  useEffect(() => {
    if (results && !compact) section.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [results, compact])

  if (!results) return null

  if (compact)
    return (
      <section ref={section} className="chat-results compact" aria-label="Results from Handsome Dan">
        <div className="container compact-bar">
          <p>
            <strong>Handsome Dan found:</strong> {results.title} <span>({results.items.length} items)</span>
          </p>
          <div className="compact-actions">
            <button className="btn btn-secondary" onClick={() => setOpen(true)}>
              Show results
            </button>
            <button className="link-button" onClick={() => setResults(null)}>
              Clear
            </button>
          </div>
        </div>
      </section>
    )

  return (
    <section ref={section} className="chat-results" aria-labelledby="chat-results-title">
      <div className="container">
        <div className="chat-results-head">
          <div>
            <p className="eyebrow dark">Handsome Dan found these for you</p>
            <h2 id="chat-results-title">{results.title}</h2>
          </div>
          <div className="compact-actions">
            <button
              className="btn btn-secondary"
              onClick={() => say(NOT_WANTED)}
              title="Tell Handsome Dan so he can fix it and learn from it"
            >
              Not what I wanted
            </button>
            <button className="btn btn-secondary" onClick={() => setResults(null)}>
              Clear
            </button>
          </div>
        </div>
        <div className="product-grid">
          {results.items.map((item) => (
            <ProductCard key={item.product_id} product={item} info={item.short_info} note={item.in_stock ? undefined : 'Sold out right now'} />
          ))}
        </div>
      </div>
    </section>
  )
}
