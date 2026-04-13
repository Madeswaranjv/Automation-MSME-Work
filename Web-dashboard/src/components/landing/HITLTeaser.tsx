import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'

export default function HITLTeaser() {
  const sectionRef = useRef(null)
  const isInView = useInView(sectionRef, { once: true, margin: '-100px' })

  return (
    <section
      ref={sectionRef}
      style={{
        width: '100%',
        background: '#111111',
        padding: '96px 10%',
        display: 'flex',
        alignItems: 'center',
        gap: 64,
      }}
    >
      {/* Left Text */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
        style={{ flex: 1 }}
      >
        <span className="section-label">HUMAN-IN-THE-LOOP</span>
        <h2 className="h2-section" style={{ marginTop: 16 }}>
          AI acts. You approve.
          <br />
          Always in control.
        </h2>
        <p
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 16,
            color: '#888888',
            marginTop: 20,
            lineHeight: 1.7,
            maxWidth: 420,
          }}
        >
          Before any money moves, invoice sends to &gt;10 customers, or GSTR
          files — the agent pauses and asks. You tap Approve or Reject from
          your phone.
        </p>
        <a
          href="#"
          style={{
            display: 'inline-block',
            marginTop: 24,
            fontFamily: "'Inter', sans-serif",
            fontSize: 14,
            fontWeight: 600,
            color: '#F96A2A',
          }}
        >
          See HITL in action →
        </a>
      </motion.div>

      {/* Right Mock HITL Card */}
      <motion.div
        initial={{ opacity: 0, x: 60 }}
        animate={isInView ? { opacity: 1, x: 0 } : {}}
        transition={{ duration: 0.6, delay: 0.2 }}
        style={{ flex: 1, maxWidth: 480 }}
      >
        <div
          style={{
            background: '#1A1A1A',
            border: '1px solid #2A2A2A',
            borderRadius: 8,
            padding: 24,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Left Accent Strip */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: 4,
              background: '#F96A2A',
            }}
          />

          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 16,
              paddingLeft: 12,
            }}
          >
            <span
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 10,
                fontWeight: 700,
                textTransform: 'uppercase',
                color: '#F96A2A',
                background: 'rgba(249,106,42,0.15)',
                padding: '3px 8px',
                borderRadius: 4,
              }}
            >
              BILLING AGENT
            </span>
            <span
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 10,
                fontWeight: 700,
                textTransform: 'uppercase',
                color: '#EF4444',
                background: 'rgba(239,68,68,0.15)',
                padding: '3px 8px',
                borderRadius: 4,
              }}
            >
              HIGH RISK
            </span>
          </div>

          {/* Title */}
          <h4
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 16,
              fontWeight: 600,
              color: '#FFFFFF',
              paddingLeft: 12,
              marginBottom: 16,
            }}
          >
            Send GST Invoice to 15 customers — ₹2,84,590 total
          </h4>

          {/* Preview Box */}
          <div
            style={{
              background: '#111111',
              border: '1px solid #2A2A2A',
              borderRadius: 6,
              padding: 16,
              marginLeft: 12,
              marginBottom: 20,
            }}
          >
            <pre
              style={{
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: 12,
                color: '#CCCCCC',
                whiteSpace: 'pre-wrap',
                margin: 0,
                lineHeight: 1.6,
              }}
            >
{`INV-2024-0148  |  Rajan Stores
HSN: 6403  |  GST: 18%
Amount: ₹18,940 × 15 customers
Total: ₹2,84,590`}
            </pre>
          </div>

          {/* Buttons */}
          <div
            style={{
              display: 'flex',
              gap: 12,
              paddingLeft: 12,
            }}
          >
            <button
              className="btn-primary"
              style={{
                padding: '10px 24px',
                animation: 'cta-pulse 2s ease infinite',
              }}
            >
              APPROVE
            </button>
            <button
              className="btn-secondary"
              style={{ padding: '10px 24px' }}
            >
              REJECT
            </button>
          </div>
        </div>
      </motion.div>
    </section>
  )
}
