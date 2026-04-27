import { useRef, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

// ── Card 1: Invoice Document ──
function InvoiceDoc() {
  const groupRef = useRef<THREE.Group>(null!)
  const gemRef = useRef<THREE.Mesh>(null!)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    if (groupRef.current) {
      groupRef.current.position.y = Math.sin(t * 0.8) * 0.1
    }
    if (gemRef.current) {
      gemRef.current.position.y = 1.1 + Math.sin(t * 1.2) * 0.15
      gemRef.current.rotation.y += 0.02
    }
  })

  return (
    <group ref={groupRef} rotation={[0.15, -0.2, 0.05]}>
      <mesh>
        <boxGeometry args={[1.2, 1.6, 0.05]} />
        <meshStandardMaterial color="#F5F5F5" roughness={0.4} />
      </mesh>
      {/* Lines on document */}
      {[0.4, 0.15, -0.1, -0.35].map((y, i) => (
        <mesh key={i} position={[0, y, 0.03]}>
          <boxGeometry args={[0.8 - i * 0.1, 0.04, 0.01]} />
          <meshStandardMaterial color="#CCCCCC" />
        </mesh>
      ))}
      <mesh ref={gemRef} position={[0, 1.1, 0]}>
        <octahedronGeometry args={[0.2]} />
        <meshStandardMaterial
          color="#F96A2A"
          emissive="#FF5500"
          emissiveIntensity={0.6}
          metalness={0.5}
          roughness={0.3}
        />
      </mesh>
    </group>
  )
}

// ── Card 2: Warehouse Box ──
function WarehouseBox() {
  const groupRef = useRef<THREE.Group>(null!)
  const orbitRef = useRef<THREE.Mesh>(null!)
  const barRef = useRef<THREE.Mesh>(null!)
  const barScaleRef = useRef(0)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    if (groupRef.current) {
      groupRef.current.position.y = Math.sin(t * 0.8 + 1) * 0.1
    }
    if (orbitRef.current) {
      orbitRef.current.position.x = Math.cos(t * 1.5) * 1.0
      orbitRef.current.position.z = Math.sin(t * 1.5) * 1.0
      orbitRef.current.position.y = Math.sin(t * 2) * 0.2 + 0.3
      orbitRef.current.rotation.y += 0.03
    }
    if (barRef.current && barScaleRef.current < 0.7) {
      barScaleRef.current = Math.min(barScaleRef.current + 0.003, 0.7)
      barRef.current.scale.x = barScaleRef.current / 0.7
    }
  })

  return (
    <group ref={groupRef} rotation={[0.2, -0.4, 0]}>
      <mesh>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="#222222" roughness={0.6} />
      </mesh>
      {/* Progress bar face */}
      <mesh ref={barRef} position={[0, 0, 0.51]}>
        <boxGeometry args={[0.7, 0.08, 0.01]} />
        <meshStandardMaterial color="#F96A2A" emissive="#FF5500" emissiveIntensity={0.3} />
      </mesh>
      <mesh ref={orbitRef}>
        <tetrahedronGeometry args={[0.15]} />
        <meshStandardMaterial
          color="#F96A2A"
          emissive="#FF5500"
          emissiveIntensity={0.5}
        />
      </mesh>
    </group>
  )
}

// ── Card 3: Orchestrator Mini ──
function OrchestratorMini() {
  const centerRef = useRef<THREE.Mesh>(null!)
  const nodesRef = useRef<THREE.Group>(null!)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    if (centerRef.current) {
      centerRef.current.rotation.y += 0.01
      centerRef.current.position.y = Math.sin(t * 0.8 + 2) * 0.1
      const s = Math.sin(t * 1.5) * 0.05 + 1
      centerRef.current.scale.set(s, s, s)
    }
    if (nodesRef.current) {
      nodesRef.current.rotation.y += 0.008
      nodesRef.current.position.y = Math.sin(t * 0.8 + 2) * 0.1
    }
  })

  return (
    <group>
      <mesh ref={centerRef}>
        <icosahedronGeometry args={[0.45, 1]} />
        <meshStandardMaterial
          color="#F96A2A"
          emissive="#FF5500"
          emissiveIntensity={0.4}
          metalness={0.4}
          roughness={0.4}
        />
      </mesh>
      <group ref={nodesRef}>
        {[0, 1, 2].map((i) => {
          const angle = (i * Math.PI * 2) / 3
          return (
            <mesh
              key={i}
              position={[
                Math.cos(angle) * 1.0,
                Math.sin(angle) * 0.3,
                Math.sin(angle) * 1.0,
              ]}
            >
              <sphereGeometry args={[0.12, 12, 12]} />
              <meshStandardMaterial
                color={['#F96A2A', '#FF8C42', '#888888'][i]}
                emissive={['#FF5500', '#FF8C42', '#666666'][i]}
                emissiveIntensity={0.4}
              />
            </mesh>
          )
        })}
      </group>
    </group>
  )
}

function MiniScene({ children }: { children: React.ReactNode }) {
  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[2, 2, 2]} color="#F96A2A" intensity={1.5} />
      <pointLight position={[-2, 1, -1]} color="#FFFFFF" intensity={0.4} />
      {children}
    </>
  )
}

const features = [
  {
    SceneComponent: InvoiceDoc,
    title: 'Smart GST Billing',
    body: 'Auto HSN validation, IRN filing, UPI QR on every invoice. Agent handles overdue follow-ups.',
  },
  {
    SceneComponent: WarehouseBox,
    title: 'AI Stock Forecasting',
    body: '7-day ML stockout prediction. Auto purchase orders. 30-day expiry alerts.',
  },
  {
    SceneComponent: OrchestratorMini,
    title: '6 Autonomous Agents',
    body: 'LangGraph orchestrator coordinates Billing, Inventory, Accounting, HR, CRM, and Credit agents autonomously.',
  },
]

export default function FeaturesRow() {
  const sectionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return
    const cards = sectionRef.current.querySelectorAll('.feature-card')
    gsap.fromTo(
      cards,
      { opacity: 0, y: 40 },
      {
        opacity: 1,
        y: 0,
        duration: 0.6,
        stagger: 0.2,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top 80%',
          once: true,
        },
      }
    )
  }, [])

  return (
    <section
      ref={sectionRef}
      style={{
        width: '100%',
        background: '#0D0D0D',
        padding: '96px 10%',
      }}
    >
      <h2
        className="h2-section"
        style={{ textAlign: 'center', marginBottom: 64 }}
      >
        Everything your MSME needs
      </h2>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: 40,
        }}
      >
        {features.map((feat, i) => (
          <div
            key={i}
            className="feature-card"
            style={{
              width: '30%',
              textAlign: 'center',
              opacity: 0,
            }}
          >
            <div style={{ width: 200, height: 200, margin: '0 auto' }}>
              <Canvas
                camera={{ position: [0, 0, 3.5], fov: 50 }}
                style={{ background: 'transparent' }}
                gl={{ antialias: true, alpha: true }}
              >
                <MiniScene>
                  <feat.SceneComponent />
                </MiniScene>
              </Canvas>
            </div>
            <h3
              style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontSize: 20,
                fontWeight: 600,
                color: '#FFFFFF',
                marginTop: 20,
              }}
            >
              {feat.title}
            </h3>
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 15,
                color: '#888888',
                marginTop: 12,
                lineHeight: 1.6,
              }}
            >
              {feat.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
