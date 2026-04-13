import { Link } from 'react-router-dom'

const productLinks = ['Dashboard', 'Billing', 'Inventory', 'Accounting', 'HR', 'CRM', 'Credit']
const resourceLinks = ['Documentation', 'GitHub', 'Changelog', 'API Docs']
const legalLinks = ['Privacy', 'Terms', 'Security']

export default function Footer() {
  const linkStyle: React.CSSProperties = {
    fontFamily: "'Inter', sans-serif",
    fontSize: 13,
    color: '#666666',
    display: 'block',
    marginBottom: 8,
    transition: 'color 150ms ease',
    cursor: 'pointer',
  }

  return (
    <footer
      style={{
        width: '100%',
        background: '#080808',
        borderTop: '1px solid #2A2A2A',
        padding: '48px 10%',
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr 1fr',
          gap: 40,
        }}
      >
        {/* Column 1 */}
        <div>
          <Link
            to="/"
            style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}
          >
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
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              color: '#666666',
              lineHeight: 1.6,
              maxWidth: 280,
            }}
          >
            Autonomous AI agents for Indian micro, small, and medium
            enterprises. Privacy-first, offline-capable, India-built.
          </p>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              color: '#888888',
              marginTop: 16,
            }}
          >
            India-Built 🇮🇳
          </p>
        </div>

        {/* Column 2 */}
        <div>
          <h4
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              fontWeight: 600,
              color: '#FFFFFF',
              marginBottom: 16,
            }}
          >
            Product
          </h4>
          {productLinks.map((link) => (
            <a
              key={link}
              href="#"
              style={linkStyle}
              onMouseEnter={(e) => ((e.target as HTMLElement).style.color = '#CCCCCC')}
              onMouseLeave={(e) => ((e.target as HTMLElement).style.color = '#666666')}
            >
              {link}
            </a>
          ))}
        </div>

        {/* Column 3 */}
        <div>
          <h4
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              fontWeight: 600,
              color: '#FFFFFF',
              marginBottom: 16,
            }}
          >
            Resources
          </h4>
          {resourceLinks.map((link) => (
            <a
              key={link}
              href="#"
              style={linkStyle}
              onMouseEnter={(e) => ((e.target as HTMLElement).style.color = '#CCCCCC')}
              onMouseLeave={(e) => ((e.target as HTMLElement).style.color = '#666666')}
            >
              {link}
            </a>
          ))}
        </div>

        {/* Column 4 */}
        <div>
          <h4
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              fontWeight: 600,
              color: '#FFFFFF',
              marginBottom: 16,
            }}
          >
            Legal
          </h4>
          {legalLinks.map((link) => (
            <a
              key={link}
              href="#"
              style={linkStyle}
              onMouseEnter={(e) => ((e.target as HTMLElement).style.color = '#CCCCCC')}
              onMouseLeave={(e) => ((e.target as HTMLElement).style.color = '#666666')}
            >
              {link}
            </a>
          ))}
        </div>
      </div>

      {/* Bottom Strip */}
      <div
        style={{
          borderTop: '1px solid #2A2A2A',
          marginTop: 40,
          paddingTop: 20,
          textAlign: 'center',
        }}
      >
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 12,
            color: '#444444',
          }}
        >
          © 2025 MSME AI Platform. Built for Bharat.
        </p>
      </div>
    </footer>
  )
}
