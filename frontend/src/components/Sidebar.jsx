import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Table,
  AlertTriangle,
  Building2,
  ShieldCheck,
  ScrollText,
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Control Tower', icon: LayoutDashboard, end: true },
  { to: '/reconciliation', label: 'Reconciliation', icon: Table },
  { to: '/exceptions', label: 'Exceptions', icon: AlertTriangle },
  { to: '/vendors', label: 'Vendors', icon: Building2 },
  { to: '/close-review', label: 'Close Review', icon: ShieldCheck },
  { to: '/audit', label: 'Audit', icon: ScrollText },
]

export default function Sidebar({ hasBatch }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      onMouseEnter={() => setExpanded(true)}
      onMouseLeave={() => setExpanded(false)}
      style={{
        width: expanded ? 224 : 56,
        transition: 'width 150ms ease',
        background: 'var(--color-surface)',
        borderRight: '1px solid var(--color-border)',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        zIndex: 10,
      }}
    >
      <div style={{ padding: '18px 16px', whiteSpace: 'nowrap' }}>
        <span className="font-sans" style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-1)' }}>
          {expanded ? 'SettleSync' : 'SS'}
        </span>
      </div>

      <nav style={{ flex: 1, padding: '8px' }}>
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `sidebar-link${isActive ? ' sidebar-link-active' : ''}`}
          >
            <Icon size={20} style={{ flexShrink: 0 }} />
            {expanded && (
              <span className="font-sans" style={{ fontSize: 14 }}>
                {label}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: '14px 16px', borderTop: '1px solid var(--color-border)' }}>
        <div className="flex items-center gap-2" style={{ whiteSpace: 'nowrap' }}>
          <span
            className={hasBatch ? 'pulse-dot' : ''}
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: hasBatch ? 'var(--color-emerald)' : '#475569',
              flexShrink: 0,
            }}
          />
          {expanded && (
            <span className="font-sans" style={{ fontSize: 12, color: 'var(--color-text-2)' }}>
              {hasBatch ? 'Batch ready' : 'No batch'}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
