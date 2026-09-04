import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, Clock, Calculator, TrendingUp, Copy } from 'lucide-react'

import ScoreGauge from '../components/ScoreGauge'
import GateRow from '../components/GateRow'
import ActivityFeed from '../components/ActivityFeed'
import MetricCard from '../components/MetricCard'
import { runBatch, getBatchStatus, getGates, preflightScan, getGstCalendar } from '../api'
import { formatRupeesPrecise } from '../format'

function GstCalendarStrip() {
  const [cal, setCal] = useState(null)

  useEffect(() => {
    getGstCalendar().then(setCal).catch(() => {})
  }, [])

  if (!cal) return null

  const gstr3bColor =
    cal.gstr3b_days_remaining > 10
      ? 'var(--color-emerald)'
      : cal.gstr3b_days_remaining > 5
        ? 'var(--color-amber)'
        : 'var(--color-rose)'

  const gstr2bText =
    cal.gstr2b_days_until > 0
      ? `In ${cal.gstr2b_days_until} day${cal.gstr2b_days_until === 1 ? '' : 's'}`
      : cal.gstr2b_days_until === 0
        ? 'Available today'
        : 'Available (14th was recent)'
  const gstr2bColor = cal.gstr2b_days_until > 0 ? 'var(--color-text-2)' : 'var(--color-emerald)'

  const Item = ({ label, value, color }) => (
    <div>
      <div className="font-sans" style={{ fontSize: 11, color: 'var(--color-text-3)' }}>
        {label}
      </div>
      <div className="font-sans" style={{ fontSize: 13, fontWeight: 500, color, marginTop: 2 }}>
        {value}
      </div>
    </div>
  )

  return (
    <div className="flex items-center gap-6" style={{ marginTop: 10 }}>
      <Item label="GSTR-3B filing" value={`${cal.gstr3b_days_remaining} days remaining`} color={gstr3bColor} />
      <div style={{ width: 1, height: 24, background: 'var(--color-border)' }} />
      <Item label="GSTR-2B available" value={gstr2bText} color={gstr2bColor} />
      <div style={{ width: 1, height: 24, background: 'var(--color-border)' }} />
      <div>
        <div className="font-sans" style={{ fontSize: 11, color: 'var(--color-text-3)' }}>
          ITC window FY2024-25
        </div>
        <span
          className="font-sans"
          style={{
            fontSize: 11,
            fontWeight: 500,
            borderRadius: 99,
            padding: '1px 8px',
            marginTop: 2,
            display: 'inline-block',
            background: cal.itc_window_fy2024_25 === 'CLOSED' ? 'var(--color-rose-dim)' : 'var(--color-emerald-dim)',
            color: cal.itc_window_fy2024_25 === 'CLOSED' ? 'var(--color-rose)' : 'var(--color-emerald)',
          }}
        >
          {cal.itc_window_fy2024_25}
        </span>
      </div>
    </div>
  )
}

function PreflightCard({ report, onRun, launching }) {
  const rate = report.predicted.estimated_auto_resolution_rate
  const rateColor = rate > 85 ? 'var(--color-emerald)' : rate >= 70 ? 'var(--color-amber)' : 'var(--color-rose)'

  const Row = ({ icon: Icon, label, count, riskColor }) => (
    <div className="flex items-center justify-between" style={{ padding: '8px 0' }}>
      <div className="flex items-center gap-2">
        <Icon size={15} color="var(--color-text-3)" />
        <span className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-2)' }}>
          {label}
        </span>
      </div>
      <span
        className="mono"
        style={{ fontSize: 13, color: riskColor || 'var(--color-text-2)', fontWeight: 500 }}
      >
        {count}
      </span>
    </div>
  )

  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border-2)',
        borderRadius: 8,
        padding: 20,
        marginTop: 20,
        textAlign: 'left',
        maxWidth: 480,
      }}
    >
      <div className="flex items-center justify-between">
        <span className="font-sans" style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-1)' }}>
          Pre-flight scan complete
        </span>
        <span style={{ fontSize: 12, color: 'var(--color-text-3)' }}>
          {report.total_settlements} settlements
        </span>
      </div>

      <div style={{ borderTop: '1px solid var(--color-border)', marginTop: 12 }}>
        <Row
          icon={Clock}
          label="Cross-period settlements"
          count={report.predicted.timing_diff_risk}
          riskColor={report.predicted.timing_diff_risk > 0 ? 'var(--color-amber)' : undefined}
        />
        <Row
          icon={Calculator}
          label="Likely TDS adjustments"
          count={report.predicted.amount_mismatch_risk}
          riskColor={report.predicted.amount_mismatch_risk > 0 ? 'var(--color-amber)' : undefined}
        />
        <Row icon={TrendingUp} label="Above 95th percentile" count={report.predicted.large_amounts} />
        <Row
          icon={Copy}
          label="Duplicate invoice refs"
          count={report.predicted.duplicate_refs}
          riskColor={report.predicted.duplicate_refs > 0 ? 'var(--color-rose)' : undefined}
        />
      </div>

      <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 12, marginTop: 4 }}>
        <span className="font-sans" style={{ fontSize: 14, fontWeight: 500, color: rateColor }}>
          Expected auto-resolution: ~{rate}%
        </span>
        <div style={{ fontSize: 13, color: 'var(--color-text-2)', fontStyle: 'italic', marginTop: 6 }}>
          {report.recommendation}
        </div>
      </div>

      {onRun && (
        <button
          onClick={onRun}
          disabled={launching}
          className="font-sans"
          style={{
            width: '100%',
            marginTop: 16,
            background: 'var(--color-emerald)',
            color: '#08101F',
            fontSize: 14,
            fontWeight: 500,
            padding: '12px 0',
            borderRadius: 6,
            border: 'none',
            cursor: launching ? 'default' : 'pointer',
            opacity: launching ? 0.7 : 1,
          }}
        >
          {launching ? 'Starting…' : 'Run reconciliation'}
        </button>
      )}
    </div>
  )
}

export default function ControlTower({ onBatchChange }) {
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [gates, setGates] = useState(null)
  const [launching, setLaunching] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [thresholds, setThresholds] = useState({ minMatchRate: 0.85, maxVariance: 10000, maxHighRisk: 0 })
  const [preflight, setPreflight] = useState(null)
  const [scanning, setScanning] = useState(false)
  const debounceRef = useRef(null)
  const thresholdsRef = useRef(thresholds)
  thresholdsRef.current = thresholds

  const refreshGates = useCallback((t) => {
    getGates({
      minMatchRate: t.minMatchRate,
      maxVariance: t.maxVariance,
      maxHighRisk: t.maxHighRisk,
    })
      .then(setGates)
      .catch(() => {})
  }, [])

  const refreshStatus = useCallback(() => {
    getBatchStatus().then((s) => {
      setStatus(s)
      onBatchChange?.(s.has_batch)
      if (s.has_batch) refreshGates(thresholdsRef.current)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshGates])

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  useEffect(() => {
    if (!status?.has_batch || !status?.running) return
    const id = setInterval(refreshStatus, 500)
    return () => clearInterval(id)
  }, [status?.has_batch, status?.running, refreshStatus])

  useEffect(() => {
    if (!status?.has_batch || status?.running) return
    const id = setInterval(refreshStatus, 2000)
    return () => clearInterval(id)
  }, [status?.has_batch, status?.running, refreshStatus])

  function handleThresholdChange(next) {
    setThresholds(next)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => refreshGates(next), 300)
  }

  async function handleRun() {
    setLaunching(true)
    try {
      await runBatch()
      refreshStatus()
    } finally {
      setLaunching(false)
    }
  }

  async function handlePreflight() {
    setScanning(true)
    try {
      const report = await preflightScan()
      setPreflight(report)
    } finally {
      setScanning(false)
    }
  }

  if (!status) {
    return <div style={{ color: 'var(--color-text-3)' }}>Loading…</div>
  }

  if (!status.has_batch) {
    return (
      <div
        className="flex flex-col items-center justify-center"
        style={{ minHeight: '70vh', textAlign: 'center' }}
      >
        <div className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
          No batch loaded
        </div>
        <div style={{ fontSize: 14, color: 'var(--color-text-2)', marginTop: 8, maxWidth: 420 }}>
          Run the reconciliation pipeline against this period's Razorpay settlement,
          books, and GSTR-2B data to see whether the books are safe to close.
        </div>

        {!preflight ? (
          <>
            <button
              onClick={handlePreflight}
              disabled={scanning}
              className="font-sans"
              style={{
                marginTop: 24,
                background: 'transparent',
                color: 'var(--color-blue)',
                fontSize: 15,
                fontWeight: 500,
                padding: '12px 28px',
                borderRadius: 6,
                border: '1px solid var(--color-blue)',
                cursor: scanning ? 'default' : 'pointer',
                opacity: scanning ? 0.7 : 1,
              }}
            >
              {scanning ? 'Scanning…' : 'Pre-flight scan'}
            </button>
            <div style={{ fontSize: 12, color: 'var(--color-text-3)', marginTop: 8 }}>
              Analyzes settlement data for exception risk before reconciliation
            </div>
          </>
        ) : (
          <PreflightCard report={preflight} onRun={handleRun} launching={launching} />
        )}
      </div>
    )
  }

  const running = status.running

  return (
    <div>
      <div className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
        Finance Control Tower
      </div>
      <div style={{ fontSize: 13, color: 'var(--color-text-3)', marginTop: 4 }}>
        This period's reconciliation batch · {status.total} records
      </div>
      <GstCalendarStrip />

      {preflight && (
        <div style={{ marginTop: 20 }}>
          <PreflightCard report={preflight} />
        </div>
      )}

      {running && (
        <div style={{ marginTop: 24 }}>
          <div style={{ fontSize: 14, color: 'var(--color-text-2)', marginBottom: 8 }}>
            Processing {status.resolved + status.human_required + status.escalated + status.approved}/{status.total} records…
          </div>
          <ActivityFeed events={status.activity} running={running} />
        </div>
      )}

      {!running && (
        <>
          <div className="grid" style={{ gridTemplateColumns: '2fr 3fr', gap: 32, marginTop: 24 }}>
            <div className="flex items-center justify-center">
              {gates && <ScoreGauge score={gates.score} canClose={gates.can_close} />}
            </div>
            <div>
              <div className="font-sans" style={{ fontSize: 16, fontWeight: 500, marginBottom: 12 }}>
                Close gate status
              </div>
              {gates?.gates.map((g) => (
                <GateRow key={g.name} gate={g} />
              ))}
              {!gates?.can_close && gates?.blockers.length > 0 && (
                <div style={{ fontSize: 13, color: 'var(--color-rose)', marginTop: 4 }}>
                  {gates.blockers.length} blocker(s) preventing close. Resolve or override in Close Review.
                </div>
              )}
            </div>
          </div>

          <div style={{ marginTop: 24, borderTop: '1px solid var(--color-border)', paddingTop: 16 }}>
            <div
              onClick={() => setSettingsOpen((o) => !o)}
              className="flex items-center gap-2"
              style={{ cursor: 'pointer' }}
            >
              <span className="font-sans" style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-1)' }}>
                Controller settings
              </span>
              <ChevronDown
                size={16}
                color="var(--color-text-3)"
                style={{ transform: settingsOpen ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }}
              />
            </div>
            {settingsOpen && (
              <div className="grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, marginTop: 16 }}>
                <label className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-2)' }}>
                  Min match rate ({Math.round(thresholds.minMatchRate * 100)}%)
                  <input
                    type="range"
                    min={0.7}
                    max={0.99}
                    step={0.01}
                    value={thresholds.minMatchRate}
                    onChange={(e) =>
                      handleThresholdChange({ ...thresholds, minMatchRate: Number(e.target.value) })
                    }
                    style={{ width: '100%', marginTop: 6 }}
                  />
                </label>
                <label className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-2)' }}>
                  Max variance (₹)
                  <input
                    type="number"
                    step={1000}
                    value={thresholds.maxVariance}
                    onChange={(e) =>
                      handleThresholdChange({ ...thresholds, maxVariance: Number(e.target.value) })
                    }
                    className="font-sans"
                    style={{
                      width: '100%',
                      marginTop: 6,
                      background: 'var(--color-surface-2)',
                      border: '1px solid var(--color-border-2)',
                      borderRadius: 6,
                      padding: '6px 10px',
                      color: 'var(--color-text-1)',
                    }}
                  />
                </label>
                <label className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-2)' }}>
                  Max high-risk open ({thresholds.maxHighRisk})
                  <input
                    type="range"
                    min={0}
                    max={5}
                    step={1}
                    value={thresholds.maxHighRisk}
                    onChange={(e) =>
                      handleThresholdChange({ ...thresholds, maxHighRisk: Number(e.target.value) })
                    }
                    style={{ width: '100%', marginTop: 6 }}
                  />
                </label>
              </div>
            )}
          </div>

          <div className="grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginTop: 24 }}>
            <MetricCard label="Total records" value={status.total} />
            <MetricCard label="Auto-resolved" value={status.resolved} accent="var(--color-emerald)" />
            <MetricCard label="Awaiting review" value={status.human_required} accent="var(--color-amber)" />
            <MetricCard label="Escalated" value={status.escalated} accent="var(--color-rose)" />
            <MetricCard
              label="Total ITC at risk"
              value={formatRupeesPrecise(status.total_itc_risk_paise)}
              mono
              accent="var(--color-rose)"
            />
          </div>

          <div style={{ marginTop: 24 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
              <span className="font-sans" style={{ fontSize: 14, fontWeight: 500 }}>
                Agent activity
              </span>
              <span
                onClick={() => navigate('/audit')}
                className="font-sans"
                style={{ fontSize: 12, color: 'var(--color-blue)', cursor: 'pointer' }}
              >
                View all
              </span>
            </div>
            <ActivityFeed events={status.activity} running={false} />
          </div>

          {gates?.can_close && (
            <div className="flex justify-end" style={{ marginTop: 24 }}>
              <button
                onClick={() => navigate('/close-review')}
                className="font-sans"
                style={{
                  background: 'var(--color-emerald)',
                  color: '#08101F',
                  fontSize: 14,
                  fontWeight: 500,
                  padding: '10px 20px',
                  borderRadius: 6,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Authorize close
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
