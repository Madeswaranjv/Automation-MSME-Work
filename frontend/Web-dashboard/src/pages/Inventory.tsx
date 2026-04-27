import { useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { motion } from 'framer-motion'
import * as THREE from 'three'
import DashboardLayout from '../layouts/DashboardLayout'
import { inventoryData } from '../data/mockData'

// ── 3D Warehouse Visual ──
const stockColors: Record<string, string> = {
  adequate: '#22C55E',
  low: '#F59E0B',
  critical: '#EF4444',
}

function WarehouseShelf({
  position,
  items,
}: {
  position: [number, number, number]
  items: { color: string; height: number; label: string }[]
}) {
  return (
    <group position={position}>
      {/* Shelf */}
      <mesh>
        <boxGeometry args={[3, 0.08, 0.8]} />
        <meshStandardMaterial color="#222222" roughness={0.6} />
      </mesh>

      {/* Items on shelf */}
      {items.map((item, i) => {
        const x = -1.2 + i * 0.6
        return (
          <group key={i} position={[x, item.height / 2 + 0.04, 0]}>
            <mesh>
              <boxGeometry args={[0.4, item.height, 0.4]} />
              <meshStandardMaterial
                color={item.color}
                emissive={item.color}
                emissiveIntensity={0.15}
                roughness={0.5}
              />
            </mesh>
            {item.color === '#EF4444' && (
              <WarningFloat position={[0, item.height / 2 + 0.3, 0]} />
            )}
          </group>
        )
      })}
    </group>
  )
}

function WarningFloat({ position }: { position: [number, number, number] }) {
  const ref = useRef<THREE.Mesh>(null!)
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.position.y = position[1] + Math.sin(clock.getElapsedTime() * 2) * 0.1
    }
  })

  return (
    <mesh ref={ref} position={position}>
      <octahedronGeometry args={[0.08]} />
      <meshStandardMaterial
        color="#EF4444"
        emissive="#EF4444"
        emissiveIntensity={0.6}
      />
    </mesh>
  )
}

function WarehouseScene() {
  const shelves = [
    {
      position: [-2, 0, 0] as [number, number, number],
      items: [
        { color: '#22C55E', height: 0.8, label: 'Cotton' },
        { color: '#22C55E', height: 0.6, label: 'Dye' },
        { color: '#F59E0B', height: 0.3, label: 'Fabric' },
        { color: '#22C55E', height: 0.7, label: 'Zipper' },
        { color: '#EF4444', height: 0.15, label: 'Buttons' },
      ],
    },
    {
      position: [2, 0, 0] as [number, number, number],
      items: [
        { color: '#F59E0B', height: 0.35, label: 'Boxes' },
        { color: '#EF4444', height: 0.1, label: 'Elastic' },
        { color: '#22C55E', height: 0.9, label: 'Thread' },
        { color: '#EF4444', height: 0.12, label: 'Needles' },
        { color: '#22C55E', height: 0.5, label: 'Fabric' },
      ],
    },
  ]

  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} color="#FFFFFF" intensity={1} />
      <pointLight position={[-3, 3, 3]} color="#F96A2A" intensity={0.5} />

      {shelves.map((shelf, i) => (
        <WarehouseShelf key={i} position={shelf.position} items={shelf.items} />
      ))}

      <OrbitControls
        minPolarAngle={Math.PI / 4}
        maxPolarAngle={Math.PI / 2.2}
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.3}
      />
    </>
  )
}

// ── Mini Sparkline ──
function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const w = 80
  const h = 24

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - ((v - min) / range) * h
    return `${x},${y}`
  })

  const pathD = points.reduce((acc, pt, i) => {
    if (i === 0) return `M ${pt}`
    return `${acc} L ${pt}`
  }, '')

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <path d={pathD} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" />
    </svg>
  )
}

// ── Inventory Page ──
export default function Inventory() {
  const [sortBy, setSortBy] = useState<'qty' | 'name' | 'status'>('status')

  const sorted = [...inventoryData].sort((a, b) => {
    if (sortBy === 'qty') return a.qty - b.qty
    if (sortBy === 'name') return a.name.localeCompare(b.name)
    const priority = { critical: 0, low: 1, adequate: 2 }
    return priority[a.status] - priority[b.status]
  })

  return (
    <DashboardLayout>
      <div style={{ marginBottom: 24 }}>
        <h2 className="h2-section" style={{ fontSize: 28 }}>Inventory</h2>
        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#666666', marginTop: 4 }}>
          AI-powered stock management & forecasting
        </p>
      </div>

      {/* 3D Warehouse */}
      <div
        style={{
          height: 200,
          background: '#111111',
          border: '1px solid #2A2A2A',
          borderRadius: 8,
          overflow: 'hidden',
          marginBottom: 24,
        }}
      >
        <Canvas
          camera={{ position: [4, 3, 4], fov: 50 }}
          gl={{ antialias: true, alpha: true }}
          onCreated={({ camera }) => camera.lookAt(0, 0, 0)}
        >
          <WarehouseScene />
        </Canvas>
      </div>

      {/* Alert Cards */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        {inventoryData
          .filter((item) => item.status === 'critical')
          .map((item) => (
            <motion.div
              key={item.sku}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                background: '#1A1A1A',
                border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 8,
                padding: 16,
                flex: 1,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: '#EF4444',
                    animation: 'dot-blink 1.5s infinite',
                  }}
                />
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 12, fontWeight: 700, color: '#EF4444', textTransform: 'uppercase' }}>
                  CRITICAL
                </span>
              </div>
              <div style={{ fontFamily: "'Inter', sans-serif", fontSize: 14, fontWeight: 600, color: '#FFFFFF' }}>
                {item.name}
              </div>
              <div style={{ fontFamily: "'Inter', sans-serif", fontSize: 12, color: '#888888', marginTop: 4 }}>
                {item.qty} units remaining · Reorder at {item.reorder}
              </div>
            </motion.div>
          ))}
      </div>

      {/* SKU Table */}
      <div className="card" style={{ overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h4 className="h4-dashboard">Stock Overview</h4>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['status', 'qty', 'name'] as const).map((sort) => (
              <button
                key={sort}
                onClick={() => setSortBy(sort)}
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 11,
                  fontWeight: 500,
                  color: sortBy === sort ? '#FFFFFF' : '#888888',
                  background: sortBy === sort ? '#222222' : 'transparent',
                  border: 'none',
                  borderRadius: 4,
                  padding: '4px 10px',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                }}
              >
                {sort}
              </button>
            ))}
          </div>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2A2A2A' }}>
              {['SKU', 'Product', 'Category', 'Qty', 'Reorder', 'Status', '7-Day Forecast', 'Value'].map((h) => (
                <th
                  key={h}
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 11,
                    fontWeight: 600,
                    color: '#888888',
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                    padding: '12px 8px',
                    textAlign: 'left',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, i) => (
              <motion.tr
                key={item.sku}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                style={{
                  borderBottom: '1px solid #1A1A1A',
                }}
              >
                <td style={{ padding: '12px 8px', fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#888888', fontWeight: 500 }}>
                  {item.sku}
                </td>
                <td style={{ padding: '12px 8px', fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#FFFFFF', fontWeight: 500 }}>
                  {item.name}
                </td>
                <td style={{ padding: '12px 8px', fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#888888' }}>
                  {item.category}
                </td>
                <td style={{ padding: '12px 8px', fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#FFFFFF', fontWeight: 600 }}>
                  {item.qty}
                </td>
                <td style={{ padding: '12px 8px', fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#666666' }}>
                  {item.reorder}
                </td>
                <td style={{ padding: '12px 8px' }}>
                  <span
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 10,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      color: stockColors[item.status],
                      background:
                        item.status === 'adequate'
                          ? 'rgba(34,197,94,0.15)'
                          : item.status === 'low'
                          ? 'rgba(245,158,11,0.15)'
                          : 'rgba(239,68,68,0.15)',
                      padding: '3px 8px',
                      borderRadius: 3,
                    }}
                  >
                    {item.status}
                  </span>
                </td>
                <td style={{ padding: '12px 8px' }}>
                  <MiniSparkline data={item.forecast} color={stockColors[item.status]} />
                </td>
                <td style={{ padding: '12px 8px', fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#CCCCCC' }}>
                  ₹{(item.qty * item.price).toLocaleString('en-IN')}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  )
}
