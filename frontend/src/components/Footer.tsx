import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import { Bulldog, Crest } from './Art'

// The mascot lives in the footer, so Handsome Dan is on every page.
export default function Footer() {
  const { user } = useAuth()
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-mascot" aria-hidden="false">
          <Bulldog className="footer-bulldog" pose="fist" />
          <p className="footer-mascot-caption">Handsome Dan says: Boola Boola!</p>
        </div>
        <div className="footer-main">
          <div className="footer-motto">
            <Crest className="footer-crest" />
            <div>
              <p className="motto">Lux et Veritas</p>
              <p className="motto-translation">Light and Truth</p>
            </div>
          </div>
          <nav aria-label="Footer" className="footer-links">
            <Link to="/">Home</Link>
            <Link to="/products">Products</Link>
            <Link to="/gift-certificates">Gift Certificates</Link>
            <Link to="/about">About Us</Link>
            {user && <Link to="/account">My Account</Link>}
            {!user && <Link to="/login">Log In</Link>}
            {!user && <Link to="/create-account">Create Account</Link>}
          </nav>
          <p className="fine-print">
            Campus Customs is a class project for MGT 409 at the Yale School of Management. It is a student exercise and is not
            an official Yale University website.
          </p>
          <p className="fine-print">
            Campus photos from Wikimedia Commons: Harkness Tower by Gunnar Klack (CC BY-SA 4.0), Sterling Memorial Library by
            Christian David (CC BY-SA 4.0), Old Campus by DimiTalen (CC0).
          </p>
        </div>
      </div>
    </footer>
  )
}
