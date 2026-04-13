import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Zap, Eye, Bell, X } from 'lucide-react'
import { reasoningSteps } from '../../data/mockData'

const iconMap: Record<string, any> = {
  Brain,
  Zap,
  Eye,
  Bell,
}

const typeColors: Record<string, string> = {
  REASON: '#888888',
  ACT: '#F96A2A',
  OBSERVE: '#22C55E',
  HITL: '#F59E0B',
}

const typeBgColors: Record<string, string> = {
  REASON: 'rgba(136,136,136,0.15)',
  ACT: 'rgba(249,106,42,0.15)',
  OBSERVE: 'rgba(34,197,94,0.15)',
  HITL: 'rgba(245,158,11,0.15)',
}

export default function ReasoningDrawer({
  isOpen,
  onClose,
}: {
  isOpen: boolean
  onClose: () => void
}) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.5)',
              zIndex: 200,
            }}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{
              type: 'spring',
              stiffness: 300,
              damping: 30,
            }}
            style={{
              position: 'fixed',
              right: 0,
              top: 0,
              width: 400,
              height: '100vh',
              background: '#1A1A1A',
              borderLeft: '1px solid #2A2A2A',
              zIndex: 210,
              overflowY: 'auto',
              padding: 24,
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 24,
              }}
            >
              <div>
                <h3
                  style={{
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                    fontSize: 18,
                    fontWeight: 700,
                    color: '#FFFFFF',
                    margin: 0,
                  }}
                >
                  Orchestrator ReAct Log
                </h3>
                <p
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 13,
                    color: '#666666',
                    marginTop: 4,
                  }}
                >
                  Last task: Invoice INV-2024-0148
                </p>
              </div>
              <button
                onClick={onClose}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#888888',
                  cursor: 'pointer',
                  padding: 4,
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Timeline Steps */}
            <div>
              {reasoningSteps.map((step, i) => {
                const Icon = iconMap[step.icon] || Brain
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.12, duration: 0.3 }}
                    style={{
                      borderLeft: `2px solid ${typeColors[step.type]}`,
                      paddingLeft: 16,
                      paddingBottom: i < reasoningSteps.length - 1 ? 20 : 0,
                      marginBottom: i < reasoningSteps.length - 1 ? 0 : 0,
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        marginBottom: 8,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "'Inter', sans-serif",
                          fontSize: 10,
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          color: typeColors[step.type],
                          background: typeBgColors[step.type],
                          padding: '2px 8px',
                          borderRadius: 3,
                        }}
                      >
                        {step.type}
                      </span>
                      <Icon size={14} style={{ color: typeColors[step.type] }} />
                    </div>
                    <p
                      style={{
                        fontFamily: "'Inter', sans-serif",
                        fontSize: 13,
                        color: '#CCCCCC',
                        lineHeight: 1.5,
                        margin: 0,
                        background: '#111111',
                        padding: 12,
                        borderRadius: 6,
                        border: '1px solid #2A2A2A',
                      }}
                    >
                      {step.content}
                    </p>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
