import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, imageSrc, LOW_STOCK, money, type SizeStock } from '../api'
import ProductCard from '../components/ProductCard'
import { useShop } from '../store'
import { useFetch } from '../useFetch'

const MAX_PER_ORDER = 10

function stockLabel(s: SizeStock): string {
  if (s.quantity === 0) return 'Sold out'
  if (s.quantity <= LOW_STOCK) return `Only ${s.quantity} left`
  return `${s.quantity} in stock`
}

export default function ProductPage() {
  const { id = '' } = useParams()
  const { data: product, error, loading } = useFetch(() => api.product(id), id)
  const [size, setSize] = useState<string | null>(null)
  const [quantity, setQuantity] = useState(1)
  const [needSize, setNeedSize] = useState(false)
  const [added, setAdded] = useState(false)
  const sizeGroup = useRef<HTMLDivElement>(null)
  const { addItem, setCartOpen, setChatOpen, setSelectedSize } = useShop()

  // "If you like this" suggestions; they lean toward the size you picked
  const similar = useFetch(() => api.similar(id, size ?? undefined), `${id}|${size ?? ''}`)

  // tell the chatbot which size is picked, and clear it when the customer leaves this page
  useEffect(() => {
    setSelectedSize(size)
    return () => setSelectedSize(null)
  }, [size, setSelectedSize])

  // a new product starts from scratch
  useEffect(() => {
    setSize(null)
    setQuantity(1)
    setNeedSize(false)
    setAdded(false)
    window.scrollTo({ top: 0 })
  }, [id])

  if (loading) return <p className="container status page">Loading…</p>
  if (error === 'not-found')
    return (
      <div className="container page empty">
        <h1>We couldn't find that product</h1>
        <Link to="/products" className="btn btn-primary">
          Back to all products
        </Link>
      </div>
    )
  if (error || !product) return <p className="container status error page">We couldn't load this product. Is the backend running? ({error})</p>

  const chosen = product.sizes.find((s) => s.size === size)
  const maxQty = chosen ? Math.min(chosen.quantity, MAX_PER_ORDER) : MAX_PER_ORDER
  const soldOut = product.total_stock === 0

  function pickSize(s: SizeStock) {
    setSize(s.size)
    setNeedSize(false)
    setAdded(false)
    setQuantity((q) => Math.min(q, Math.min(s.quantity, MAX_PER_ORDER)))
  }

  function addToCart() {
    if (!product) return
    if (!chosen) {
      setNeedSize(true)
      sizeGroup.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    addItem({
      productId: product.product_id,
      name: product.name,
      size: chosen.size,
      quantity,
      price: product.price,
      imageUrl: product.image_url,
    })
    setAdded(true)
  }

  return (
    <div className="container page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link> / <Link to="/products">Products</Link> / <span aria-current="page">{product.name}</span>
      </nav>

      <div className="product-layout">
        <div className="product-photo">
          <img src={imageSrc(product)} alt={product.name} />
        </div>

        <div className="product-info">
          <p className="eyebrow dark">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price">{money(product.price)}</p>
          <p className={`availability ${soldOut ? 'out' : ''}`}>
            <span className="dot" aria-hidden="true" />
            {soldOut ? 'Currently sold out' : `In stock · ${product.total_stock} available across all sizes`}
          </p>

          <p className="description">{product.description}</p>

          <p className="color-line">
            <strong>{product.colors.length > 1 ? 'Colors' : 'Color'}:</strong>{' '}
            {product.colors.length ? product.colors.join(', ') : 'see photo'}
          </p>

          <div ref={sizeGroup} className={`size-block ${needSize ? 'needs-attention' : ''}`}>
            <div className="size-head">
              <strong>Size</strong>
              <button className="link-button" onClick={() => setChatOpen(true)}>
                Need help with sizing?
              </button>
            </div>
            <div className="size-grid" role="radiogroup" aria-label="Choose a size">
              {product.sizes.map((s) => (
                <button
                  key={s.size}
                  role="radio"
                  aria-checked={size === s.size}
                  disabled={s.quantity === 0}
                  className={`size-option ${size === s.size ? 'selected' : ''} ${s.quantity > 0 && s.quantity <= LOW_STOCK ? 'low' : ''}`}
                  onClick={() => pickSize(s)}
                >
                  <span className="size-name">{s.size}</span>
                  <span className="size-stock">{stockLabel(s)}</span>
                </button>
              ))}
            </div>
            {needSize && (
              <p className="field-error" role="alert">
                Please choose a size first.
              </p>
            )}
          </div>

          <div className="buy-row">
            <div className="stepper" aria-label="Quantity">
              <button onClick={() => setQuantity((q) => Math.max(1, q - 1))} disabled={quantity <= 1} aria-label="Fewer">
                −
              </button>
              <span aria-live="polite">{quantity}</span>
              <button onClick={() => setQuantity((q) => Math.min(maxQty, q + 1))} disabled={quantity >= maxQty} aria-label="More">
                +
              </button>
            </div>
            <button className="btn btn-primary btn-large add-to-cart" onClick={addToCart} disabled={soldOut}>
              {soldOut ? 'Sold out' : chosen ? `Add to cart · ${money(product.price * quantity)}` : 'Add to cart'}
            </button>
          </div>

          {added && (
            <p className="added" role="status">
              ✓ Added to your cart.{' '}
              <button className="link-button" onClick={() => setCartOpen(true)}>
                View cart
              </button>
            </p>
          )}

          <ul className="assurances">
            <li>Official Campus Customs merchandise, Yale's original licensed boutique since 1975</li>
            <li>Stock counts above are live from our inventory</li>
          </ul>

          <dl className="details">
            <div>
              <dt>Style</dt>
              <dd className="cap">{product.garment_type}</dd>
            </div>
            <div>
              <dt>Item number</dt>
              <dd>{product.product_id}</dd>
            </div>
            {product.search_tags.length > 0 && (
              <div>
                <dt>Also known as</dt>
                <dd className="tag-list">
                  {product.search_tags.map((t) => (
                    <span key={t} className="tag">
                      {t}
                    </span>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      <section className="section similar" aria-labelledby="similar-title">
        <h2 id="similar-title">If you like this, consider…</h2>
        {similar.loading && <p className="status">Finding matches…</p>}
        {similar.data && (
          <div className="product-grid three">
            {similar.data.map((p) => (
              <ProductCard key={p.product_id} product={p} note={p.reason} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
