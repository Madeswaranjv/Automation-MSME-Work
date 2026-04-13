import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Receipt,
  Package,
  BarChart3,
  Users,
  MessageSquare,
  CreditCard,
} from 'lucide-react'
import { activityLog, additionalActivities, type ActivityItem } from '../../data/mockData'

const iconMap: Record<string, any> = {
  Receipt,
  Package,
  BarChart3,
  Users,
  MessageSquare,
  CreditCard,
}

const statusColors: Record<string, string> = {
  COMPLETED: '#22C55E',
  'PENDING HITL': '#F59E0B',
  FAILED: '#EF4444',
}

const statusBgColors: Record<string, string> = {
  COMPLETED: 'rgba(34,197,94,0.15)',
  'PENDING HITL': 'rgba(245,158,11,0.15)',
  FAILED: 'rgba(239,68,68,0.15)',
}

export default function AgentActivityLog() {
  const [activities, setActivities] = useState<ActivityItem[]>(activityLog)
  const extraIdx = useState({ current: 0 })[0]

  useEffect(() => {
    const interval = setInterval(() => {
      if (extraIdx.current >= additionalActivities.length) {
        extraIdx.current = 0
      }
      const newActivity = {
        ...additionalActivities[extraIdx.current],
        id: `live-${Date.now()}`,
        timestamp: 'Just now',
      }
      extraIdx.current++
      setActivities((prev) => [newActivity, ...prev.slice(0, 7)])
    }, 12000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="card">
      <h4 className="h4-dashboard" style={{ marginBottom: 20 }}>
        Agent Activity Log
      </h4>

      <div style={{ position: 'relative' }}>
        <AnimatePresence mode="popLayout">
          {activities.map((activity, i) => {
            const Icon = iconMap[activity.icon] || Receipt
            return (
              <motion.div
                key={activity.id}
                layout
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3, delay: i * 0.08 }}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 12,
                  padding: '12px 0',
                  borderBottom: i < activities.length - 1 ? '1px solid #1A1A1A' : 'none',
                }}
              >
                {/* Dot + Icon */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 4,
                    minWidth: 24,
                  }}
                >
                  <div
                    style={{
                      width: 3,
                      height: 3,
                      borderRadius: '50%',
                      background: activity.agentColor,
                      marginTop: 2,
                    }}
                  />
                  <Icon
                    size={14}
                    style={{ color: activity.agentColor }}
                  />
                  {i < activities.length - 1 && (
                    <div
                      style={{
                        width: 1,
                        flex: 1,
                        minHeight: 16,
                        background: '#2A2A2A',
                      }}
                    />
                  )}
                </div>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 13,
                      color: '#CCCCCC',
                      lineHeight: 1.5,
                      margin: 0,
                    }}
                  >
                    {activity.description}
                  </p>
                </div>

                {/* Status + Time */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-end',
                    gap: 4,
                    flexShrink: 0,
                  }}
                >
                  <span
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 10,
                      fontWeight: 700,
                      color: statusColors[activity.status],
                      background: statusBgColors[activity.status],
                      padding: '2px 6px',
                      borderRadius: 3,
                      textTransform: 'uppercase',
                    }}
                  >
                    {activity.status}
                  </span>
                  <span
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 11,
                      color: '#666666',
                    }}
                  >
                    {activity.timestamp}
                  </span>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
