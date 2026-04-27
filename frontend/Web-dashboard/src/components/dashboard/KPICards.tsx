import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import gsap from 'gsap'
import { kpiData } from '../../data/mockData'
import { TrendingUp, AlertTriangle, Bell } from 'lucide-react'

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const w = 100
  const h = 32

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
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ overflow: 'visible' }}>
      <path d={pathD} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function KPICard({ item, index }: { item: typeof kpiData[0]; index: number }) {
  const [displayValue, setDisplayValue] = useState(0)
  const counterRef = useRef({ val: 0 })
  const hasAnimated = useRef(false)
  const cardRef = useRef<HTMLDivElement>(null)
  const [tilt, setTilt] = useState({ x: 0, y: 0 })

  useEffect(() => {
    if (hasAnimated.current) return
    hasAnimated.current = true
    gsap.to(counterRef.current, {
      val: item.value,
      duration: 1.8,
      ease: 'power2.out',
      onUpdate: () => {
        setDisplayValue(Math.round(counterRef.current.val))
      },
    })
  }, [item.value])

  const formatValue = (val: number) => {
    if (item.prefix === '₹') {
      return `₹${val.toLocaleString('en-IN')}`
    }
    return val.toString()
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    setTilt({ x: y * -12, y: x * 12 })
  }

  const changeColors = {
    success: '#22C55E',
    warning: '#F59E0B',
    error: '#EF4444',
  }
  const changeIcons = {
    success: <TrendingUp size={14} />,
    warning: item.id === 'hitl' ? <Bell size={14} /> : <AlertTriangle size={14} />,
    error: <AlertTriangle size={14} />,
  }

  return (
    <motion.div
      ref={cardRef}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setTilt({ x: 0, y: 0 })}
      style={{
        background: '#1A1A1A',
        border: `1px solid ${item.id === 'hitl' ? undefined : '#2A2A2A'}`,
        borderRadius: 8,
        padding: 24,
        transform: `perspective(800px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
        transition: 'transform 200ms ease',
        animation: item.id === 'hitl' ? 'border-pulse 2s infinite' : undefined,
        borderColor: item.id === 'hitl' ? '#2A2A2A' : undefined,
      }}
    >
      <div
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 13,
          color: '#888888',
          marginBottom: 8,
        }}
      >
        {item.title}
      </div>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div className="text-metric" style={{ fontSize: 36, lineHeight: 1 }}>
            {formatValue(displayValue)}
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              marginTop: 8,
              color: changeColors[item.changeType],
              fontFamily: "'Inter', sans-serif",
              fontSize: 12,
              fontWeight: 500,
            }}
          >
            {changeIcons[item.changeType]}
            <span>{item.change}</span>
            {item.changeLabel && (
              <span style={{ color: '#666666', marginLeft: 4 }}>
                {item.changeLabel}
              </span>
            )}
          </div>
        </div>
        <Sparkline data={item.sparkline} color={item.color} />
      </div>
    </motion.div>
  )
}

export default function KPICards() {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 24,
        marginTop: 24,
      }}
    >
      {kpiData.map((item, i) => (
        <KPICard key={item.id} item={item} index={i} />
      ))}
    </div>
  )
}
