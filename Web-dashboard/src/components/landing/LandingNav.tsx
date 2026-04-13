import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function LandingNav() {
  const links = ['Platform', 'Agents', 'Features', 'Pricing']

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: 64,
        background: '#080808',
        borderBottom: '1px solid #2A2A2A',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 5%',
        zIndex: 1000,
      }}
    >
      {/* Logo */}
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          style={{
            width: 28,
            height: 28,
            background: '#F96A2A',
            borderRadius: 4,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800,
            fontSize: 16,
            color: '#FFFFFF',
          }}
        >
          M
        </div>
        <span
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: 17,
            fontWeight: 700,
            color: '#FFFFFF',
          }}
        >
          MSME AI
        </span>
      </Link>

      {/* Center Nav Links */}
      <div style={{ display: 'flex', gap: 32, alignItems: 'center' }}>
        {links.map((link) => (
          <motion.a
            key={link}
            href="#"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 14,
              fontWeight: 500,
              color: '#888888',
              textDecoration: 'none',
              transition: 'color 150ms ease',
            }}
            whileHover={{ color: '#FFFFFF' }}
          >
            {link}
          </motion.a>
        ))}
      </div>

      {/* Right Buttons */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button
          className="btn-secondary"
          style={{ padding: '8px 18px', fontSize: 13 }}
        >
          Sign In
        </button>
        <Link to="/dashboard">
          <button
            className="btn-primary"
            style={{ padding: '8px 20px', fontSize: 13 }}
          >
            Get Started
          </button>
        </Link>
      </div>
    </nav>
  )
}
