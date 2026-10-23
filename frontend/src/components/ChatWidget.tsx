import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { chat, type ApiError } from '../api'
import { useAuth } from '../auth'
import { useShop } from '../store'
import { Bulldog } from './Art'

type Message = { from: 'bot' | 'me' | 'error'; text: string; shown?: number; quick?: string[] } // `shown`: cards put on the page; `quick`: answer buttons

const IDLE_MS = 60_000 // a quiet minute, then Handsome Dan offers a game of Yale trivia
export const NOT_WANTED = "These aren't what I was looking for. Some of them are the wrong kind of thing."
const OFFERED = 'cc-idle-offered' // remembered for this browser tab, so reloading the page doesn't bring a second offer

// A random id for this browser tab, so the chatbot can remember a guest's conversation during their visit.
function sessionId(): string {
  let id = sessionStorage.getItem('cc-chat-session')
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem('cc-chat-session', id)
  }
  return id
}

const greeting = (name?: string): Message => ({
  from: 'bot',
  text: name
    ? `Woof! Welcome back, ${name}. Ask me about sizes, colors or what's in stock.`
    : "Woof! I'm Handsome Dan. Ask me about sizes, colors or what's in stock.",
})

// Floating helper in the bottom-right corner: a friendly bulldog with a "Need help?" bubble.
// The panel talks to the shop chatbot (a PydanticAI agent) through POST /api/chat.
export default function ChatWidget() {
  const { chatOpen, setChatOpen, setResults, results, selectedSize, outbox, clearOutbox } = useShop()
  const { pathname } = useLocation()
  const { user, ready } = useAuth()
  const [messages, setMessages] = useState<Message[]>([greeting()])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [mayOffer, setMayOffer] = useState(() => sessionStorage.getItem(OFFERED) !== '1') // one trivia offer per quiet spell; a message from the customer re-arms it
  const bottom = useRef<HTMLDivElement>(null)

  // Whenever someone logs in or out, start from their own conversation: a logged-in customer's
  // earlier chat comes back from the server, a guest starts fresh.
  useEffect(() => {
    if (!ready) return
    setMessages([greeting(user?.first_name)])
    if (!user) return
    let cancelled = false
    chat
      .resume() // brings back their saved conversation, and asks how a past purchase worked out if that's due
      .then(({ messages: past, follow_up }) => {
        if (cancelled || past.length === 0) return
        if (follow_up) setChatOpen(true) // a "how did it work out?" question is waiting: open the chat so they see it
        setMessages([
          greeting(user.first_name),
          ...past.map<Message>((m) => ({ from: m.role === 'user' ? 'me' : 'bot', text: m.content })),
        ])
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [user?.id, ready]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, chatOpen, busy])

  const pageState = () => ({
    path: pathname,
    selected_size: pathname.startsWith('/products/') ? selectedSize : null,
    shown_product_ids: results?.items.map((i) => i.product_id) ?? [],
  })

  // Quiet for a minute (nothing typed, nothing sent): Handsome Dan offers a round of Yale trivia, once.
  useEffect(() => {
    if (!ready || !mayOffer || busy) return
    const timer = setTimeout(async () => {
      setMayOffer(false)
      sessionStorage.setItem(OFFERED, '1')
      try {
        const offer = await chat.idle(sessionId(), pageState())
        setMessages((m) => [...m, { from: 'bot', text: offer.reply, quick: offer.quick_replies }])
        setChatOpen(true)
      } catch {
        /* an offer that fails is simply skipped */
      }
    }, IDLE_MS)
    return () => clearTimeout(timer)
  }, [ready, mayOffer, busy, text, messages.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // "Not what I wanted" on the page's results sends a message for the customer
  useEffect(() => {
    if (outbox && !busy) {
      clearOutbox()
      void ask(outbox)
    }
  }, [outbox]) // eslint-disable-line react-hooks/exhaustive-deps

  async function ask(question: string) {
    if (!question || busy) return
    setMayOffer(true)
    sessionStorage.removeItem(OFFERED)
    setMessages((m) => [...m, { from: 'me', text: question }])
    setBusy(true)
    try {
      const answer = await chat.send(question, sessionId(), pageState())
      setMessages((m) => [...m, { from: 'bot', text: answer.reply, shown: answer.results?.items.length, quick: answer.quick_replies }])
      if (answer.results) {
        setResults(answer.results) // hand the cards to the page the customer is looking at
        if (window.innerWidth < 760) setChatOpen(false) // on a phone the chat would cover them
      }
    } catch (err) {
      setMessages((m) => [...m, { from: 'error', text: (err as ApiError).message }])
    } finally {
      setBusy(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    const question = text.trim()
    if (!question || busy) return
    setText('')
    void ask(question)
  }

  return (
    <div className="chat-widget">
      {chatOpen && (
        <section className="chat-panel" role="dialog" aria-label="Chat with Handsome Dan">
          <div className="chat-head">
            <Bulldog className="chat-head-dog" />
            <div>
              <strong>Handsome Dan</strong>
              <span>Campus Customs helper</span>
            </div>
            <button className="icon-button" onClick={() => setChatOpen(false)} aria-label="Close chat">
              ×
            </button>
          </div>
          <div className="chat-log" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`chat-turn ${m.from}`}>
                <p className={`chat-msg ${m.from}`}>{m.text}</p>
                {m.shown ? (
                  <p className="chat-shown">
                    ↑ {m.shown} {m.shown === 1 ? 'item is' : 'items are'} on the page
                    {i === messages.length - 1 && !busy && (
                      <>
                        {' · '}
                        <button className="link-button" onClick={() => void ask(NOT_WANTED)} title="Tell Handsome Dan so he can fix it and learn from it">
                          Not what I wanted
                        </button>
                      </>
                    )}
                  </p>
                ) : null}
                {m.quick?.length && i === messages.length - 1 && !busy ? (
                  <div className="quick-replies" role="group" aria-label="Quick answers">
                    {m.quick.map((q) => (
                      <button key={q} className="btn btn-secondary quick-reply" onClick={() => void ask(q)}>
                        {q}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
            {busy && <p className="chat-msg bot typing">Dan is thinking…</p>}
            <div ref={bottom} />
          </div>
          <form className="chat-form" onSubmit={onSubmit}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your question…" aria-label="Your question" maxLength={1000} />
            <button className="btn btn-primary" disabled={busy || !text.trim()}>
              Send
            </button>
          </form>
        </section>
      )}
      <div className="chat-launcher">
        {!chatOpen && <span className="chat-bubble">Need help?</span>}
        <button className="chat-dog-button" onClick={() => setChatOpen(!chatOpen)} aria-label={chatOpen ? 'Close chat' : 'Open chat: Need help?'}>
          <Bulldog className="chat-dog" />
        </button>
      </div>
    </div>
  )
}
