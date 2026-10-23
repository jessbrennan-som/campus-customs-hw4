import { useEffect, useRef, useState } from 'react'

const SEEN = 'cc-doors-opened' // the doors open once per browser tab, not on every page

// One wrought-iron gate leaf, drawn in SVG: a frame, spear-topped bars, scrollwork, rivets and a ring handle.
function Leaf({ side }: { side: 'left' | 'right' }) {
  const bars = [30, 75, 120, 165, 210, 255]
  return (
    <svg className={`door-leaf ${side}`} viewBox="0 0 300 600" preserveAspectRatio="none" aria-hidden="true">
      <rect width="300" height="600" fill="#15181d" />
      <rect x="6" y="6" width="288" height="588" fill="none" stroke="#3a4048" strokeWidth="6" />
      {bars.map((x) => (
        <g key={x}>
          <path d={`M${x} 590V70`} stroke="#0b0d10" strokeWidth="9" />
          <path d={`M${x} 590V70`} stroke="#4b525c" strokeWidth="2" transform="translate(-2 0)" />
          <path d={`M${x} 40l-11 32h22z`} fill="#0b0d10" stroke="#4b525c" strokeWidth="1.5" />
          <circle cx={x} cy="78" r="5" fill="#0b0d10" stroke="#4b525c" strokeWidth="1.5" />
        </g>
      ))}
      {[150, 330, 500].map((y) => (
        <path key={y} d={`M6 ${y}H294`} stroke="#0b0d10" strokeWidth="11" />
      ))}
      {[150, 330, 500].map((y) => (
        <path key={`h${y}`} d={`M6 ${y - 3}H294`} stroke="#4b525c" strokeWidth="1.5" />
      ))}
      {/* scrolls between the bars on the middle rail */}
      {[52, 142, 232].map((x) => (
        <g key={x} fill="none" stroke="#0b0d10" strokeWidth="6" strokeLinecap="round">
          <path d={`M${x} 330c0-26 30-26 30 0s-22 22-22 6`} />
          <path d={`M${x + 38} 330c0 26-30 26-30 0`} />
        </g>
      ))}
      {[52, 142, 232].map((x) => (
        <path key={`s${x}`} d={`M${x} 330c0-26 30-26 30 0s-22 22-22 6`} fill="none" stroke="#4b525c" strokeWidth="1.2" />
      ))}
      {[28, 272].flatMap((x) => [20, 150, 330, 500, 580].map((y) => <circle key={`${x}${y}`} cx={x} cy={y} r="4" fill="#4b525c" />))}
      <circle cx={side === 'left' ? 278 : 22} cy="330" r="16" fill="none" stroke="#8a7a4a" strokeWidth="5" />
    </svg>
  )
}

// When someone first arrives, a pair of wrought-iron gates stands closed across the screen with the Campus Customs
// motto. Choosing "Enter the store" (or waiting a few seconds) swings them open to reveal the shop.
export default function EntryDoors() {
  const [phase, setPhase] = useState<'closed' | 'opening' | 'gone'>(() => (sessionStorage.getItem(SEEN) ? 'gone' : 'closed'))
  const button = useRef<HTMLButtonElement>(null)
  const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const open = () => {
    sessionStorage.setItem(SEEN, '1')
    setPhase('opening')
  }

  useEffect(() => {
    if (phase !== 'closed') return
    button.current?.focus()
    const auto = setTimeout(open, 6000)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && open()
    window.addEventListener('keydown', onKey)
    return () => {
      clearTimeout(auto)
      window.removeEventListener('keydown', onKey)
    }
  }, [phase])

  useEffect(() => {
    if (phase !== 'opening') return
    const done = setTimeout(() => setPhase('gone'), reduced ? 200 : 2200)
    return () => clearTimeout(done)
  }, [phase, reduced])

  if (phase === 'gone') return null
  return (
    <div className={`doors ${phase}`} role="dialog" aria-label="Welcome to Campus Customs" aria-modal="true">
      <div className="doors-stage">
        <Leaf side="left" />
        <Leaf side="right" />
      </div>
      <div className="doors-plaque">
        <p className="doors-eyebrow">Campus Customs · Since 1975</p>
        <p className="doors-motto">Lux et Veritas</p>
        <button ref={button} className="btn btn-light btn-large" onClick={open}>
          Enter the store
        </button>
      </div>
    </div>
  )
}
