import { Link } from 'react-router-dom'

export default function FinalCTA() {
  return (
    <section
      style={{
        width: '100%',
        background: '#0D0D0D',
        padding: '120px 10%',
        textAlign: 'center',
        position: 'relative',
      }}
    >
      {/* Orange glow */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse 40% 40% at 50% 50%, rgba(249,106,42,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      <div style={{ position: 'relative', zIndex: 1 }}>
        <h2
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: 56,
            fontWeight: 800,
            color: '#FFFFFF',
            lineHeight: 1.1,
          }}
        >
          Your business, run by agents.
        </h2>
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 18,
            color: '#888888',
            marginTop: 20,
            lineHeight: 1.7,
          }}
        >
          Install on your desktop. Connect your Tally.
          <br />
          Watch 6 agents take over.
        </p>
        <Link to="/dashboard">
          <button
            className="btn-primary"
            style={{
              padding: '16px 36px',
              fontSize: 16,
              marginTop: 40,
            }}
          >
            Download Free — Windows & Mac
          </button>
        </Link>
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 13,
            color: '#444444',
            marginTop: 20,
          }}
        >
          No cloud. No subscription. No data leaves your machine.
        </p>
      </div>
    </section>
  )
}
