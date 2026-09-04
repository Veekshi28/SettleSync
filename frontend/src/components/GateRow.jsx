import { useState } from 'react'
import { CheckCircle2, XCircle, ChevronDown } from 'lucide-react'

export default function GateRow({ gate, defaultExpanded = false }) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div
      onClick={() => setExpanded((e) => !e)}
      style={{
        background: gate.passed ? 'var(--color-surface)' : 'rgba(244,63,94,0.04)',
        border: '1px solid var(--color-border)',
        borderLeft: `3px solid ${gate.passed ? 'var(--color-emerald)' : 'var(--color-rose)'}`,
        borderRadius: 6,
        padding: '12px 16px',
        cursor: 'pointer',
        marginBottom: 8,
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {gate.passed ? (
            <CheckCircle2 size={18} color="var(--color-emerald)" />
          ) : (
            <XCircle size={18} color="var(--color-rose)" />
          )}
          <span className="font-sans" style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-1)' }}>
            {gate.label}
          </span>
          {!gate.overridable && (
            <span
              className="font-sans"
              style={{
                fontSize: 11,
                color: 'var(--color-text-3)',
                border: '1px solid var(--color-border-2)',
                borderRadius: 99,
                padding: '1px 8px',
              }}
            >
              absolute
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span style={{ fontSize: 13, color: 'var(--color-text-2)' }}>{gate.message}</span>
          <ChevronDown
            size={16}
            color="var(--color-text-3)"
            style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }}
          />
        </div>
      </div>
      {expanded && (
        <pre
          className="mono"
          style={{
            background: '#050A14',
            fontSize: 11,
            color: 'var(--color-text-2)',
            borderRadius: 4,
            padding: 8,
            marginTop: 8,
            overflowX: 'auto',
          }}
        >
          {JSON.stringify(gate.detail, null, 2)}
        </pre>
      )}
    </div>
  )
}
