import { useMemo, useState } from 'react'
import { formatRupeesPrecise } from '../format'

const STATUS_PILLS = ['All', 'Resolved', 'Exception', 'Review', 'Escalated']

const STATUS_MATCH = {
  All: () => true,
  Resolved: (r) => r.state === 'RESOLVED',
  Exception: (r) => r.exception_class !== null,
  Review: (r) => r.state === 'HUMAN_REQUIRED',
  Escalated: (r) => r.state === 'ESCALATED',
}

const MATCH_TYPE_STYLE = {
  exact: { bg: 'var(--color-blue-dim)', color: 'var(--color-blue)' },
  fuzzy: { bg: 'var(--color-blue-dim)', color: 'var(--color-blue)' },
  timing: { bg: 'var(--color-amber-dim)', color: 'var(--color-amber)' },
}

const EXC_CLASSES = ['RULE_37A', 'ITC_TIME_BAR', 'AMOUNT_MISMATCH', 'TIMING_DIFF', 'MISSING_ENTRY']

function Pill({ active, children, onClick }) {
  return (
    <button
      onClick={onClick}
      className="font-sans"
      style={{
        fontSize: 13,
        padding: '5px 12px',
        borderRadius: 99,
        border: `1px solid ${active ? 'var(--color-border-2)' : 'var(--color-border)'}`,
        background: active ? 'var(--color-surface-2)' : 'transparent',
        color: active ? 'var(--color-text-1)' : 'var(--color-text-2)',
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
  )
}

export default function RecordTable({ records, onReview }) {
  const [statusFilter, setStatusFilter] = useState('All')
  const [excFilter, setExcFilter] = useState('')
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    let rows = records.filter(STATUS_MATCH[statusFilter])
    if (excFilter) rows = rows.filter((r) => r.exception_class === excFilter)
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(
        (r) => r.record_id.toLowerCase().includes(q) || r.vendor_name.toLowerCase().includes(q)
      )
    }
    return rows
  }, [records, statusFilter, excFilter, search])

  return (
    <div>
      <div className="flex items-center gap-3" style={{ marginBottom: 16, flexWrap: 'wrap' }}>
        <div className="flex gap-2">
          {STATUS_PILLS.map((s) => (
            <Pill key={s} active={statusFilter === s} onClick={() => setStatusFilter(s)}>
              {s}
            </Pill>
          ))}
        </div>
        <select
          value={excFilter}
          onChange={(e) => setExcFilter(e.target.value)}
          className="font-sans"
          style={{
            fontSize: 13,
            background: 'var(--color-surface-2)',
            border: '1px solid var(--color-border)',
            borderRadius: 6,
            padding: '6px 10px',
            color: 'var(--color-text-1)',
          }}
        >
          <option value="">All exception classes</option>
          {EXC_CLASSES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search record ID or vendor…"
          className="font-sans"
          style={{
            fontSize: 13,
            background: 'var(--color-surface-2)',
            border: '1px solid var(--color-border)',
            borderRadius: 6,
            padding: '6px 10px',
            color: 'var(--color-text-1)',
            minWidth: 220,
          }}
        />
      </div>

      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--color-surface-2)', borderBottom: '1px solid var(--color-border)' }}>
                {['Record ID', 'Match type', 'Confidence', 'Exception class', 'Amount (₹)', 'ITC Risk', 'Status', ''].map(
                  (h) => (
                    <th
                      key={h}
                      className="font-sans"
                      style={{
                        textAlign: h === 'Amount (₹)' || h === 'ITC Risk' ? 'right' : 'left',
                        fontSize: 13,
                        fontWeight: 500,
                        color: 'var(--color-text-2)',
                        padding: '10px 16px',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => {
                const mt = MATCH_TYPE_STYLE[r.match_type]
                return (
                  <tr
                    key={r.record_id}
                    style={{ height: 48, borderBottom: '1px solid var(--color-border)' }}
                    onMouseOver={(e) => (e.currentTarget.style.background = 'var(--color-surface-2)')}
                    onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td className="mono" style={{ padding: '0 16px', fontSize: 12, color: 'var(--color-text-2)' }}>
                      {r.record_id}
                    </td>
                    <td style={{ padding: '0 16px' }}>
                      {r.match_type ? (
                        <span
                          className="font-sans"
                          style={{
                            fontSize: 11,
                            borderRadius: 99,
                            padding: '2px 8px',
                            background: mt?.bg || 'var(--color-surface-2)',
                            color: mt?.color || 'var(--color-text-2)',
                          }}
                        >
                          {r.match_type}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--color-text-3)' }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: '0 16px' }}>
                      {r.match_type ? (
                        <div className="flex items-center gap-2">
                          <div style={{ width: 40, height: 4, background: 'var(--color-border-2)', borderRadius: 2 }}>
                            <div
                              style={{
                                width: `${Math.round(r.confidence * 100)}%`,
                                height: 4,
                                background: 'var(--color-emerald)',
                                borderRadius: 2,
                              }}
                            />
                          </div>
                          <span style={{ fontSize: 12, color: 'var(--color-text-2)' }}>
                            {Math.round(r.confidence * 100)}%
                          </span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--color-text-3)' }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: '0 16px' }}>
                      {r.exception_class ? (
                        <span
                          className="font-sans"
                          style={{
                            fontSize: 11,
                            borderRadius: 99,
                            padding: '2px 8px',
                            background: 'var(--color-rose-dim)',
                            color: 'var(--color-rose)',
                          }}
                        >
                          {r.exception_class}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--color-text-3)' }}>—</span>
                      )}
                    </td>
                    <td className="mono" style={{ padding: '0 16px', textAlign: 'right', fontSize: 13, color: 'var(--color-text-1)' }}>
                      {formatRupeesPrecise(r.settlement_amount_paise)}
                    </td>
                    <td
                      className="mono"
                      style={{
                        padding: '0 16px',
                        textAlign: 'right',
                        fontSize: 12,
                        color: r.itc_risk_paise > 0 ? 'var(--color-rose)' : 'var(--color-text-3)',
                      }}
                    >
                      {r.itc_risk_paise > 0 ? formatRupeesPrecise(r.itc_risk_paise) : '—'}
                    </td>
                    <td style={{ padding: '0 16px' }}>
                      <span
                        className="font-sans"
                        style={{
                          fontSize: 11,
                          borderRadius: 99,
                          padding: '2px 8px',
                          background: 'var(--color-surface-2)',
                          color: 'var(--color-text-2)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {r.status_label}
                      </span>
                    </td>
                    <td style={{ padding: '0 16px' }}>
                      {r.state === 'HUMAN_REQUIRED' && onReview && (
                        <button
                          onClick={() => onReview(r)}
                          className="font-sans"
                          style={{
                            fontSize: 12,
                            color: 'var(--color-blue)',
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                          }}
                        >
                          Review
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-3)' }}>
                    No records match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
