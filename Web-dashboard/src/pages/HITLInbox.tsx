import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import DashboardLayout from '../layouts/DashboardLayout'
import { hitlItems, type HITLItem } from '../data/mockData'

// ── Mini 3D Agent Icons ──
function MiniAgent({ geometry }: { geometry: string }) {
  const ref = useRef<THREE.Mesh>(null!)
  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.y += 0.02
      ref.current.rotation.x += 0.01
    }
  })

  const getGeometry = () => {
    switch (geometry) {
      case 'octahedron': return <octahedronGeometry args={[0.5]} />
      case 'tetrahedron': return <tetrahedronGeometry args={[0.5]} />
      case 'box': return <boxGeometry args={[0.7, 0.7, 0.7]} />
      default: return <sphereGeometry args={[0.4, 16, 16]} />
    }
  }

  return (
    <Canvas
      style={{ width: 48, height: 48, background: 'transparent' }}
      camera={{ position: [0, 0, 2] }}
      gl={{ antialias: true, alpha: true }}
    >
      <ambientLight intensity={0.6} />
      <pointLight position={[2, 2, 2]} color="#F96A2A" intensity={1.5} />
      <mesh ref={ref}>
        {getGeometry()}
        <meshStandardMaterial
          color="#F96A2A"
          emissive="#FF5500"
          emissiveIntensity={0.4}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>
    </Canvas>
  )
}

// ── HITL Card ──
function HITLCard({
  item,
  index,
  onApprove,
  onReject,
}: {
  item: HITLItem
  index: number
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  const [showRejectInput, setShowRejectInput] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const riskColors: Record<string, string> = {
    HIGH: '#EF4444',
    MEDIUM: '#F59E0B',
    LOW: '#22C55E',
  }
  const riskBgColors: Record<string, string> = {
    HIGH: 'rgba(239,68,68,0.15)',
    MEDIUM: 'rgba(245,158,11,0.15)',
    LOW: 'rgba(34,197,94,0.15)',
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 100, height: 0, marginBottom: 0, paddingTop: 0, paddingBottom: 0 }}
      transition={{ duration: 0.3, delay: index * 0.15 }}
      style={{
        background: '#1A1A1A',
        border: '1px solid #2A2A2A',
        borderRadius: 8,
        padding: 24,
        position: 'relative',
        overflow: 'hidden',
        marginBottom: 16,
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
          background: item.agentColor,
        }}
      />

      <div style={{ paddingLeft: 12, display: 'flex', gap: 16 }}>
        {/* Mini 3D */}
        <div style={{ flexShrink: 0, paddingTop: 4 }}>
          <MiniAgent geometry={item.geometry} />
        </div>

        <div style={{ flex: 1 }}>
          {/* Header Badges */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 10,
                fontWeight: 700,
                textTransform: 'uppercase',
                color: item.agentColor,
                background: `rgba(249,106,42,0.15)`,
                padding: '3px 8px',
                borderRadius: 4,
              }}
            >
              {item.agent} AGENT
            </span>
            <span
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 10,
                fontWeight: 700,
                textTransform: 'uppercase',
                color: riskColors[item.risk],
                background: riskBgColors[item.risk],
                padding: '3px 8px',
                borderRadius: 4,
              }}
            >
              {item.risk} RISK
            </span>
            <span
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 11,
                color: '#666666',
                marginLeft: 'auto',
              }}
            >
              {item.timestamp}
            </span>
          </div>

          {/* Title */}
          <h4
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 16,
              fontWeight: 600,
              color: '#FFFFFF',
              marginBottom: 16,
            }}
          >
            {item.title}
          </h4>

          {/* Preview Box */}
          <div
            style={{
              background: '#111111',
              border: '1px solid #2A2A2A',
              borderRadius: 6,
              padding: 16,
              marginBottom: 16,
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
              {item.preview}
            </pre>
          </div>

          {/* Buttons */}
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn-primary" onClick={() => onApprove(item.id)}>
              APPROVE
            </button>
            <button
              className="btn-secondary"
              onClick={() => setShowRejectInput(!showRejectInput)}
            >
              REJECT
            </button>
          </div>

          {/* Inline Reject Input */}
          <AnimatePresence>
            {showRejectInput && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                style={{ overflow: 'hidden', marginTop: 12 }}
              >
                <input
                  className="input-field"
                  placeholder="Reason for rejection..."
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  style={{ width: '100%', marginBottom: 8 }}
                />
                <button
                  className="btn-destructive"
                  style={{ fontSize: 12, padding: '6px 16px' }}
                  onClick={() => onReject(item.id)}
                >
                  CONFIRM REJECT
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  )
}

// ── HITL Inbox Page ──
export default function HITLInbox() {
  const [items, setItems] = useState<HITLItem[]>(hitlItems)

  const handleApprove = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id))
  }

  const handleReject = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id))
  }

  return (
    <DashboardLayout>
      {/* Banner */}
      <div
        style={{
          border: '1px solid #F96A2A',
          borderRadius: 8,
          padding: '16px 24px',
          marginBottom: 24,
          animation: 'border-pulse 2s infinite',
          background: 'rgba(249,106,42,0.05)',
        }}
      >
        <h3
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: 20,
            fontWeight: 700,
            color: '#FFFFFF',
            margin: 0,
          }}
        >
          {items.length} Actions Awaiting Your Approval
        </h3>
      </div>

      {/* HITL Cards */}
      <AnimatePresence mode="popLayout">
        {items.map((item, i) => (
          <HITLCard
            key={item.id}
            item={item}
            index={i}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        ))}
      </AnimatePresence>

      {items.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            textAlign: 'center',
            padding: 48,
            color: '#666666',
            fontFamily: "'Inter', sans-serif",
            fontSize: 16,
          }}
        >
          ✓ All caught up! No pending approvals.
        </motion.div>
      )}
    </DashboardLayout>
  )
}
