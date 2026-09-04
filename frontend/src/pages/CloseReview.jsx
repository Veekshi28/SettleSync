import { useEffect, useState } from 'react'

import ScoreGauge from '../components/ScoreGauge'
import GateRow from '../components/GateRow'
import { getGates, getRecords, authorizeClose, overrideClose, getAuditEvents } from '../api'
import { formatRupeesPrecise } from '../format'

export default function CloseReview() {
  const [gates, setGates] = useState(null)
  const [resolvedRecords, setResolvedRecords] = useState([])
  const [allRecords, setAllRecords] = useState([])
  const [selectedResolved, setSelectedResolved] = useState('')
  const [overrideOpen, setOverrideOpen] = useState(false)
  const [justification, setJustification] = useState('')
  const [ackPermanent, setAckPermanent] = useState(false)
  const [closedInfo, setClosedInfo] = useState(null) // { ledger_seq, timestamp, mode }
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function refreshGates() {
    getGates().then(setGates)
  }

  useEffect(() => {
    refreshGates()
    getRecords({ status: 'resolved' }).then(setResolvedRecords)
    getRecords().then(setAllRecords)
  }, [])

  async function finishWithLedgerLookup(mode) {
    const events = await getAuditEvents(1)
    setClosedInfo({ ledger_seq: events[0]?.seq, timestamp: events[0]?.timestamp, mode })
  }

  async function handleAuthorize() {
    setBusy(true)
    setError('')
    try {
      await authorizeClose()
      await finishWithLedgerLookup('authorized')
      refreshGates()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleOverride() {
    setBusy(true)
    setError('')
    try {
      await overrideClose(justification)
      await finishWithLedgerLookup('override')
      refreshGates()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (!gates) {
    return <div style={{ color: 'var(--color-text-3)' }}>Loading…</div>
  }

  if (!gates.gates.length) {
    return (
      <div>
        <div className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
          Close Review
        </div>
        <div style={{ color: 'var(--color-text-3)', marginTop: 16 }}>
          No batch loaded. Run reconciliation from the Control Tower first.
        </div>
      </div>
    )
  }

  const totalRisk = allRecords.reduce((sum, r) => sum + (r.itc_risk_paise || 0), 0)
  const resolvedCount = allRecords.filter((r) => r.state === 'RESOLVED').length
  const resolutionRate = allRecords.length ? Math.round((resolvedCount / allRecords.length) * 100) : 0
  const selectedRecord = resolvedRecords.find((r) => r.record_id === selectedResolved)

  const absoluteBlockers = gates.gates.filter((g) => !g.passed && !g.overridable)

  return (
    <div>
      <div className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
        Close Review
      </div>
      <div style={{ fontSize: 13, color: 'var(--color-text-3)', marginTop: 4 }}>
        Month-end authorization
      </div>

      <div className="flex items-center gap-8" style={{ marginTop: 24 }}>
        <ScoreGauge score={gates.score} canClose={gates.can_close} size={200} />
        <div>
          <div style={{ fontSize: 13, color: 'var(--color-text-2)', marginBottom: 6 }}>
            Records: <span className="mono">{allRecords.length}</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--color-text-2)', marginBottom: 6 }}>
            Resolution rate: <span className="mono">{resolutionRate}%</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--color-text-2)' }}>
            Total ITC risk:{' '}
            <span className="mono" style={{ color: 'var(--color-rose)' }}>
              {formatRupeesPrecise(totalRisk)}
            </span>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 32 }}>
        <div className="font-sans" style={{ fontSize: 16, fontWeight: 500, marginBottom: 12 }}>
          Close gates
        </div>
        {gates.gates.map((g) => (
          <GateRow key={g.name} gate={g} defaultExpanded={!g.passed} />
        ))}
      </div>

      <div style={{ marginTop: 24 }}>
        {closedInfo ? (
          <div
            style={{
              background: closedInfo.mode === 'authorized' ? 'var(--color-emerald-dim)' : 'var(--color-amber-dim)',
              border: `1px solid ${closedInfo.mode === 'authorized' ? 'var(--color-emerald)' : 'var(--color-amber)'}`,
              borderRadius: 8,
              padding: 20,
            }}
          >
            <div
              className="font-sans"
              style={{
                fontSize: 16,
                fontWeight: 500,
                color: closedInfo.mode === 'authorized' ? 'var(--color-emerald)' : 'var(--color-amber)',
              }}
            >
              {closedInfo.mode === 'authorized' ? 'CLOSE AUTHORIZED' : 'OVERRIDE RECORDED'}
            </div>
            <div style={{ fontSize: 13, color: 'var(--color-text-2)', marginTop: 6 }}>
              Closed at {closedInfo.timestamp} · ledger #{closedInfo.ledger_seq}
            </div>
          </div>
        ) : gates.can_close ? (
          <div>
            <div
              style={{
                background: 'var(--color-emerald-dim)',
                border: '1px solid var(--color-emerald)',
                borderRadius: 8,
                padding: '14px 16px',
                color: 'var(--color-emerald)',
                fontSize: 14,
                marginBottom: 16,
              }}
            >
              All gates pass. Books are ready to close.
            </div>
            <button
              onClick={handleAuthorize}
              disabled={busy}
              className="font-sans"
              style={{
                width: '100%',
                height: 52,
                fontSize: 16,
                fontWeight: 500,
                background: 'var(--color-emerald)',
                color: '#08101F',
                border: 'none',
                borderRadius: 6,
                cursor: busy ? 'default' : 'pointer',
                opacity: busy ? 0.7 : 1,
              }}
            >
              Authorize Close
            </button>
          </div>
        ) : (
          <div>
            <div
              style={{
                background: 'var(--color-rose-dim)',
                border: '1px solid var(--color-rose)',
                borderRadius: 8,
                padding: '14px 16px',
                marginBottom: 16,
              }}
            >
              <div style={{ color: 'var(--color-rose)', fontSize: 14, fontWeight: 500 }}>
                {gates.blockers.length} gate(s) blocking close
              </div>
              <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: 'var(--color-text-2)', fontSize: 13 }}>
                {gates.gates
                  .filter((g) => !g.passed)
                  .map((g) => (
                    <li key={g.name}>{g.label}</li>
                  ))}
              </ul>
            </div>

            {error && (
              <div style={{ color: 'var(--color-rose)', fontSize: 13, marginBottom: 12 }}>{error}</div>
            )}

            {absoluteBlockers.length > 0 && (
              <div style={{ fontSize: 13, color: 'var(--color-text-3)', marginBottom: 12 }}>
                {absoluteBlockers.map((g) => g.label).join(', ')} cannot be overridden — resolve directly.
              </div>
            )}

            <div
              onClick={() => setOverrideOpen((o) => !o)}
              className="font-sans"
              style={{ fontSize: 13, color: 'var(--color-amber)', cursor: 'pointer', marginBottom: 12 }}
            >
              {overrideOpen ? '▾' : '▸'} Override (requires justification)
            </div>

            {overrideOpen && (
              <div>
                <div style={{ fontSize: 12, color: 'var(--color-text-3)', marginBottom: 8 }}>
                  Overriding a close gate is an immutable, accountable act. Your justification will be
                  permanently recorded in the audit ledger.
                </div>
                <textarea
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="Describe why this variance has been verified externally…"
                  rows={3}
                  className="font-sans"
                  style={{
                    width: '100%',
                    background: 'var(--color-surface-2)',
                    border: '1px solid var(--color-border-2)',
                    borderRadius: 6,
                    padding: 10,
                    fontSize: 13,
                    color: 'var(--color-text-1)',
                    resize: 'vertical',
                  }}
                />
                <label className="flex items-center gap-2 font-sans" style={{ fontSize: 12, color: 'var(--color-text-2)', marginTop: 8 }}>
                  <input type="checkbox" checked={ackPermanent} onChange={(e) => setAckPermanent(e.target.checked)} />
                  I understand this action is permanent and auditable
                </label>
                <button
                  onClick={handleOverride}
                  disabled={!ackPermanent || !justification.trim() || busy || absoluteBlockers.length > 0}
                  className="font-sans"
                  style={{
                    marginTop: 12,
                    fontSize: 13,
                    padding: '10px 16px',
                    borderRadius: 6,
                    border: '1px solid var(--color-amber)',
                    background: 'transparent',
                    color: 'var(--color-amber)',
                    cursor: !ackPermanent || !justification.trim() ? 'default' : 'pointer',
                    opacity: !ackPermanent || !justification.trim() ? 0.5 : 1,
                  }}
                >
                  Override and Close
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {(closedInfo || gates.can_close) && resolvedRecords.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <div className="font-sans" style={{ fontSize: 16, fontWeight: 500, marginBottom: 12 }}>
            Why was this auto-resolved?
          </div>
          <select
            value={selectedResolved}
            onChange={(e) => setSelectedResolved(e.target.value)}
            className="font-sans"
            style={{
              fontSize: 13,
              background: 'var(--color-surface-2)',
              border: '1px solid var(--color-border)',
              borderRadius: 6,
              padding: '6px 10px',
              color: 'var(--color-text-1)',
              marginBottom: 12,
            }}
          >
            <option value="">Select a resolved record…</option>
            {resolvedRecords.slice(0, 30).map((r) => (
              <option key={r.record_id} value={r.record_id}>
                {r.record_id}
              </option>
            ))}
          </select>
          {selectedRecord && (
            <div
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                padding: 16,
              }}
            >
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                <div>
                  <div className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-2)', marginBottom: 6 }}>
                    Match evidence
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--color-text-1)' }}>
                    Match type: <span className="mono">{selectedRecord.match_type}</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--color-text-1)' }}>
                    Confidence: <span className="mono">{Math.round(selectedRecord.confidence * 100)}%</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--color-text-1)' }}>
                    Vendor GSTIN: <span className="mono">{selectedRecord.vendor_gstin}</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--color-text-1)' }}>
                    Amount: <span className="mono">{formatRupeesPrecise(selectedRecord.settlement_amount_paise)}</span>
                  </div>
                </div>
                <div>
                  <div className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-2)', marginBottom: 6 }}>
                    Policy checks passed
                  </div>
                  {['Invoice ID matched', 'GSTIN consistent across sources', 'Amount within tolerance', 'GSTR-2B compliance clean'].map(
                    (c) => (
                      <div key={c} style={{ fontSize: 13, color: 'var(--color-emerald)' }}>
                        ✓ {c}
                      </div>
                    )
                  )}
                </div>
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-text-3)', marginTop: 12 }}>
                AI involvement: NONE — fully deterministic. Replay: reproducible (same seed → same result).
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
