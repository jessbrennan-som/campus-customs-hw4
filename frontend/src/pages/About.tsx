import { Link } from 'react-router-dom'
import { Bulldog } from '../components/Art'

// Handsome Dan modelling real Campus Customs gear. Each look is drawn to match a product in the shop and links to it.
const LOOKS = [
  { outfit: 'hoodie', product: 'basic-hoodie-big-yale', wearing: 'the Basic Hoodie Big Yale', caption: 'Between classes on Cross Campus', tint: 'sky' },
  { outfit: 'tee', product: 'boola-boola-t-shirt', wearing: 'the Boola Boola T-Shirt', caption: 'Game day at the Yale Bowl', tint: 'grass' },
  { outfit: 'quarterzip', product: 'berkeley-1-4-zip', wearing: 'the Berkeley Quarter-Zip', caption: 'Strolling the Berkeley College courtyard', tint: 'brick' },
  { outfit: 'hockey', product: 'yale-sports-hoodie-hockey', wearing: 'the Yale Sports Hoodie Hockey', caption: 'Cheering at Ingalls Rink', tint: 'ice' },
] as const

export default function About() {
  return (
    <>
      <section className="page-banner about-banner" aria-labelledby="about-title">
        <div className="page-banner-inner">
          <p className="eyebrow">Since 1975</p>
          <h1 id="about-title">About Us</h1>
        </div>
      </section>

      <section className="section">
        <div className="container narrow">
          <p className="lead">Campus Customs has been Yale University’s original licensed merchandise boutique since 1975!</p>
          <p className="body-large">
            We learn from YOU and grow our offerings with each generation that passes through these hallowed halls - this ain’t
            your granddaddy’s Yale sweater.
          </p>
          <Link to="/products" className="btn btn-primary btn-large">
            Shop the collection
          </Link>
        </div>
      </section>

      <section className="section students" aria-labelledby="students-title">
        <div className="container">
          <h2 id="students-title">Handsome Dan wears it best</h2>
          <p className="students-sub">Our mascot models the gear around campus. Tap a caption to shop his look.</p>
          <div className="student-grid">
            {LOOKS.map((l) => (
              <figure key={l.product} className="student">
                <div className={`student-scene ${l.tint}`}>
                  <Bulldog className="student-dan" outfit={l.outfit} />
                </div>
                <figcaption>
                  {l.caption}. <Link to={`/products/${l.product}`}>Wearing {l.wearing} →</Link>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
