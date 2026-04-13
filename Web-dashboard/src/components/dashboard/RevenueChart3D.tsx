import { useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Text } from '@react-three/drei'
import * as THREE from 'three'
import { revenueData } from '../../data/mockData'

function Bar3D({
  position,
  height,
  label,
  value,
}: {
  position: [number, number, number]
  height: number
  label: string
  value: number
}) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const targetHeight = useRef(0)
  const [hovered, setHovered] = useState(false)
  const mounted = useRef(false)
  const currentHeight = useRef(0.001)

  useFrame(() => {
    if (!meshRef.current) return
    if (!mounted.current) {
      targetHeight.current = height
      mounted.current = true
    }

    // Lerp to target height
    currentHeight.current += (targetHeight.current - currentHeight.current) * 0.03
    meshRef.current.scale.y = currentHeight.current
    meshRef.current.position.y = currentHeight.current / 2
  })

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <boxGeometry args={[0.4, 1, 0.4]} />
        <meshStandardMaterial
          color={hovered ? '#FFFFFF' : '#F96A2A'}
          metalness={0.1}
          roughness={0.6}
        />
      </mesh>

      {/* Month label */}
      <Text
        position={[0, -0.15, 0.35]}
        fontSize={0.2}
        color="#666666"
        anchorX="center"
        anchorY="top"
        rotation={[-0.3, 0, 0]}
      >
        {label}
      </Text>

      {/* Value tooltip on hover */}
      {hovered && (
        <Text
          position={[0, height + 0.3, 0]}
          fontSize={0.2}
          color="#FFFFFF"
          anchorX="center"
          anchorY="bottom"
        >
          {`${label} · ₹${value}L`}
        </Text>
      )}
    </group>
  )
}

function BarChartScene() {
  const maxVal = Math.max(...revenueData.map((d) => d.value))

  return (
    <>
      <ambientLight intensity={0.5} />
      <pointLight position={[5, 8, 5]} color="#F96A2A" intensity={1.5} />
      <pointLight position={[-3, 3, 5]} color="#FFFFFF" intensity={0.5} />

      {/* Floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[12, 6]} />
        <meshStandardMaterial color="#111111" />
      </mesh>

      {/* Grid */}
      <gridHelper args={[12, 12, '#2A2A2A', '#2A2A2A']} position={[0, 0.01, 0]} />

      {/* Bars */}
      {revenueData.map((d, i) => (
        <Bar3D
          key={d.month}
          position={[(i - 5.5) * 0.9, 0, 0]}
          height={(d.value / maxVal) * 3.5}
          label={d.month}
          value={d.value}
        />
      ))}
    </>
  )
}

export default function RevenueChart3D() {
  const [activeTab, setActiveTab] = useState('Monthly')
  const tabs = ['Weekly', 'Monthly', 'Yearly']

  return (
    <div className="card" style={{ height: '100%' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <h4 className="h4-dashboard">Revenue Overview</h4>
        <div style={{ display: 'flex', gap: 4 }}>
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 12,
                fontWeight: 500,
                color: activeTab === tab ? '#FFFFFF' : '#888888',
                background: activeTab === tab ? '#222222' : 'transparent',
                border: 'none',
                borderRadius: 4,
                padding: '4px 12px',
                cursor: 'pointer',
                transition: 'all 150ms ease',
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div style={{ height: 220 }}>
        <Canvas
          camera={{ position: [6, 5, 6], fov: 50 }}
          orthographic={false}
          gl={{ antialias: true, alpha: true }}
          onCreated={({ camera }) => camera.lookAt(0, 1, 0)}
        >
          <BarChartScene />
        </Canvas>
      </div>
    </div>
  )
}
