import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../auth'
import { useShop } from '../store'
import { Crest } from './Art'

export default function Header() {
  const { count, setCartOpen } = useShop()
  const { user, ready, logOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const close = () => setMenuOpen(false)

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link to="/" className="brand" onClick={close} aria-label="Campus Customs home">
          <Crest className="brand-crest" />
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-sub">Yale merchandise since 1975</span>
          </span>
        </Link>

        <button
          className="menu-toggle"
          aria-expanded={menuOpen}
          aria-controls="main-nav"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? 'Close' : 'Menu'}
        </button>

        <nav id="main-nav" className={`main-nav ${menuOpen ? 'open' : ''}`} aria-label="Main">
          <ul className="nav-links">
            <li>
              <NavLink to="/" end onClick={close}>
                Home
              </NavLink>
            </li>
            <li>
              <NavLink to="/products" onClick={close}>
                Products
              </NavLink>
            </li>
            <li>
              <NavLink to="/gift-certificates" onClick={close}>
                Gift Certificates
              </NavLink>
            </li>
            <li>
              <NavLink to="/about" onClick={close}>
                About Us
              </NavLink>
            </li>
          </ul>
          <div className="nav-account">
            {ready && user && (
              <>
                <span className="nav-greeting">Hi, {user.first_name}</span>
                <NavLink to="/account" className="nav-signup" onClick={close}>
                  My Account
                </NavLink>
                <button
                  className="nav-login nav-logout"
                  onClick={() => {
                    close()
                    void logOut()
                  }}
                >
                  Log Out
                </button>
              </>
            )}
            {ready && !user && (
              <>
                <NavLink to="/login" className="nav-login" onClick={close}>
                  Log In
                </NavLink>
                <NavLink to="/create-account" className="nav-signup" onClick={close}>
                  Create Account
                </NavLink>
              </>
            )}
            <button
              className="cart-button"
              onClick={() => {
                close()
                setCartOpen(true)
              }}
              aria-label={`Shopping cart, ${count} ${count === 1 ? 'item' : 'items'}`}
            >
              <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                <path
                  d="M3 4h2l2.4 11h10.2L20 7H6.2"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="9" cy="19" r="1.6" fill="currentColor" />
                <circle cx="17" cy="19" r="1.6" fill="currentColor" />
              </svg>
              {count > 0 && <span className="cart-badge">{count}</span>}
            </button>
          </div>
        </nav>
      </div>
    </header>
  )
}
