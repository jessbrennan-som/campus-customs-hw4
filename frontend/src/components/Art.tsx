// Hand-drawn SVG artwork: the shield crest and Handsome Dan, the bulldog mascot.
// These are friendly illustrations for a class project, not Yale's official marks.

export function Crest({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 100 120" role="img" aria-label="Campus Customs crest">
      <path d="M8 6h84v56c0 38-42 52-42 52S8 100 8 62z" fill="#00356b" stroke="#ffffff" strokeWidth="4" strokeLinejoin="round" />
      <path d="M50 36c-9-6-22-6-30-2v36c8-4 21-4 30 2 9-6 22-6 30-2V34c-8-4-21-4-30 2z" fill="#ffffff" />
      <path d="M50 36v36" stroke="#00356b" strokeWidth="2.5" />
      <g stroke="#63aaff" strokeWidth="2" strokeLinecap="round">
        <path d="M27 46c5-1 10-1 17 1M27 54c5-1 10-1 17 1M27 62c5-1 10-1 17 1" />
        <path d="M73 46c-5-1-10-1-17 1M73 54c-5-1-10-1-17 1M73 62c-5-1-10-1-17 1" />
      </g>
      <path d="M22 84h56l-6 9 6 9H22l6-9z" fill="#ffffff" stroke="#00356b" strokeWidth="1.5" strokeLinejoin="round" />
      <text x="50" y="97" textAnchor="middle" fontSize="8.5" fontWeight="700" fontFamily="Georgia, serif" letterSpacing="0.6" fill="#00356b">
        LUX ET VERITAS
      </text>
    </svg>
  )
}

const INK = '#2b2118'
const FUR = '#f3e8d4'
const MUZZLE = '#fbf2e2'
const BROWN = '#a8693f'

// Handsome Dan, a tough-looking cartoon English bulldog: heavy brow, wide jaw, underbite fangs, a
// spiked collar and a Yale-blue sweater. pose="fist" raises a fist; the default is just head and shoulders.
export type Outfit = 'sweater' | 'hoodie' | 'tee' | 'quarterzip' | 'hockey'

const BODY = 'M10 250C10 192 56 168 120 168s110 24 110 82z'

// What Dan has on, drawn from the shoulders down. Each outfit matches a real product in the shop.
function Outfit({ outfit }: { outfit: Outfit }) {
  const shirt = (fill: string) => <path d={BODY} fill={fill} stroke={INK} strokeWidth="3.5" strokeLinejoin="round" />
  const word = (y: number, size: number, text: string, fill = '#ffffff') => (
    <text x="120" y={y} textAnchor="middle" fontSize={size} fontWeight="700" fontFamily="Georgia, serif" letterSpacing="1" fill={fill}>
      {text}
    </text>
  )
  if (outfit === 'hoodie' || outfit === 'hockey')
    return (
      <g>
        {/* the hood bunched up behind his neck */}
        <path d="M40 190C46 168 84 160 120 160s74 8 80 30c-30-10-130-10-160 0z" fill="#6f7886" stroke={INK} strokeWidth="3.5" strokeLinejoin="round" />
        {shirt('#9aa3b0')}
        <path d="M104 190v34M136 190v34" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" />
        <path d="M96 232h48" stroke="#6f7886" strokeWidth="3" strokeLinecap="round" />
        {outfit === 'hoodie' ? (
          word(240, 34, 'YALE', '#00356b')
        ) : (
          <>
            {word(236, 22, 'YALE', '#00356b')}
            {word(248, 9, 'HOCKEY', '#00356b')}
            {/* a hockey stick over his shoulder */}
            <path d="M206 250L176 156" stroke={INK} strokeWidth="9" strokeLinecap="round" />
            <path d="M206 250L176 156" stroke="#c89a5b" strokeWidth="5" strokeLinecap="round" />
            <path d="M176 156l-20-4" stroke={INK} strokeWidth="9" strokeLinecap="round" />
            <path d="M176 156l-20-4" stroke="#c89a5b" strokeWidth="5" strokeLinecap="round" />
          </>
        )}
      </g>
    )
  if (outfit === 'tee')
    return (
      <g>
        {/* bare furry arms sticking out of short sleeves */}
        <ellipse cx="22" cy="226" rx="20" ry="26" fill={FUR} stroke={INK} strokeWidth="3.5" />
        <ellipse cx="218" cy="226" rx="20" ry="26" fill={FUR} stroke={INK} strokeWidth="3.5" />
        {shirt('#8a8f98')}
        <path d="M12 214c12 6 24 6 34-2M228 214c-12 6-24 6-34-2" fill="none" stroke={INK} strokeWidth="3" strokeLinecap="round" />
        <path d="M92 172c8 14 48 14 56 0" fill="none" stroke="#6f7480" strokeWidth="5" strokeLinecap="round" />
        {word(222, 16, 'BOOLA', '#ffffff')}
        {word(240, 16, 'BOOLA', '#ffffff')}
      </g>
    )
  if (outfit === 'quarterzip')
    return (
      <g>
        {shirt('#00356b')}
        <path d="M70 178c10 20 90 20 100 0" fill="none" stroke="#63aaff" strokeWidth="9" strokeLinecap="round" />
        <path d="M120 188v34" stroke="#d7dbe3" strokeWidth="4" strokeLinecap="round" />
        <rect x="116" y="220" width="8" height="10" rx="2" fill="#d7dbe3" stroke={INK} strokeWidth="1.5" />
        <path d="M30 222h40M170 222h40" stroke="#63aaff" strokeWidth="4" strokeLinecap="round" />
        {word(246, 14, 'BERKELEY')}
      </g>
    )
  return (
    <g>
      {shirt('#00356b')}
      {word(244, 40, 'Y')}
    </g>
  )
}

export function Bulldog({ className, pose = 'bust', outfit = 'sweater' }: { className?: string; pose?: 'bust' | 'fist'; outfit?: Outfit }) {
  return (
    <svg className={className} viewBox="0 0 240 250" role="img" aria-label="Handsome Dan, the Yale bulldog mascot">
      <Outfit outfit={outfit} />

      {/* raised fist */}
      {pose === 'fist' && (
        <g>
          <path d="M204 226Q232 196 218 156" fill="none" stroke={INK} strokeWidth="31" strokeLinecap="round" />
          <path d="M204 226Q232 196 218 156" fill="none" stroke="#00356b" strokeWidth="25" strokeLinecap="round" />
          <rect x="201" y="128" width="34" height="32" rx="12" fill={FUR} stroke={INK} strokeWidth="3.5" />
          <path d="M212 132v10M223 132v10" stroke={INK} strokeWidth="2.5" strokeLinecap="round" />
        </g>
      )}

      {/* spiked collar, behind the chin */}
      <path d="M58 184Q120 224 182 184" fill="none" stroke={INK} strokeWidth="19" strokeLinecap="round" />
      <path d="M58 184Q120 224 182 184" fill="none" stroke="#3a3a42" strokeWidth="13" strokeLinecap="round" />
      {[
        [70, 191],
        [89, 198],
        [108, 203],
        [120, 204],
        [132, 203],
        [151, 198],
        [170, 191],
      ].map(([x, y]) => (
        <path key={x} d={`M${x - 4.5} ${y - 2}L${x} ${y + 9}L${x + 4.5} ${y - 2}z`} fill="#d7dbe3" stroke={INK} strokeWidth="1.8" strokeLinejoin="round" />
      ))}

      {/* ears: rose ears with a nick taken out of one */}
      <g>
        <path d="M44 94C24 74 26 44 46 28 70 30 90 50 96 80z" fill="#8a5a36" stroke={INK} strokeWidth="3.5" strokeLinejoin="round" />
        <path d="M50 82C38 68 38 52 48 40 62 44 76 58 82 74z" fill="#6e4526" />
        <path d="M33 52l9 5" stroke={FUR} strokeWidth="2.5" strokeLinecap="round" />
      </g>
      <g transform="translate(240 0) scale(-1 1)">
        <path d="M44 94C24 74 26 44 46 28 70 30 90 50 96 80z" fill="#8a5a36" stroke={INK} strokeWidth="3.5" strokeLinejoin="round" />
        <path d="M50 82C38 68 38 52 48 40 62 44 76 58 82 74z" fill="#6e4526" />
      </g>

      {/* big square head */}
      <path d="M44 112C40 70 76 46 120 46s80 24 76 66c4 48-28 80-76 80s-80-32-76-80z" fill={FUR} stroke={INK} strokeWidth="3.5" strokeLinejoin="round" />
      {/* brown patch over one eye */}
      <path d="M52 98C54 68 88 58 106 78c8 14-4 34-24 34-18 2-32-6-30-14z" fill={BROWN} opacity="0.95" />
      {/* forehead wrinkles */}
      <path d="M98 61Q120 53 142 61M106 69Q120 64 134 69" fill="none" stroke="#cdbb9f" strokeWidth="2.5" strokeLinecap="round" />

      {/* heavy jowls, muzzle */}
      <ellipse cx="72" cy="150" rx="30" ry="24" fill={MUZZLE} stroke={INK} strokeWidth="3" />
      <ellipse cx="168" cy="150" rx="30" ry="24" fill={MUZZLE} stroke={INK} strokeWidth="3" />
      <ellipse cx="120" cy="142" rx="50" ry="34" fill={MUZZLE} stroke={INK} strokeWidth="3" />

      {/* eyes, narrowed under a heavy brow */}
      <ellipse cx="92" cy="106" rx="11" ry="8.5" fill="#ffffff" stroke={INK} strokeWidth="2.5" />
      <ellipse cx="148" cy="106" rx="11" ry="8.5" fill="#ffffff" stroke={INK} strokeWidth="2.5" />
      <circle cx="95" cy="108" r="5" fill={INK} />
      <circle cx="145" cy="108" r="5" fill={INK} />
      <circle cx="96.5" cy="106.5" r="1.6" fill="#ffffff" />
      <circle cx="146.5" cy="106.5" r="1.6" fill="#ffffff" />
      <path d="M64 87L113 103M176 87L127 103" stroke={INK} strokeWidth="10" strokeLinecap="round" />

      {/* wide flat nose */}
      <path d="M96 124c0-12 48-12 48 0 0 14-14 22-24 22s-24-8-24-22z" fill="#1b1b1f" />
      <ellipse cx="109" cy="120" rx="8" ry="3" fill="#ffffff" opacity="0.5" />

      {/* smirk, underbite and fangs */}
      <path d="M120 146v10M120 156c-10 12-26 12-36 4M120 156c10 12 26 12 36 4" fill="none" stroke={INK} strokeWidth="3.5" strokeLinecap="round" />
      <path d="M82 162Q120 194 158 162Q158 188 120 192Q82 188 82 162z" fill={FUR} stroke={INK} strokeWidth="3" strokeLinejoin="round" />
      <path d="M94 168l5-24 9 24zM132 168l9-24 5 24z" fill="#ffffff" stroke={INK} strokeWidth="2.2" strokeLinejoin="round" />

      {/* a battle scar on one cheek */}
      <path d="M152 112L172 134M158 124l7-5M164 131l7-5M156 116l5-7" fill="none" stroke="#7a3b2e" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  )
}
