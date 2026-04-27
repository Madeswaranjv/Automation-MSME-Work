import { motion } from 'framer-motion'
import { revenueSources } from '../../data/mockData'

export default function RevenueSources() {
  return (
    <div className="card" style={{ height: '100%' }}>
      <h4 className="h4-dashboard" style={{ marginBottom: 24 }}>
        Revenue Sources
      </h4>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {revenueSources.map((source, i) => (
          <div key={source.name}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 8,
              }}
            >
              <span
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 13,
                  color: '#CCCCCC',
                }}
              >
                {source.name}
              </span>
              <span
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 13,
                  color: '#888888',
                  fontWeight: 600,
                }}
              >
                {source.value}%
              </span>
            </div>
            <div
              style={{
                width: '100%',
                height: 4,
                background: '#2A2A2A',
                borderRadius: 2,
                overflow: 'hidden',
              }}
            >
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${source.value}%` }}
                transition={{ duration: 0.4, delay: i * 0.1, ease: 'easeOut' }}
                style={{
                  height: '100%',
                  background: '#F96A2A',
                  borderRadius: 2,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
