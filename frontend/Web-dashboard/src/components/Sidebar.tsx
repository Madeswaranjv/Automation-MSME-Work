import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Receipt,
  Package,
  BarChart3,
  Users,
  MessageSquare,
  CreditCard,
  BellRing,
  Settings,
} from 'lucide-react'

const iconMap: Record<string, any> = {
  LayoutDashboard,
  Receipt,
  Package,
  BarChart3,
  Users,
  MessageSquare,
  CreditCard,
  BellRing,
  Settings,
}

const navItems = [
  { label: 'Dashboard', icon: 'LayoutDashboard', path: '/dashboard' },
  { label: 'Billing', icon: 'Receipt', path: '/dashboard' },
  { label: 'Inventory', icon: 'Package', path: '/inventory' },
  { label: 'Accounting', icon: 'BarChart3', path: '/dashboard' },
  { label: 'HR & Payroll', icon: 'Users', path: '/dashboard' },
  { label: 'CRM', icon: 'MessageSquare', path: '/dashboard' },
  { label: 'Credit', icon: 'CreditCard', path: '/dashboard' },
]

const systemItems = [
  { label: 'HITL Inbox', icon: 'BellRing', path: '/hitl', badge: 3 },
  { label: 'Settings', icon: 'Settings', path: '/dashboard' },
]

export default function Sidebar() {
  const location = useLocation()
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)

  const isActive = (label: string) => {
    if (label === 'Dashboard' && location.pathname === '/dashboard') return true
    if (label === 'Inventory' && location.pathname === '/inventory') return true
    if (label === 'HITL Inbox' && location.pathname === '/hitl') return true
    return false
  }

  const renderNavItem = (item: { label: string; icon: string; path: string; badge?: number }) => {
    const Icon = iconMap[item.icon]
    const active = isActive(item.label)
    const hovered = hoveredItem === item.label

    return (
      <Link
        key={item.label}
        to={item.path}
        style={{ textDecoration: 'none' }}
        onMouseEnter={() => setHoveredItem(item.label)}
        onMouseLeave={() => setHoveredItem(null)}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            height: 40,
            paddingLeft: active ? 13 : 16,
            borderRadius: 6,
            color: active ? '#FFFFFF' : hovered ? '#CCCCCC' : '#666666',
            background: active ? '#222222' : hovered ? '#1A1A1A' : 'transparent',
            borderLeft: active ? '3px solid #F96A2A' : '3px solid transparent',
            transition: 'all 150ms ease',
            cursor: 'pointer',
            position: 'relative',
          }}
        >
          {Icon && <Icon size={16} />}
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 14,
              fontWeight: active ? 600 : 500,
            }}
          >
            {item.label}
          </span>
          {item.badge !== undefined && (
            <span
              style={{
                position: 'absolute',
                right: 12,
                background: '#F96A2A',
                color: '#FFFFFF',
                fontSize: 10,
                fontWeight: 700,
                fontFamily: "'Inter', sans-serif",
                padding: '2px 6px',
                borderRadius: 10,
                minWidth: 18,
                textAlign: 'center',
              }}
            >
              {item.badge}
            </span>
          )}
        </div>
      </Link>
    )
  }

  return (
    <aside
      style={{
        position: 'fixed',
        left: 0,
        top: 0,
        width: 240,
        height: '100vh',
        background: '#111111',
        borderRight: '1px solid #2A2A2A',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
      }}
    >
      {/* Logo Area */}
      <Link
        to="/"
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '0 20px',
          textDecoration: 'none',
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            background: '#F96A2A',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800,
            fontSize: 18,
            color: '#FFFFFF',
          }}
        >
          M
        </div>
        <span
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: 17,
            fontWeight: 700,
            color: '#FFFFFF',
          }}
        >
          MSME AI
        </span>
      </Link>

      {/* Main Nav */}
      <div style={{ padding: '16px 12px 8px', flex: 1 }}>
        <span
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 11,
            fontWeight: 700,
            color: '#444444',
            textTransform: 'uppercase',
            letterSpacing: 1.5,
            paddingLeft: 16,
            display: 'block',
            marginBottom: 8,
          }}
        >
          MODULES
        </span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {navItems.map(renderNavItem)}
        </div>

        <span
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 11,
            fontWeight: 700,
            color: '#444444',
            textTransform: 'uppercase',
            letterSpacing: 1.5,
            paddingLeft: 16,
            display: 'block',
            marginTop: 24,
            marginBottom: 8,
          }}
        >
          SYSTEM
        </span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {systemItems.map(renderNavItem)}
        </div>
      </div>

      {/* User Profile */}
      <div
        style={{
          padding: '16px 20px',
          borderTop: '1px solid #2A2A2A',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #444444, #F96A2A)',
            flexShrink: 0,
          }}
        />
        <div>
          <div
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              fontWeight: 500,
              color: '#FFFFFF',
            }}
          >
            Business Owner
          </div>
          <div
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 12,
              color: '#666666',
            }}
          >
            Admin
          </div>
        </div>
      </div>
    </aside>
  )
}
