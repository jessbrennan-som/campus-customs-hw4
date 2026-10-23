import { Link } from 'react-router-dom'
import { api, type Product } from '../api'
import CollegeMarquee from '../components/CollegeMarquee'
import ProductCard from '../components/ProductCard'
import { useFetch } from '../useFetch'

// Show one fan favorite from each of four popular kinds of garment.
const FEATURED_TYPES = ['pullover hoodie', 'crewneck sweatshirt', 'short-sleeve t-shirt', 'quarter-zip pullover']

function pickFeatured(products: Product[]): Product[] {
  return FEATURED_TYPES.flatMap((type) => {
    const best = products.filter((p) => p.garment_type === type && p.total_stock > 0)[0]
    return best ? [best] : []
  })
}

export default function Home() {
  const { data, error, loading } = useFetch(api.products, 'all')

  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-inner">
          <p className="eyebrow">Campus Customs · Yale University</p>
          <h1 id="hero-title">Lux et Veritas meets swagger &amp; pride</h1>
          <p className="hero-sub">where generations of Yalies go for their Bulldog Blues</p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-light btn-large">
              Shop the collection
            </Link>
            <Link to="/about" className="btn btn-outline-light btn-large">
              Our story
            </Link>
          </div>
        </div>
      </section>

      <CollegeMarquee />

      <section className="section" aria-labelledby="featured-title">
        <div className="container">
          <div className="section-head">
            <h2 id="featured-title">Fan favorites</h2>
            <Link to="/products" className="text-link">
              See all products →
            </Link>
          </div>
          {loading && <p className="status">Loading the shelves…</p>}
          {error && <p className="status error">We couldn't load the products. Is the backend running? ({error})</p>}
          {data && (
            <div className="product-grid four">
              {pickFeatured(data).map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="motto-banner" aria-label="Our motto">
        <div className="motto-banner-inner">
          <p className="motto-big">Lux et Veritas</p>
          <p className="motto-small">Light and Truth</p>
        </div>
      </section>
    </>
  )
}
