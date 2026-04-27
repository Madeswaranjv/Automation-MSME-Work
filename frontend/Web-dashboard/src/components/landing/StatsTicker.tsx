import { tickerItems } from '../../data/mockData'

export default function StatsTicker() {
  const items = tickerItems
  const repeated = [...items, ...items, ...items]

  return (
    <section
      style={{
        width: '100%',
        background: '#F96A2A',
        height: 100,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <div className="ticker-wrapper">
        <div className="ticker-content">
          {repeated.map((item, i) => (
            <span
              key={i}
              style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontSize: 20,
                fontWeight: 700,
                color: '#080808',
                textTransform: 'uppercase',
                whiteSpace: 'nowrap',
                padding: '0 20px',
              }}
            >
              {item}
              <span
                style={{
                  color: '#D94F10',
                  margin: '0 16px',
                  fontSize: 14,
                }}
              >
                ◆
              </span>
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
