import { motion } from 'framer-motion'
import Sidebar from '../components/Sidebar'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      style={{ display: 'flex', minHeight: '100vh', background: '#080808' }}
    >
      <Sidebar />

      {/* Main Content Area */}
      <div style={{ marginLeft: 240, flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Top Header */}
        <header
          style={{
            height: 64,
            background: '#080808',
            borderBottom: '1px solid #2A2A2A',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 32px',
            position: 'sticky',
            top: 0,
            zIndex: 50,
          }}
        >
          <div
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 14,
              color: '#888888',
            }}
          >
            {new Date().toLocaleDateString('en-IN', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <input
              className="input-field"
              placeholder="Search agents, invoices..."
              style={{ width: 240, fontSize: 13 }}
            />
            <button
              className="btn-secondary"
              style={{ padding: '8px 16px', fontSize: 12 }}
            >
              View Agent Reasoning
            </button>
          </div>
        </header>

        {/* Scrollable Content */}
        <main
          style={{
            flex: 1,
            padding: 32,
            overflowY: 'auto',
          }}
        >
          {children}
        </main>
      </div>
    </motion.div>
  )
}
