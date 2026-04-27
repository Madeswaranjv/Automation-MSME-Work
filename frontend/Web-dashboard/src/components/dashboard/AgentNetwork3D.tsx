import { useRef, useMemo, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import * as THREE from 'three'

// ── Agent definitions ──
const agents = [
  { name: 'Billing', geometry: 'octahedron', color: '#F96A2A', emissive: '#F96A2A', speed: 0.4, tilt: 10, size: 0.35 },
  { name: 'Inventory', geometry: 'tetrahedron', color: '#FF8C42', emissive: '#FF8C42', speed: 0.55, tilt: -12, size: 0.35 },
  { name: 'Accounting', geometry: 'box', color: '#CCCCCC', emissive: '#CCCCCC', speed: 0.35, tilt: 8, size: 0.5 },
  { name: 'HR', geometry: 'sphere', color: '#F96A2A', emissive: '#F96A2A', speed: 0.65, tilt: -15, size: 0.28 },
  { name: 'CRM', geometry: 'cone', color: '#FF8C42', emissive: '#FF8C42', speed: 0.5, tilt: 5, size: 0.3 },
  { name: 'Credit', geometry: 'dodecahedron', color: '#888888', emissive: '#888888', speed: 0.45, tilt: -8, size: 0.32 },
]

// ── Orchestrator Center Node ──
function OrchestratorNode() {
  const meshRef = useRef<THREE.Mesh>(null!)
  const wireRef = useRef<THREE.Mesh>(null!)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    if (meshRef.current) {
      const s = Math.sin(t * 1.5) * 0.05 + 1
      meshRef.current.scale.set(s, s, s)
      meshRef.current.rotation.y += 0.005
    }
    if (wireRef.current) {
      wireRef.current.rotation.y -= 0.002
    }
  })

  return (
    <group>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[0.8, 1]} />
        <meshStandardMaterial
          color="#F96A2A"
          emissive="#FF5500"
          emissiveIntensity={2.0} // Fix B
          metalness={0.0} // Fix B
          roughness={0.3} // Fix B
        />
      </mesh>
      <mesh ref={wireRef}>
        <sphereGeometry args={[1.0, 16, 16]} />
        <meshBasicMaterial wireframe color="#F96A2A" transparent opacity={0.5} /> {/* Fix B */}
      </mesh>
    </group>
  )
}

// ── Agent Geometry Helper ──
function AgentGeometry({ type, size }: { type: string; size: number }) {
  switch (type) {
    case 'octahedron': return <octahedronGeometry args={[size]} />
    case 'tetrahedron': return <tetrahedronGeometry args={[size]} />
    case 'box': return <boxGeometry args={[size, size, size]} />
    case 'sphere': return <sphereGeometry args={[size, 16, 16]} />
    case 'cone': return <coneGeometry args={[size, size * 1.8, 16]} />
    case 'dodecahedron': return <dodecahedronGeometry args={[size]} />
    default: return <sphereGeometry args={[size, 16, 16]} />
  }
}

// ── Orbiting Agent Node ──
function AgentNode({ agent, index }: { agent: typeof agents[0]; index: number }) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const groupRef = useRef<THREE.Group>(null!)
  const startAngle = (index / agents.length) * Math.PI * 2

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const angle = startAngle + t * agent.speed
    const semiMajor = 3.2
    const semiMinor = 2.0
    const tiltRad = (agent.tilt * Math.PI) / 180

    if (groupRef.current) {
      groupRef.current.position.x = Math.cos(angle) * semiMajor
      groupRef.current.position.z = Math.sin(angle) * semiMinor
      groupRef.current.position.y = Math.sin(angle) * Math.sin(tiltRad) * 0.5
    }
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.02
    }
  })

  return (
    <group ref={groupRef}>
      <mesh ref={meshRef}>
        <AgentGeometry type={agent.geometry} size={agent.size} />
        <meshStandardMaterial
          color={agent.color}
          emissive={agent.emissive}
          emissiveIntensity={1.5} // Fix B
          metalness={0.0} // Fix B
          roughness={0.3} // Fix B
        />
      </mesh>
      {/* Fix E: used Html instead of Text */}
      <Html
        position={[0, -agent.size - 0.2, 0]}
        center
        style={{
          fontSize: '10px',
          color: '#CCCCCC',
          fontFamily: 'Inter, sans-serif',
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
          userSelect: 'none',
        }}
      >
        {agent.name}
      </Html>
    </group>
  )
}

// ── Connection Line (Tube fallback - Fix G) ──
function DynamicTube({ agent, index }: { agent: typeof agents[0], index: number }) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const timerOffset = useMemo(() => Math.random() * 5 + 4, [])
  const startAngle = (index / agents.length) * Math.PI * 2

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const angle = startAngle + t * agent.speed
    const semiMajor = 3.2
    const semiMinor = 2.0
    const tiltRad = (agent.tilt * Math.PI) / 180

    const agentX = Math.cos(angle) * semiMajor
    const agentZ = Math.sin(angle) * semiMinor
    const agentY = Math.sin(angle) * Math.sin(tiltRad) * 0.5

    if (meshRef.current) {
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(agentX, agentY, agentZ)
      ])
      const geo = new THREE.TubeGeometry(curve, 8, 0.01, 4, false)
      if (meshRef.current.geometry) meshRef.current.geometry.dispose()
      meshRef.current.geometry = geo

      const localTime = (t + timerOffset) % timerOffset
      const isFlashing = localTime < 0.4
      const mat = meshRef.current.material as THREE.MeshBasicMaterial
      mat.color.set(isFlashing ? '#F96A2A' : '#2A2A2A')
      mat.opacity = isFlashing ? 1 : 0.5
    }
  })

  // Initial render with a dummy curve
  const initialCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(1, 0, 0)
  ])

  return (
    <mesh ref={meshRef}>
      <tubeGeometry args={[initialCurve, 8, 0.01, 4, false]} />
      <meshBasicMaterial color="#2A2A2A" opacity={0.5} transparent />
    </mesh>
  )
}

function ConnectionLines() {
  return (
    <group>
      {agents.map((agent, i) => (
        <DynamicTube key={agent.name} agent={agent} index={i} />
      ))}
    </group>
  )
}

// ── Data Particles ──
function DataParticles() {
  const particlesRef = useRef<THREE.Group>(null!)

  useFrame(({ clock }) => {
    if (!particlesRef.current) return
    const t = clock.getElapsedTime()

    particlesRef.current.children.forEach((particle, i) => {
      const agentIdx = Math.floor(i / 2)
      const agent = agents[agentIdx]
      const direction = i % 2 === 0 ? 1 : -1
      const progress = ((t * 0.5 * direction + i * 0.3) % 1 + 1) % 1

      const startAngle = (agentIdx / agents.length) * Math.PI * 2
      const angle = startAngle + t * agent.speed
      const semiMajor = 3.2
      const semiMinor = 2.0
      const tiltRad = (agent.tilt * Math.PI) / 180

      const targetX = Math.cos(angle) * semiMajor
      const targetZ = Math.sin(angle) * semiMinor
      const targetY = Math.sin(angle) * Math.sin(tiltRad) * 0.5

      particle.position.x = targetX * progress
      particle.position.y = targetY * progress
      particle.position.z = targetZ * progress
    })
  })

  return (
    <group ref={particlesRef}>
      {agents.flatMap((agent) =>
        [0, 1].map((j) => (
          <mesh key={`${agent.name}-${j}`}>
            <sphereGeometry args={[0.04, 8, 8]} />
            <meshBasicMaterial color="#F96A2A" />
          </mesh>
        ))
      )}
    </group>
  )
}

// ── Full Scene Wrapped inside Suspense ──
function OrchestratorScene() {
  return (
    <>
      <ambientLight intensity={1.2} /> {/* Fix B */}
      <pointLight position={[5, 5, 5]} color="#F96A2A" intensity={8} /> {/* Fix B */}
      <pointLight position={[-5, -3, 3]} color="#FFFFFF" intensity={4} /> {/* Fix B */}
      <pointLight position={[0, -5, 5]} color="#FF8C42" intensity={3} /> {/* Fix B */}

      <OrchestratorNode />
      {agents.map((agent, i) => (
        <AgentNode key={agent.name} agent={agent} index={i} />
      ))}
      <ConnectionLines />
      <DataParticles />

      {/* Fix F */}
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate={true}
        autoRotateSpeed={0.6}
      />
    </>
  )
}

// ── Main Export ──
export default function AgentNetwork3D() {
  return (
    <div
      style={{
        width: '100%',
        minHeight: 320,
        background: '#111111',
        border: '1px solid #2A2A2A',
        borderRadius: 8,
        overflow: 'hidden',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Overlay Labels */}
      <div
        style={{
          position: 'absolute',
          top: 16,
          left: 20,
          zIndex: 10,
        }}
      >
        <div
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 13,
            fontWeight: 600,
            color: '#CCCCCC',
          }}
        >
          Orchestrator Agent Network
        </div>
        <div
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 11,
            color: '#666666',
            marginTop: 4,
          }}
        >
          6 Agents · ReAct Loop · Live
        </div>
      </div>

      {/* Active Status */}
      <div
        style={{
          position: 'absolute',
          top: 16,
          right: 20,
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#22C55E',
            animation: 'dot-blink 1.5s infinite',
          }}
        />
        <span
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 11,
            color: '#22C55E',
            fontWeight: 600,
          }}
        >
          ACTIVE
        </span>
      </div>

      {/* Fix A: Ensure Canvas is wrapped in explicitly sized container */}
      <div style={{ width: '100%', height: '300px', flexGrow: 1, position: 'relative', marginTop: 24 }}>
        {/* Fix C: Add near, far, fov and specific position */}
        <Canvas
          style={{ width: '100%', height: '100%' }}
          gl={{ antialias: true, alpha: true }}
          camera={{ position: [0, 0, 7], fov: 55, near: 0.1, far: 100 }}
          frameloop="always"
        >
          {/* Fix D: Wrap inside Suspense */}
          <Suspense fallback={null}>
            <OrchestratorScene />
          </Suspense>
        </Canvas>
      </div>
    </div>
  )
}
