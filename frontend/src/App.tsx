import { Link, Route, Routes } from 'react-router-dom'
import CartDrawer from './components/CartDrawer'
import ChatWidget from './components/ChatWidget'
import ChatResults from './components/ChatResults'
import EntryDoors from './components/EntryDoors'
import Footer from './components/Footer'
import GiftBanner from './components/GiftBanner'
import Header from './components/Header'
import About from './pages/About'
import { AuthProvider } from './auth'
import { CreateAccount, ForgotPassword, LogIn, MyAccount, ResetPassword } from './pages/AccountForms'
import GiftCertificates from './pages/GiftCertificates'
import Home from './pages/Home'
import ProductPage from './pages/ProductPage'
import Products from './pages/Products'
import { ShopProvider } from './store'

function NotFound() {
  return (
    <div className="container page empty">
      <h1>Page not found</h1>
      <p>That page wandered off campus.</p>
      <Link to="/" className="btn btn-primary">
        Back to the home page
      </Link>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ShopProvider>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <EntryDoors />
        <GiftBanner />
        <Header />
        <main id="main">
          <ChatResults />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:id" element={<ProductPage />} />
            <Route path="/gift-certificates" element={<GiftCertificates />} />
            <Route path="/about" element={<About />} />
            <Route path="/login" element={<LogIn />} />
            <Route path="/create-account" element={<CreateAccount />} />
            <Route path="/account" element={<MyAccount />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <Footer />
        <CartDrawer />
        <ChatWidget />
      </ShopProvider>
    </AuthProvider>
  )
}
