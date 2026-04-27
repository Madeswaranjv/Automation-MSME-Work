import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Line } from '@react-three/drei'
import * as THREE from 'three'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'

// ── Particle Field (Background) ──
function ParticleField() {
  const ref = useRef<THREE.Points>(null!)
  const positions = useMemo(() => {
    const pos = new Float32Array(300 * 3)
    for (let i = 0; i < 300; i++) {
      const r = 4 * Math.cbrt(Math.random())
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i * 3 + 2] = r * Math.cos(phi)
    }
    return pos
  }, [])

  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.y += 0.0004
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
          count={300}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.012}
        color="#F96A2A"
        transparent
        opacity={0.35}
        sizeAttenuation
      />
    </points>
  )
}

// ── Connection Line (Orchestrator to Agent) ──
function ConnectionLine({
  start,
  end,
}: {
  start: [number, number, number]
  end: [number, number, number]
}) {
  const lineRef = useRef<any>(null!)
  const timerOffset = useMemo(() => Math.random() * 5 + 4, [])
  
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    // Flash #F96A2A for 400ms (0.4s) every random interval between 4-9s
    const localTime = (t + timerOffset) % timerOffset
    const isFlashing = localTime < 0.4
    if (lineRef.current) {
      lineRef.current.material.color.set(isFlashing ? '#F96A2A' : '#2A2A2A')
    }
  })

  return (
    <Line
      ref={lineRef}
      points={[start, end]}
      color="#2A2A2A"
      lineWidth={1}
    />
  )
}

// ── Traveling Data Particle ──
function DataParticle({
  start,
  end,
  speed,
  offset,
}: {
  start: THREE.Vector3
  end: THREE.Vector3
  speed: number
  offset: number
}) {
  const ref = useRef<THREE.Mesh>(null!)
  
  useFrame(({ clock }) => {
    if (ref.current) {
      const t = clock.getElapsedTime()
      const progress = (Math.sin(t * speed + offset) + 1) / 2
      ref.current.position.lerpVectors(start, end, progress)
    }
  })

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.04]} />
      <meshBasicMaterial color="#F96A2A" />
    </mesh>
  )
}

// ── Individual Agent Node ──
function AgentNode({ agent, index }: { agent: any; index: number }) {
  const ref = useRef<THREE.Mesh>(null!)
  
  useFrame(({ clock }) => {
    if (ref.current) {
      const t = clock.getElapsedTime()
      ref.current.rotation.y += 0.01
      ref.current.position.y += Math.sin(t * 0.9 + index * 1.1) * 0.002
    }
  })

  return (
    <mesh ref={ref} position={agent.pos.clone()}>
      {agent.geo}
      <meshStandardMaterial
        color={agent.color}
        emissive={agent.emissive}
        emissiveIntensity={agent.eIntensity}
        metalness={0.3}
        roughness={0.5}
      />
    </mesh>
  )
}

// ── Neural Agent Mesh Cluster ──
function AgentMeshCluster() {
  const groupRef = useRef<THREE.Group>(null!)
  const orchestratorRef = useRef<THREE.Mesh>(null!)
  const shellRef = useRef<THREE.Mesh>(null!)

  const agents = useMemo(() => [
    { name: 'Billing', pos: new THREE.Vector3(2.0, 1.0, 0.5), geo: <octahedronGeometry args={[0.28]} />, color: '#F96A2A', emissive: '#F96A2A', eIntensity: 0.5 },
    { name: 'Inventory', pos: new THREE.Vector3(-2.0, 0.8, -0.3), geo: <tetrahedronGeometry args={[0.28]} />, color: '#FF8C42', emissive: '#FF8C42', eIntensity: 0.4 },
    { name: 'Accounting', pos: new THREE.Vector3(0.5, 2.0, -1.0), geo: <boxGeometry args={[0.42, 0.42, 0.42]} />, color: '#CCCCCC', emissive: '#888888', eIntensity: 0.2 },
    { name: 'HR', pos: new THREE.Vector3(0.3, -2.0, 0.8), geo: <sphereGeometry args={[0.24, 16, 16]} />, color: '#F96A2A', emissive: '#F96A2A', eIntensity: 0.4 },
    { name: 'CRM', pos: new THREE.Vector3(-1.5, -0.8, 1.5), geo: <coneGeometry args={[0.25, 0.45, 16]} />, color: '#FF8C42', emissive: '#FF8C42', eIntensity: 0.3 },
    { name: 'Credit', pos: new THREE.Vector3(1.2, 0.2, -2.0), geo: <dodecahedronGeometry args={[0.26]} />, color: '#888888', emissive: '#888888', eIntensity: 0.2 },
  ], [])

  const origin = useMemo(() => new THREE.Vector3(0, 0, 0), [])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    if (orchestratorRef.current) {
      orchestratorRef.current.rotation.y += 0.004
      const s = 0.97 + Math.sin(t * 1.4) * 0.04
      orchestratorRef.current.scale.set(s, s, s)
    }
    if (shellRef.current) {
      shellRef.current.rotation.y -= 0.002
    }
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0015
      groupRef.current.rotation.x = Math.sin(t * 0.2) * 0.08
    }
  })

  // Pre-calculate speeds and offsets to avoid random jumps during re-renders
  const particleConfigs = useMemo(() => {
    return agents.map((_, i) => ({
      p1: { speed: 0.8 + Math.random() * 0.6, offset: i * 0.5 },
      p2: { speed: 0.8 + Math.random() * 0.6, offset: i * 0.5 + 1.5 }
    }))
  }, [agents])

  return (
    <group ref={groupRef}>
      {/* Central Orchestrator */}
      <mesh ref={orchestratorRef}>
        <icosahedronGeometry args={[0.7, 2]} />
        <meshStandardMaterial
          color="#F96A2A"
          emissive="#FF5500"
          emissiveIntensity={0.6}
          metalness={0.4}
          roughness={0.4}
        />
      </mesh>

      {/* Wireframe Shell */}
      <mesh ref={shellRef}>
        <sphereGeometry args={[0.85, 16, 16]} />
        <meshBasicMaterial wireframe color="#F96A2A" transparent opacity={0.12} />
      </mesh>

      {/* Agents, Lines, and Particles */}
      {agents.map((agent, i) => (
        <group key={agent.name}>
          <AgentNode agent={agent} index={i} />
          
          <ConnectionLine start={[0,0,0]} end={[agent.pos.x, agent.pos.y, agent.pos.z]} />
          
          <DataParticle start={origin} end={agent.pos} speed={particleConfigs[i].p1.speed} offset={particleConfigs[i].p1.offset} />
          <DataParticle start={origin} end={agent.pos} speed={particleConfigs[i].p2.speed} offset={particleConfigs[i].p2.offset} />
        </group>
      ))}
    </group>
  )
}

// ── Hero 3D Scene ──
function HeroScene() {
  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[4, 3, 4]} color="#F96A2A" intensity={3.5} />
      <pointLight position={[-3, -2, -1]} color="#CCCCCC" intensity={0.8} />
      <pointLight position={[0, 4, -3]} color="#FF8C42" intensity={1.0} />

      <AgentMeshCluster />
      <ParticleField />
    </>
  )
}

// ── Main Hero Section ──
export default function HeroSection() {
  return (
    <section
      id="hero-section"
      style={{
        width: '100%',
        minHeight: '100vh',
        background: '#080808',
        position: 'relative',
        overflow: 'hidden',
        paddingTop: 64,
      }}
    >
      {/* Background Dot Grid */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle, #2A2A2A 1px, transparent 1px)',
          backgroundSize: '32px 32px',
          opacity: 0.4,
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      {/* Left Text Content */}
      <div
        style={{
          position: 'absolute',
          left: '10%',
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 10,
          maxWidth: 520,
          paddingTop: 24,
        }}
      >
        {/* Eyebrow Tag */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
        >
          <span
            style={{
              display: 'inline-block',
              border: '1px solid #F96A2A',
              borderRadius: 100,
              padding: '4px 14px',
              fontFamily: "'Inter', sans-serif",
              fontSize: 12,
              fontWeight: 600,
              color: '#F96A2A',
            }}
          >
            🤖 Agentic AI for Indian MSMEs
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          className="h1-hero"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.6 }}
          style={{ marginTop: 24 }}
        >
          Run your business
          <br />
          on autonomous
          <br />
          AI <span style={{ color: '#F96A2A' }}>agents</span>.
        </motion.h1>

        {/* Sub-headline */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.45, duration: 0.5 }}
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 18,
            color: '#888888',
            maxWidth: 440,
            lineHeight: 1.7,
            marginTop: 24,
          }}
        >
          6 specialized agents handle Billing, Inventory, Accounting,
          HR, CRM, and Credit — fully automated, privacy-first,
          India-built. Your data never leaves your machine.
        </motion.p>

        {/* CTA Row */}
        <div style={{ display: 'flex', gap: 16, marginTop: 40 }}>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6, duration: 0.5 }}
          >
            <Link to="/dashboard">
              <button
                className="btn-primary"
                style={{
                  padding: '14px 28px',
                  fontSize: 15,
                  fontWeight: 700,
                }}
              >
                Start Free Demo
              </button>
            </Link>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.7, duration: 0.5 }}
          >
            <button
              className="btn-secondary"
              style={{ padding: '14px 28px', fontSize: 15 }}
            >
              View Architecture
            </button>
          </motion.div>
        </div>

        {/* Trust Strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9, duration: 0.5 }}
          style={{
            marginTop: 48,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex' }}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  background: `linear-gradient(135deg, #F96A2A, #FF8C42)`,
                  border: '2px solid #080808',
                  marginLeft: i > 0 ? -8 : 0,
                  opacity: 1 - i * 0.2,
                }}
              />
            ))}
          </div>
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              color: '#444444',
            }}
          >
            Trusted by 500+ Indian MSMEs
          </span>
        </motion.div>
      </div>

      {/* Right 3D Canvas */}
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          width: '55%',
          height: '100%',
          zIndex: 1,
        }}
      >
        {/* Light Ray Effect */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'radial-gradient(ellipse 60% 80% at 65% 40%, rgba(249,106,42,0.12) 0%, transparent 70%)',
            zIndex: 2,
            pointerEvents: 'none',
          }}
        />
        <Canvas
          camera={{ position: [0, 0, 7], fov: 60 }}
          style={{ background: 'transparent' }}
          gl={{ antialias: true, alpha: true }}
        >
          <HeroScene />
        </Canvas>
      </div>
    </section>
  )
}
