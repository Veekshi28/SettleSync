import { useEffect, useRef } from 'react'

function actionColor(action) {
  if (action === 'resolved') return 'var(--color-emerald)'
  if (action === 'classified' || action === 'exception') return 'var(--color-amber)'
  if (action === 'human_required' || action === 'blocked') return 'var(--color-rose)'
  if (action === 'BATCH_START' || action === 'BATCH_COMPLETE') return 'var(--color-blue)'
  return 'var(--color-text-2)'
}

export default function ActivityFeed({ events = [], running = false }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const el = containerRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [events.length])

  return (
    <div
      className="mono"
      style={{
        background: '#050A14',
        border: '1px solid var(--color-border)',
        borderRadius: 6,
        fontSize: 12,
      }}
    >
      <div
        className="flex items-center justify-between px-3 py-2"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        <div className="flex items-center gap-2">
          <span
            className={running ? 'pulse-dot' : ''}
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: running ? 'var(--color-emerald)' : 'var(--color-text-3)',
              display: 'inline-block',
            }}
          />
          <span className="font-sans" style={{ fontSize: 12, color: 'var(--color-text-2)' }}>
            Activity log
          </span>
        </div>
        <span style={{ color: 'var(--color-text-3)' }}>{events.length} events</span>
      </div>
      <div ref={containerRef} style={{ height: 240, overflowY: 'auto', padding: 12 }}>
        {events.length === 0 && (
          <div style={{ color: 'var(--color-text-3)' }}>No activity yet.</div>
        )}
        {events.map((ev, i) => (
          <div key={`${ev.ts}-${ev.record_id}-${i}`} className="line-fade-in" style={{ marginBottom: 4 }}>
            <span style={{ color: 'var(--color-text-3)' }}>[{ev.ts}]</span>{' '}
            <span style={{ color: 'var(--color-text-2)' }}>{ev.record_id}</span>{' '}
            <span style={{ color: actionColor(ev.action) }}>{ev.action}</span>{' '}
            <span style={{ color: 'var(--color-text-3)' }}>{ev.detail}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
