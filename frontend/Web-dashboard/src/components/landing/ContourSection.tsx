import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { motion, useInView } from 'framer-motion'

function ContourWaveField() {
  const meshRef = useRef<THREE.Mesh>(null!)
  const geoRef = useRef<THREE.PlaneGeometry>(null!)

  useFrame(({ clock }) => {
    if (!geoRef.current) return
    const time = clock.getElapsedTime()
    const pos = geoRef.current.attributes.position
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i)
      const y = pos.getY(i)
      const z =
        Math.sin(x * 1.5 + time * 0.8) * 0.4 +
        Math.sin(y * 2.0 + time * 0.6) * 0.3 +
        Math.sin((x + y) * 1.0 + time * 0.4) * 0.2
      pos.setZ(i, z)
    }
    pos.needsUpdate = true
    geoRef.current.computeVertexNormals()
  })

  return (
    <group rotation={[-0.5, 0, 0]}>
      {/* Wireframe overlay */}
      <mesh ref={meshRef}>
        <planeGeometry ref={geoRef} args={[8, 8, 80, 80]} />
        <meshStandardMaterial
          wireframe
          color="#F96A2A"
          opacity={0.35}
          transparent
        />
      </mesh>
      {/* Solid fill behind */}
      <mesh position={[0, 0, -0.01]}>
        <planeGeometry args={[8, 8, 80, 80]} />
        <meshStandardMaterial color="#1A1A1A" />
      </mesh>
    </group>
  )
}

function ContourScene() {
  return (
    <>
      <ambientLight intensity={0.5} />
      <pointLight position={[2, 2, 2]} color="#F96A2A" intensity={2} />
      <ContourWaveField />
    </>
  )
}

export default function ContourSection() {
  const sectionRef = useRef(null)
  const isInView = useInView(sectionRef, { once: true, margin: '-100px' })

  return (
    <section
      ref={sectionRef}
      style={{
        width: '100%',
        height: 600,
        background: '#080808',
        overflow: 'hidden',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      {/* Left Text */}
      <div
        style={{
          width: '40%',
          paddingLeft: '10%',
          zIndex: 2,
          position: 'relative',
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <span className="section-label">AUTONOMOUS AGENT MESH</span>
          <h2
            className="h2-section"
            style={{ marginTop: 16, lineHeight: 1.1 }}
          >
            6 agents.
            <br />
            One orchestrator.
            <br />
            Zero chaos.
          </h2>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 16,
              color: '#888888',
              marginTop: 20,
              lineHeight: 1.7,
              maxWidth: 380,
            }}
          >
            The LangGraph orchestrator coordinates all agents using ReAct
            loops — planning, acting, and escalating only when your approval
            is needed.
          </p>
          <a
            href="#"
            style={{
              display: 'inline-block',
              marginTop: 24,
              fontFamily: "'Inter', sans-serif",
              fontSize: 14,
              fontWeight: 600,
              color: '#F96A2A',
            }}
          >
            See the architecture →
          </a>
        </motion.div>
      </div>

      {/* Right 3D Contour */}
      <motion.div
        initial={{ opacity: 0, x: 80 }}
        animate={isInView ? { opacity: 1, x: 0 } : {}}
        transition={{ duration: 0.7 }}
        style={{
          width: '60%',
          height: '100%',
          position: 'relative',
        }}
      >
        <Canvas
          camera={{ position: [0, 3, 5] }}
          style={{ background: 'transparent' }}
          gl={{ antialias: true, alpha: true }}
          onCreated={({ camera }) => camera.lookAt(0, 0, 0)}
        >
          <ContourScene />
        </Canvas>
      </motion.div>
    </section>
  )
}
