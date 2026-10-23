import { Link } from 'react-router-dom'

// The residential colleges and professional schools, each linking to its page of gear in the Products "Shop for" menu.
// (ids match /api/browse-filters)
const COLLEGES = [
  ['benjamin-franklin', 'Benjamin Franklin'], ['berkeley', 'Berkeley'], ['branford', 'Branford'], ['davenport', 'Davenport'],
  ['grace-hopper', 'Grace Hopper'], ['jonathan-edwards', 'Jonathan Edwards'], ['morse', 'Morse'], ['pierson', 'Pierson'],
  ['saybrook', 'Saybrook'], ['timothy-dwight', 'Timothy Dwight'], ['trumbull', 'Trumbull'],
]
const SCHOOLS = [
  ['architecture', 'Architecture'], ['art', 'Art'], ['divinity', 'Divinity'], ['engineering', 'Engineering'],
  ['forestry', 'Forestry & Environment'], ['law', 'Law'], ['management', 'Management'], ['medicine', 'Medicine'],
  ['music', 'Music'], ['nursing', 'Nursing'], ['public-health', 'Public Health'],
]

function Shield() {
  return (
    <svg className="marquee-shield" viewBox="0 0 20 24" aria-hidden="true">
      <path d="M2 2h16v10c0 7-8 10-8 10S2 19 2 12z" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10 7v9M6 9h8" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  )
}

function Row({ hidden }: { hidden?: boolean }) {
  const item = (kind: string, [id, label]: string[]) => (
    <li key={`${kind}${id}`}>
      <Link to={`/products?shop=${id}`} tabIndex={hidden ? -1 : undefined}>
        <Shield />
        <span className="marquee-kind">{kind}</span> {label}
      </Link>
    </li>
  )
  return (
    <ul className="marquee-row" aria-hidden={hidden || undefined}>
      {COLLEGES.map((c) => item('College', c))}
      {SCHOOLS.map((s) => item('School', s))}
    </ul>
  )
}

// A slow scrolling ribbon so every student can find their own college or school. Hover or focus pauses it.
export default function CollegeMarquee() {
  return (
    <section className="marquee" aria-label="Shop by Yale college or school">
      <div className="marquee-track">
        <Row />
        <Row hidden />
      </div>
    </section>
  )
}
