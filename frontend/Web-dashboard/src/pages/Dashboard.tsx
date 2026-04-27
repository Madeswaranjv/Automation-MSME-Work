import { useState } from 'react'
import DashboardLayout from '../layouts/DashboardLayout'
import AgentNetwork3D from '../components/dashboard/AgentNetwork3D'
import KPICards from '../components/dashboard/KPICards'
import RevenueChart3D from '../components/dashboard/RevenueChart3D'
import RevenueSources from '../components/dashboard/RevenueSources'
import AgentActivityLog from '../components/dashboard/AgentActivityLog'
import ReasoningDrawer from '../components/dashboard/ReasoningDrawer'

export default function Dashboard() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <DashboardLayout>
      {/* Header with reasoning trigger — override the layout's button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 className="h2-section" style={{ fontSize: 28 }}>Dashboard</h2>
          <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#666666', marginTop: 4 }}>
            AI agent operations overview
          </p>
        </div>
        <button
          className="btn-secondary"
          onClick={() => setDrawerOpen(true)}
          style={{ padding: '8px 16px', fontSize: 12 }}
        >
          View Agent Reasoning
        </button>
      </div>

      {/* Agent Network 3D Visualizer */}
      <AgentNetwork3D />

      {/* KPI Cards */}
      <KPICards />

      {/* Revenue Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '8fr 4fr',
          gap: 24,
          marginTop: 24,
        }}
      >
        <RevenueChart3D />
        <RevenueSources />
      </div>

      {/* Activity Log */}
      <div style={{ marginTop: 24 }}>
        <AgentActivityLog />
      </div>

      {/* Reasoning Drawer */}
      <ReasoningDrawer isOpen={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </DashboardLayout>
  )
}
