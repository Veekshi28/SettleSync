import { useState } from 'react'
import { ChevronDown, Clock } from 'lucide-react'
import { formatRupeesPrecise } from '../format'
import PlaybookSteps from './PlaybookSteps'

const BORDER_BY_CLASS = {
  RULE_37A: 'var(--color-rose)',
  ITC_TIME_BAR: '#FB7185',
  AMOUNT_MISMATCH: 'var(--color-amber)',
  TIMING_DIFF: '#FCD34D',
  MISSING_ENTRY: 'var(--color-border-2)',
  GSTR2B_PENDING: 'var(--color-blue)',
}

const RISK_BADGE_BG = {
  RULE_37A: 'var(--color-rose-dim)',
  ITC_TIME_BAR: 'var(--color-rose-dim)',
  AMOUNT_MISMATCH: 'var(--color-amber-dim)',
}
const RISK_BADGE_COLOR = {
  RULE_37A: 'var(--color-rose)',
  ITC_TIME_BAR: 'var(--color-rose)',
  AMOUNT_MISMATCH: 'var(--color-amber)',
}

function Badge({ children, bg, color }) {
  return (
    <span
      className="font-sans"
      style={{
        fontSize: 11,
        background: bg,
        color,
        borderRadius: 99,
        padding: '2px 8px',
        display: 'inline-block',
      }}
    >
      {children}
    </span>
  )
}

function AmountColumn({ label, paise, dateLabel }) {
  return (
    <div>
      <div className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-3)' }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 16, color: 'var(--color-text-1)', marginTop: 4 }}>
        {formatRupeesPrecise(paise)}
      </div>
      {dateLabel && (
        <div style={{ fontSize: 11, color: 'var(--color-text-3)', marginTop: 2 }}>{dateLabel}</div>
      )}
    </div>
  )
}

export default function ExceptionCard({ record, onAction }) {
  const [expanded, setExpanded] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [mandatoryComplete, setMandatoryComplete] = useState(false)

  const isPending = record.exception_class === 'GSTR2B_PENDING'
  const borderColor = BORDER_BY_CLASS[record.exception_class] || 'var(--color-border-2)'
  const diff =
    record.settlement_amount_paise != null && record.books_amount_paise != null
      ? record.settlement_amount_paise - record.books_amount_paise
      : null

  async function confirm(action) {
    setBusy(true)
    try {
      await onAction({ record_id: record.record_id, action, note })
    } finally {
      setBusy(false)
      setPendingAction(null)
      setNote('')
    }
  }

  const actionTaken = !!record.human_action

  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: 8,
        marginBottom: 10,
        opacity: actionTaken ? 0.6 : 1,
        transition: 'opacity 200ms',
      }}
    >
      <div
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center justify-between"
        style={{ padding: '12px 16px', cursor: 'pointer' }}
      >
        <div className="flex items-center gap-2">
          {isPending && <Clock size={14} color="var(--color-blue)" />}
          <span className="mono" style={{ fontSize: 12, color: 'var(--color-text-2)' }}>
            {record.record_id}
          </span>
          <Badge bg="var(--color-blue-dim)" color="var(--color-blue)">
            {isPending ? 'Pending — GSTR-2B' : record.exception_class}
          </Badge>
        </div>
        <div className="flex items-center gap-3">
          {record.itc_risk_paise > 0 && (
            <Badge
              bg={RISK_BADGE_BG[record.exception_class] || 'var(--color-surface-2)'}
              color={RISK_BADGE_COLOR[record.exception_class] || 'var(--color-text-2)'}
            >
              {formatRupeesPrecise(record.itc_risk_paise)} at risk
            </Badge>
          )}
          <ChevronDown
            size={16}
            color="var(--color-text-3)"
            style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }}
          />
        </div>
      </div>

      {expanded && (
        <div style={{ padding: '0 16px 16px' }}>
          <div className="grid grid-cols-3 gap-4">
            <AmountColumn
              label="Settlement"
              paise={record.settlement_amount_paise}
              dateLabel={record.settlement_date}
            />
            <AmountColumn
              label="Books"
              paise={record.books_amount_paise}
              dateLabel={record.invoice_date}
            />
            <AmountColumn label="GSTR-2B" paise={record.gstr_amount_paise} />
          </div>

          {diff !== null && diff !== 0 && (
            <div
              className="mono"
              style={{
                marginTop: 8,
                fontSize: 12,
                color: diff < 0 ? 'var(--color-rose)' : 'var(--color-amber)',
              }}
            >
              Δ {formatRupeesPrecise(Math.abs(diff))}
            </div>
          )}

          <div style={{ borderTop: '1px solid var(--color-border)', margin: '14px 0' }} />

          <div style={{ fontSize: 14, color: 'var(--color-text-2)', lineHeight: 1.6 }}>
            {record.exception_narrative}
          </div>
          {record.exception_rule && (
            <div
              style={{
                fontSize: 12,
                color: 'var(--color-text-3)',
                fontStyle: 'italic',
                marginTop: 4,
              }}
            >
              {record.exception_rule}
            </div>
          )}

          {isPending ? (
            <div
              className="font-sans"
              style={{ fontSize: 12, color: 'var(--color-text-3)', marginTop: 12 }}
            >
              No action needed — this will resolve automatically once GSTR-2B is generated.
            </div>
          ) : (
          <div className="flex justify-end" style={{ marginTop: 12 }}>
            {actionTaken ? (
              <Badge bg="var(--color-surface-2)" color="var(--color-text-2)">
                Action taken: {record.human_action}
              </Badge>
            ) : pendingAction ? (
              <div className="flex items-center gap-2" style={{ width: '100%' }}>
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Review note (optional)"
                  className="font-sans"
                  style={{
                    flex: 1,
                    background: 'var(--color-surface-2)',
                    border: '1px solid var(--color-border-2)',
                    borderRadius: 4,
                    padding: '6px 10px',
                    fontSize: 13,
                    color: 'var(--color-text-1)',
                  }}
                />
                <button
                  disabled={busy}
                  onClick={() => confirm(pendingAction)}
                  className="font-sans"
                  style={{
                    fontSize: 13,
                    borderRadius: 4,
                    padding: '6px 14px',
                    border: '1px solid var(--color-emerald)',
                    color: 'var(--color-emerald)',
                    background: 'transparent',
                    cursor: 'pointer',
                  }}
                >
                  Confirm {pendingAction}
                </button>
                <button
                  onClick={() => setPendingAction(null)}
                  className="font-sans"
                  style={{
                    fontSize: 13,
                    borderRadius: 4,
                    padding: '6px 10px',
                    border: '1px solid var(--color-border-2)',
                    color: 'var(--color-text-2)',
                    background: 'transparent',
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => setPendingAction('approve')}
                  className={mandatoryComplete ? 'font-sans' : 'font-sans action-btn-emerald'}
                  style={
                    mandatoryComplete
                      ? { ...ACTION_BTN_STYLE('var(--color-emerald)'), background: 'var(--color-emerald)', color: '#08101F' }
                      : ACTION_BTN_STYLE('var(--color-emerald)')
                  }
                >
                  Approve
                </button>
                <button
                  onClick={() => setPendingAction('reject')}
                  className="font-sans action-btn-rose"
                  style={ACTION_BTN_STYLE('var(--color-rose)')}
                >
                  Reject
                </button>
                <button
                  onClick={() => setPendingAction('escalate')}
                  className="font-sans action-btn-amber"
                  style={ACTION_BTN_STYLE('var(--color-amber)')}
                >
                  Escalate
                </button>
              </div>
            )}
          </div>
          )}

          {!isPending && !actionTaken && (
            <PlaybookSteps recordId={record.record_id} onAllMandatoryComplete={() => setMandatoryComplete(true)} />
          )}
        </div>
      )}
    </div>
  )
}

function ACTION_BTN_STYLE(color) {
  return {
    fontSize: 13,
    borderRadius: 4,
    padding: '6px 14px',
    border: `1px solid ${color}`,
    color,
    background: 'transparent',
    cursor: 'pointer',
  }
}
