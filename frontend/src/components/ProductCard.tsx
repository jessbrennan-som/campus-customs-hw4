import { Link } from 'react-router-dom'
import { imageSrc, money, type Product } from '../api'

// The same card is used on the Products page, in "If you like this", and for the chat's results on the page.
type CardProduct = Pick<Product, 'product_id' | 'name' | 'garment_type' | 'price' | 'image_url'>
type Props = { product: CardProduct; note?: string; info?: string }

// One product tile: the photo and the title both open the full product page, and so does the button.
export default function ProductCard({ product, note, info }: Props) {
  const to = `/products/${product.product_id}`
  return (
    <article className="product-card">
      <Link to={to} className="product-card-photo" aria-label={`View ${product.name}`}>
        <img src={imageSrc(product)} alt={product.name} loading="lazy" />
      </Link>
      <div className="product-card-body">
        <p className="product-card-type">{product.garment_type}</p>
        <h3 className="product-card-title">
          <Link to={to}>{product.name}</Link>
        </h3>
        <p className="product-card-price">{money(product.price)}</p>
        {info && <p className="product-card-info">{info}</p>}
        {note && <p className="product-card-note">{note}</p>}
        <Link to={to} className="btn btn-primary btn-block">
          View product
        </Link>
      </div>
    </article>
  )
}
