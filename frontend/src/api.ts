// Talks to the FastAPI backend. In development Vite forwards /api and /images to it.
// When the site is deployed somewhere the backend lives elsewhere, set VITE_API_URL.

const API_BASE: string = import.meta.env.VITE_API_URL ?? ''

export type SizeStock = { size: string; quantity: number }

export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  price: number
  image_url: string
  sizes: SizeStock[]
  total_stock: number
}

export type SimilarProduct = Product & { reason: string }

export type GarmentTypeCount = { garment_type: string; count: number }

// The Products page dropdowns: categories (Hoodies, T-shirts...) and "shop for" groups (colleges, schools, sports...).
export type BrowseOption = { id: string; label: string; count: number }
export type BrowseFilters = { categories: BrowseOption[]; groups: { label: string; options: BrowseOption[] }[] }

// At or below this many left, we tell the shopper stock is running low.
export const LOW_STOCK = 5

async function get<T>(path: string): Promise<T> {
  const res = await fetch(API_BASE + path)
  if (!res.ok) throw new Error(res.status === 404 ? 'not-found' : `The shop is having trouble (error ${res.status}).`)
  return res.json() as Promise<T>
}

export const api = {
  products: (category?: string, collection?: string) => {
    const query = new URLSearchParams()
    if (category) query.set('category', category)
    if (collection) query.set('collection', collection)
    return get<Product[]>(`/api/products${query.size ? `?${query}` : ''}`)
  },
  browseFilters: () => get<BrowseFilters>('/api/browse-filters'),
  product: (id: string) => get<Product>(`/api/products/${encodeURIComponent(id)}`),
  similar: (id: string, size?: string) =>
    get<SimilarProduct[]>(`/api/products/${encodeURIComponent(id)}/similar${size ? `?size=${encodeURIComponent(size)}` : ''}`),
  garmentTypes: () => get<GarmentTypeCount[]>('/api/garment-types'),
}

// Photo addresses carry a ?v= number so a changed photo is never served from the browser's old cache.
// (Carts saved before that existed get a one-time version so they pick up the new photos too.)
// ---------- accounts ----------
export type User = { id: number; first_name: string; last_name: string; email: string }

// An error from the API, with a message that is fine to show the shopper. `rules` lists any password rules broken.
export class ApiError extends Error {
  status: number
  rules: string[]
  constructor(status: number, message: string, rules: string[] = []) {
    super(message)
    this.status = status
    this.rules = rules
  }
}

async function send<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  const res = await fetch(API_BASE + path, {
    method,
    credentials: 'include', // sends and receives the login cookie
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  }).catch(() => {
    throw new ApiError(0, "We couldn't reach the shop. Is the backend running?")
  })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data?.detail
    if (d && typeof d === 'object' && !Array.isArray(d)) throw new ApiError(res.status, d.message ?? 'Something went wrong.', d.rules ?? [])
    if (Array.isArray(d)) throw new ApiError(res.status, String(d[0]?.msg ?? 'Please check what you typed.').replace(/^Value error, /, ''))
    throw new ApiError(res.status, typeof d === 'string' ? d : 'Something went wrong. Please try again.')
  }
  return data as T
}

export type NewAccount = { first_name: string; last_name: string; email: string; password: string; confirm_password: string }

export const accounts = {
  me: () => send<User>('GET', '/api/auth/me').catch((e: ApiError) => (e.status === 401 ? null : Promise.reject(e))),
  register: (a: NewAccount) => send<User>('POST', '/api/auth/register', a),
  login: (email: string, password: string) => send<User>('POST', '/api/auth/login', { email, password }),
  logout: () => send<void>('POST', '/api/auth/logout'),
  forgotPassword: (email: string) => send<{ message: string }>('POST', '/api/auth/forgot-password', { email }),
  changePassword: (current_password: string, password: string, confirm_password: string) =>
    send<{ message: string }>('POST', '/api/auth/change-password', { current_password, password, confirm_password }),
  resetPassword: (token: string, password: string, confirm_password: string) =>
    send<{ message: string }>('POST', '/api/auth/reset-password', { token, password, confirm_password }),
}

// ---------- chatbot ----------
// The contract for chat search: the chatbot's reply, plus (in `results`) the product cards to show on the page.
// Every field of every card is read from the database by the API; `product_id` opens /products/{product_id}.
export type ProductResult = {
  product_id: string
  name: string
  garment_type: string
  price: number
  price_text: string
  image_url: string
  short_info: string
  colors: string[]
  in_stock: boolean
}
export type SearchResults = { title: string; items: ProductResult[] }
export type ChatReply = { reply: string; results: SearchResults | null; quick_replies: string[]; tools_used: string[] }
export type ChatTurn = { role: 'user' | 'assistant'; content: string }
export type FollowUp = { order_item_id: number; product_id: string; product_name: string; size: string; question: string }

// What the website tells the chatbot about the page the customer is looking at. The API checks every part of it
// against the database before the chatbot sees it.
export type PageState = { path: string; selected_size: string | null; shown_product_ids: string[] }

export const chat = {
  send: (message: string, session_id: string, page: PageState) => send<ChatReply>('POST', '/api/chat', { message, session_id, page }),
  // the chat has been quiet for a minute: Handsome Dan offers a game of Yale trivia
  idle: (session_id: string, page: PageState) => send<ChatReply>('POST', '/api/chat/idle', { session_id, page }),
  // a logged-in customer opens the chat: their earlier conversation, plus a "how did it work out?" question if one is due
  resume: () => send<{ messages: ChatTurn[]; follow_up: FollowUp | null }>('POST', '/api/chat/resume'),
}

// ---------- gift certificates ----------
export const GIFT_DISCOUNT_PERCENT = 10
export type GiftOrder = { amount: number; purchaser_name: string; purchaser_email: string; recipient_name: string; recipient_email: string; message: string }
export type GiftPurchased = { code: string; amount: number; recipient_name: string; recipient_email: string; payment_note: string }
export type GiftCartLine = { product_id: string; size: string; quantity: number }
export type QuoteLine = { product_id: string; name: string; size: string; quantity: number; unit_price: number; line_total: number }
export type GiftQuote = { lines: QuoteLine[]; subtotal: number; discount_percent: number; discount: number; total: number; balance: number; enough: boolean }
export type GiftReceipt = GiftQuote & { order_id: number; balance_remaining: number }

export const giftCards = {
  buy: (order: GiftOrder) => send<GiftPurchased>('POST', '/api/gift-cards/buy', order),
  quote: (code: string, items: GiftCartLine[]) => send<GiftQuote>('POST', '/api/gift-cards/quote', { code, items }),
  pay: (code: string, items: GiftCartLine[]) => send<GiftReceipt>('POST', '/api/checkout/gift-card', { code, items }),
}

export const imageSrc = (p: Pick<Product, 'image_url'>) => API_BASE + p.image_url + (p.image_url.includes('?') ? '' : '?v=white')

export const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
