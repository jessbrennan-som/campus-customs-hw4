import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type Product } from '../api'
import { Crest } from '../components/Art'
import ProductCard from '../components/ProductCard'
import { useFetch } from '../useFetch'

type Sort = 'name' | 'price-low' | 'price-high'

function matches(p: Product, words: string[]): boolean {
  const text = [p.name, p.garment_type, p.description, ...p.colors, ...p.search_tags].join(' ').toLowerCase()
  return words.every((w) => text.includes(w))
}

export default function Products() {
  // The two dropdowns live in the address (/products?category=hoodies&shop=berkeley), so a filtered page can be shared or bookmarked.
  const [params, setParams] = useSearchParams()
  const category = params.get('category') ?? ''
  const collection = params.get('shop') ?? ''
  const products = useFetch(() => api.products(category, collection), `${category}|${collection}`)
  const filters = useFetch(api.browseFilters, 'filters')
  const [search, setSearch] = useState('')
  const choose = (key: 'category' | 'shop') => (value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }
  const [sort, setSort] = useState<Sort>('name')

  const shown = useMemo(() => {
    const words = search.toLowerCase().split(/\s+/).filter(Boolean)
    const list = (products.data ?? []).filter((p) => matches(p, words))
    if (sort === 'price-low') list.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    if (sort === 'price-high') list.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    return list
  }, [products.data, search, sort])

  return (
    <div className="products-page">
      <Crest className="products-watermark" />
      <section className="page-banner products-banner" aria-labelledby="products-title">
        <Crest className="products-watermark banner" />
        <div className="page-banner-inner">
          <p className="eyebrow">Campus Customs</p>
          <h1 id="products-title">Products</h1>
          <p className="products-banner-sub">Official Yale gear for every Bulldog: hoodies, crewnecks, tees and more.</p>
        </div>
      </section>
      <div className="container page">

      <div className="toolbar" role="search">
        <label className="field grow">
          <span>Search</span>
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Try “navy hoodie” or “Berkeley”" />
        </label>
        <label className="field">
          <span>Category</span>
          <select value={category} onChange={(e) => choose('category')(e.target.value)}>
            <option value="">All categories</option>
            {(filters.data?.categories ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.label} ({c.count})
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Shop for</span>
          <select value={collection} onChange={(e) => choose('shop')(e.target.value)}>
            <option value="">Everyone &amp; everything</option>
            {(filters.data?.groups ?? []).map((g) => (
              <optgroup key={g.label} label={g.label}>
                {g.options.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label} ({o.count})
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Sort by</span>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
            <option value="name">Name</option>
            <option value="price-low">Price: low to high</option>
            <option value="price-high">Price: high to low</option>
          </select>
        </label>
      </div>

      {products.loading && <p className="status">Loading the shelves…</p>}
      {products.error && <p className="status error">We couldn't load the products. Is the backend running? ({products.error})</p>}
      {products.data && (
        <>
          <p className="result-count" aria-live="polite">
            Showing {shown.length} {category || collection ? '' : `of ${products.data.length} `}products
          </p>
          {shown.length === 0 ? (
            <div className="empty">
              <p>No products match that search.</p>
              <button
                className="btn btn-primary"
                onClick={() => {
                  setSearch('')
                  setParams({})
                }}
              >
                Clear filters
              </button>
            </div>
          ) : (
            <div className="product-grid">
              {shown.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          )}
        </>
      )}
      </div>
    </div>
  )
}
