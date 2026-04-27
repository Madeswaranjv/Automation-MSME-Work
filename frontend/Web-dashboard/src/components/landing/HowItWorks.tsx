import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { howItWorksSteps } from '../../data/mockData'

export default function HowItWorks() {
  const sectionRef = useRef(null)
  const isInView = useInView(sectionRef, { once: true, margin: '-100px' })

  return (
    <section
      ref={sectionRef}
      style={{
        width: '100%',
        background: '#080808',
        padding: '96px 10%',
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: 64 }}>
        <span className="section-label">THE AGENT PIPELINE</span>
        <h2 className="h2-section" style={{ marginTop: 16 }}>
          From trigger to action in seconds
        </h2>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          overflowX: 'auto',
          gap: 0,
          paddingBottom: 16,
        }}
      >
        {howItWorksSteps.map((step, i) => (
          <div
            key={i}
            style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}
          >
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: i * 0.08, duration: 0.4 }}
              style={{
                background: '#1A1A1A',
                border: '1px solid #2A2A2A',
                borderRadius: 8,
                padding: 24,
                width: 200,
                minHeight: 140,
                position: 'relative',
              }}
            >
              <span
                style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontSize: 48,
                  fontWeight: 800,
                  color: '#2A2A2A',
                  position: 'absolute',
                  top: 8,
                  right: 12,
                  lineHeight: 1,
                }}
              >
                {String(i + 1).padStart(2, '0')}
              </span>
              <span
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 13,
                  fontWeight: 700,
                  color: '#F96A2A',
                  textTransform: 'uppercase',
                  letterSpacing: 1,
                }}
              >
                {step.name}
              </span>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 13,
                  color: '#888888',
                  marginTop: 12,
                  lineHeight: 1.5,
                }}
              >
                {step.description}
              </p>
            </motion.div>
            {i < howItWorksSteps.length - 1 && (
              <span
                style={{
                  color: '#444444',
                  fontSize: 20,
                  padding: '0 8px',
                  flexShrink: 0,
                }}
              >
                →
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
