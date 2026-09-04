import { useState } from 'react'
import { verifyAudit } from '../api'

const CLOSE_ACTIONS = new Set(['CLOSE_AUTHORIZED', 'CLOSE_OVERRIDE', 'BATCH_COMPLETE'])

export default function LedgerTimeline({ events }) {
  const [verifyState, setVerifyState] = useState(null) // null | 'loading' | result
  const [showResult, setShowResult] = useState(false)

  async function handleVerify() {
    setVerifyState('loading')
    setShowResult(false)
    try {
      const result = await verifyAudit()
      setVerifyState(result)
      setTimeout(() => setShowResult(true), 600)
    } catch (e) {
      setVerifyState({ intact: false, broken_at: null, event_count: 0, error: e.message })
      setTimeout(() => setShowResult(true), 600)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
        <span className="font-sans" style={{ fontSize: 16, fontWeight: 500, color: 'var(--color-text-1)' }}>
          Audit ledger
        </span>
        <button
          onClick={handleVerify}
          className="font-sans"
          style={{
            fontSize: 12,
            border: '1px solid var(--color-border-2)',
            borderRadius: 6,
            padding: '6px 12px',
            color: 'var(--color-text-2)',
            background: 'transparent',
            cursor: 'pointer',
          }}
        >
          {verifyState === 'loading' ? 'Verifying…' : 'Verify chain integrity'}
        </button>
      </div>

      {verifyState && verifyState !== 'loading' && showResult && (
        <div
          className="font-sans"
          style={{
            fontSize: 13,
            marginBottom: 12,
            color: verifyState.intact ? 'var(--color-emerald)' : 'var(--color-rose)',
          }}
        >
          {verifyState.intact
            ? `✓ ${verifyState.event_count} events verified — chain intact`
            : `✗ Chain broken at event #${verifyState.broken_at}`}
        </div>
      )}

      <div>
        {events.map((e) => (
          <div key={e.seq} className="flex" style={{ marginBottom: 2 }}>
            <div style={{ width: 48, position: 'relative', display: 'flex', justifyContent: 'center' }}>
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  bottom: 0,
                  width: 1,
                  background: 'var(--color-border)',
                }}
              />
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: CLOSE_ACTIONS.has(e.action) ? 'var(--color-emerald)' : 'var(--color-text-3)',
                  marginTop: 6,
                  zIndex: 1,
                }}
              />
            </div>
            <div style={{ paddingBottom: 16, flex: 1 }}>
              <div className="mono" style={{ fontSize: 11, color: 'var(--color-text-3)' }}>
                #{e.seq} · {e.timestamp}
              </div>
              <div className="font-sans" style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-1)' }}>
                {e.action}
              </div>
              {e.record_id && (
                <div className="mono" style={{ fontSize: 12, color: 'var(--color-text-2)' }}>
                  {e.record_id}
                </div>
              )}
              <div className="mono" style={{ fontSize: 11, color: 'var(--color-text-3)' }}>
                {e.current_hash.slice(0, 16)}…
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
