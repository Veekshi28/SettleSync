import { useEffect, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import LedgerTimeline from '../components/LedgerTimeline'
import { getAuditEvents, getEvaluation, getHistory } from '../api'
import { formatRupeesPrecise } from '../format'

export default function AuditEvaluation() {
  const [events, setEvents] = useState(null)
  const [evaluation, setEvaluation] = useState(null)
  const [history, setHistory] = useState(null)

  useEffect(() => {
    getAuditEvents(25).then(setEvents)
    getEvaluation().then(setEvaluation)
    getHistory(12).then(setHistory)
  }, [])

  return (
    <div>
      <div className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
        Audit &amp; Evaluation
      </div>

      <div className="grid" style={{ gridTemplateColumns: '3fr 2fr', gap: 32, marginTop: 24 }}>
        <div>{events && <LedgerTimeline events={events} />}</div>

        <div>
          <div className="font-sans" style={{ fontSize: 16, fontWeight: 500, marginBottom: 12 }}>
            Evaluation
          </div>
          {!evaluation ? (
            <div style={{ color: 'var(--color-text-3)' }}>Loading…</div>
          ) : evaluation.error ? (
            <div style={{ color: 'var(--color-text-3)', fontSize: 13 }}>{evaluation.error}</div>
          ) : (
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <EvalStat label="Match rate" value={`${evaluation.settlesync_match_rate.toFixed(1)}%`} />
              <EvalStat
                label="vs baseline"
                value={`+${evaluation.improvement_pp.toFixed(1)} pp`}
                accent="var(--color-emerald)"
              />
              <EvalStat
                label="Unsafe closure rate"
                value={`${evaluation.unsafe_closure_rate.toFixed(1)}%`}
                accent={evaluation.unsafe_closure_rate === 0 ? 'var(--color-emerald)' : 'var(--color-rose)'}
              />
              <EvalStat label="Abstention quality" value={`${evaluation.abstention_quality.toFixed(1)}%`} />
              <EvalStat
                label="Total ITC at risk"
                value={formatRupeesPrecise(evaluation.total_itc_risk_paise)}
                mono
                accent="var(--color-rose)"
              />
              <EvalStat label="Records processed" value={evaluation.total_records} />
            </div>
          )}

          {evaluation && !evaluation.error && evaluation.confidence_calibration && (
            <div style={{ marginTop: 28 }}>
              <div className="font-sans" style={{ fontSize: 16, fontWeight: 500, marginBottom: 10 }}>
                Confidence calibration
              </div>
              <div
                style={{
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 8,
                  overflow: 'hidden',
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--color-surface-2)', borderBottom: '1px solid var(--color-border)' }}>
                      {['Confidence range', 'Matched', 'Correct', 'Precision'].map((h) => (
                        <th
                          key={h}
                          className="font-sans"
                          style={{
                            textAlign: h === 'Precision' || h === 'Correct' || h === 'Matched' ? 'right' : 'left',
                            fontSize: 12, fontWeight: 500, color: 'var(--color-text-2)', padding: '8px 12px',
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {evaluation.confidence_calibration.map((b) => {
                      const p = b.precision
                      const color =
                        p === null ? 'var(--color-text-3)' : p === 100 ? 'var(--color-emerald)' : p > 90 ? 'var(--color-amber)' : 'var(--color-rose)'
                      return (
                        <tr key={b.bucket} style={{ height: 36, borderBottom: '1px solid var(--color-border)' }}>
                          <td className="mono" style={{ padding: '0 12px', fontSize: 12, color: 'var(--color-text-2)' }}>{b.bucket}</td>
                          <td className="mono" style={{ padding: '0 12px', textAlign: 'right', fontSize: 12, color: 'var(--color-text-1)' }}>{b.count}</td>
                          <td className="mono" style={{ padding: '0 12px', textAlign: 'right', fontSize: 12, color: 'var(--color-text-1)' }}>{b.correct}</td>
                          <td className="mono" style={{ padding: '0 12px', textAlign: 'right', fontSize: 12, color, fontWeight: 500 }}>
                            {p === null ? '—' : `${p.toFixed(1)}%`}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: 10 }}>
                <span
                  className="font-sans"
                  style={{
                    fontSize: 12,
                    fontWeight: 500,
                    borderRadius: 99,
                    padding: '3px 10px',
                    background: evaluation.calibration_quality === 'Well-calibrated' ? 'var(--color-emerald-dim)' : 'var(--color-amber-dim)',
                    color: evaluation.calibration_quality === 'Well-calibrated' ? 'var(--color-emerald)' : 'var(--color-amber)',
                  }}
                >
                  {evaluation.calibration_quality}
                </span>
                <span style={{ fontSize: 12, color: 'var(--color-text-3)', marginLeft: 8 }}>
                  {evaluation.calibration_quality === 'Well-calibrated'
                    ? 'High-confidence matches are accurate'
                    : 'Review the confidence threshold on the bucket below 100% precision'}
                </span>
              </div>

              <div className="font-sans" style={{ fontSize: 12, color: 'var(--color-text-3)', marginTop: 8, lineHeight: 1.5 }}>
                When the engine reports high confidence, does it actually get it right?
                This table shows match precision by confidence bucket.
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: 32 }}>
        <div className="font-sans" style={{ fontSize: 16, fontWeight: 500, marginBottom: 12 }}>
          Batch history
        </div>
        {!history ? (
          <div style={{ color: 'var(--color-text-3)' }}>Loading…</div>
        ) : history.length === 0 ? (
          <div style={{ color: 'var(--color-text-3)', fontSize: 13 }}>
            No batch runs recorded yet. Run reconciliation from the Control Tower to start tracking history.
          </div>
        ) : (
          <>
            {history.length >= 2 && (
              <div
                style={{
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 8,
                  padding: 16,
                  marginBottom: 16,
                }}
              >
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={history}>
                    <XAxis
                      dataKey="run_date"
                      tick={{ fill: '#94A3B8', fontSize: 11 }}
                      axisLine={{ stroke: 'var(--color-border)' }}
                      tickFormatter={(v) => v?.slice(5, 10)}
                    />
                    <YAxis domain={[0, 100]} tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={{ stroke: 'var(--color-border)' }} />
                    <Tooltip
                      contentStyle={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border-2)', fontSize: 12 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="close_readiness_score"
                      stroke="var(--color-emerald)"
                      strokeWidth={2}
                      dot={{ fill: 'var(--color-emerald)', r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            <div
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                overflow: 'hidden',
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--color-surface-2)', borderBottom: '1px solid var(--color-border)' }}>
                    {['Date', 'Records', 'Match rate', 'Score', 'Status'].map((h) => (
                      <th
                        key={h}
                        className="font-sans"
                        style={{ textAlign: 'left', fontSize: 12, fontWeight: 500, color: 'var(--color-text-2)', padding: '8px 14px' }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history
                    .slice()
                    .reverse()
                    .map((h) => (
                      <tr key={h.run_id} style={{ height: 40, borderBottom: '1px solid var(--color-border)' }}>
                        <td className="mono" style={{ padding: '0 14px', fontSize: 12, color: 'var(--color-text-2)' }}>
                          {h.run_date?.slice(0, 16).replace('T', ' ')}
                        </td>
                        <td style={{ padding: '0 14px', fontSize: 13, color: 'var(--color-text-1)' }}>{h.total_records}</td>
                        <td style={{ padding: '0 14px', fontSize: 13, color: 'var(--color-text-1)' }}>{h.match_rate}%</td>
                        <td style={{ padding: '0 14px', fontSize: 13, color: 'var(--color-text-1)' }}>{h.close_readiness_score}</td>
                        <td style={{ padding: '0 14px', fontSize: 13, color: h.closed_at ? 'var(--color-emerald)' : 'var(--color-text-3)' }}>
                          {h.closed_at ? 'Closed' : 'Open'}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function EvalStat({ label, value, mono, accent }) {
  return (
    <div>
      <div className={mono ? 'mono' : 'font-sans'} style={{ fontSize: 20, fontWeight: 500, color: accent || 'var(--color-text-1)' }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: 'var(--color-text-3)', marginTop: 2 }}>{label}</div>
    </div>
  )
}
