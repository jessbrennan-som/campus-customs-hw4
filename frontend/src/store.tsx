import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { SearchResults } from './api'

// Two small pieces of shared state: the shopping cart and whether the chat panel is open.

export type CartItem = {
  productId: string
  name: string
  size: string
  quantity: number
  price: number
  imageUrl: string
}

type Shop = {
  items: CartItem[]
  count: number
  subtotal: number
  addItem: (item: CartItem) => void
  removeItem: (productId: string, size: string) => void
  clearCart: () => void
  cartOpen: boolean
  setCartOpen: (open: boolean) => void
  chatOpen: boolean
  setChatOpen: (open: boolean) => void
  results: SearchResults | null // product cards the chatbot put on the page
  setResults: (results: SearchResults | null) => void
  say: (text: string) => void // something to send to the chatbot for the customer (opens the chat)
  outbox: string | null
  clearOutbox: () => void
  selectedSize: string | null // the size picked on the product page being viewed (the chatbot is told)
  setSelectedSize: (size: string | null) => void
}

const ShopContext = createContext<Shop | null>(null)
const STORAGE_KEY = 'campus-customs-cart'

function loadCart(): CartItem[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? (JSON.parse(saved) as CartItem[]) : []
  } catch {
    return []
  }
}

export function ShopProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(loadCart)
  const [cartOpen, setCartOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [results, setResults] = useState<SearchResults | null>(null)
  const [selectedSize, setSelectedSize] = useState<string | null>(null)
  const [outbox, setOutbox] = useState<string | null>(null)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }, [items])

  const addItem = useCallback((item: CartItem) => {
    setItems((current) => {
      const same = current.find((i) => i.productId === item.productId && i.size === item.size)
      if (!same) return [...current, item]
      return current.map((i) => (i === same ? { ...i, quantity: i.quantity + item.quantity } : i))
    })
  }, [])

  const removeItem = useCallback((productId: string, size: string) => {
    setItems((current) => current.filter((i) => !(i.productId === productId && i.size === size)))
  }, [])

  const say = useCallback((text: string) => {
    setOutbox(text)
    setChatOpen(true)
  }, [])
  const clearOutbox = useCallback(() => setOutbox(null), [])
  const clearCart = useCallback(() => setItems([]), [])

  const value = useMemo<Shop>(
    () => ({
      items,
      count: items.reduce((n, i) => n + i.quantity, 0),
      subtotal: items.reduce((sum, i) => sum + i.quantity * i.price, 0),
      addItem,
      removeItem,
      clearCart,
      cartOpen,
      setCartOpen,
      chatOpen,
      setChatOpen,
      results,
      setResults,
      say,
      outbox,
      clearOutbox,
      selectedSize,
      setSelectedSize,
    }),
    [items, addItem, removeItem, clearCart, cartOpen, chatOpen, results, selectedSize, say, outbox, clearOutbox],
  )
  return <ShopContext.Provider value={value}>{children}</ShopContext.Provider>
}

export function useShop(): Shop {
  const shop = useContext(ShopContext)
  if (!shop) throw new Error('useShop must be used inside <ShopProvider>')
  return shop
}
