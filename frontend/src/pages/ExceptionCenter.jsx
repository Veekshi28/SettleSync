import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChevronDown } from 'lucide-react'

import ExceptionCard from '../components/ExceptionCard'
import { getExceptions, recordAction } from '../api'
import { formatRupeesPrecise } from '../format'

const EXC_CLASSES = ['RULE_37A', 'ITC_TIME_BAR', 'AMOUNT_MISMATCH', 'TIMING_DIFF', 'MISSING_ENTRY']

const SORTERS = {
  'By ITC risk (₹ desc)': (a, b) => b.itc_risk_paise - a.itc_risk_paise,
  'By class': (a, b) => a.exception_class.localeCompare(b.exception_class),
  'By record ID': (a, b) => a.record_id.localeCompare(b.record_id),
}

const GROUP_BADGE = {
  vendor: { label: '🏢 Vendor pattern', color: 'var(--color-blue)' },
  temporal: { label: '📅 Timing pattern', color: 'var(--color-amber)' },
  tds_rate: { label: '💸 TDS pattern', color: 'var(--color-emerald)' },
  ungrouped: { label: 'No pattern', color: 'var(--color-text-3)' },
}

function GroupCard({ group, onAction }) {
  const [open, setOpen] = useState(false)
  const badge = GROUP_BADGE[group.group_type] || GROUP_BADGE.ungrouped

  return (
    <div
      style={{
        border: '1px solid var(--color-border)',
        borderRadius: 8,
        marginBottom: 12,
        background: 'var(--color-surface)',
      }}
    >
      <div
        onClick={() => setOpen((o) => !o)}
        className="flex items-center justify-between"
        style={{ padding: '14px 16px', cursor: 'pointer' }}
      >
        <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
          <span className="font-sans" style={{ fontSize: 12, color: badge.color }}>
            {badge.label}
          </span>
          <span className="font-sans" style={{ fontSize: 14, color: 'var(--color-text-1)' }}>
            {group.label}
          </span>
          <span className="mono" style={{ fontSize: 12, color: 'var(--color-rose)' }}>
            {formatRupeesPrecise(group.total_risk_paise)} at risk
          </span>
        </div>
        <ChevronDown
          size={16}
          color="var(--color-text-3)"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }}
        />
      </div>
      {open && (
        <div style={{ padding: '0 16px 16px' }}>
          <div style={{ fontSize: 13, color: 'var(--color-amber)', marginBottom: 12 }}>
            {group.recommended_action}
          </div>
          {group.records.map((r) => (
            <ExceptionCard key={r.record_id} record={r} onAction={onAction} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function ExceptionCenter() {
  const [allExceptions, setAllExceptions] = useState(null)
  const [viewMode, setViewMode] = useState('Individual')
  const [classFilter, setClassFilter] = useState('')
  const [sortLabel, setSortLabel] = useState('By ITC risk (₹ desc)')
  const [grouped, setGrouped] = useState(null)

  const refresh = useCallback(() => {
    getExceptions().then(setAllExceptions)
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    if (viewMode !== 'Grouped') return
    getExceptions({ grouped: true, excClass: classFilter || undefined }).then(setGrouped)
  }, [viewMode, classFilter, allExceptions])

  async function handleAction({ record_id, action, note }) {
    await recordAction(record_id, action, note)
    refresh()
  }

  const counts = useMemo(() => {
    const c = {}
    for (const cls of EXC_CLASSES) c[cls] = 0
    ;(allExceptions || []).forEach((r) => {
      c[r.exception_class] = (c[r.exception_class] || 0) + 1
    })
    return c
  }, [allExceptions])

  const totalRisk = useMemo(
    () => (allExceptions || []).reduce((sum, r) => sum + r.itc_risk_paise, 0),
    [allExceptions]
  )

  const individualRows = useMemo(() => {
    let rows = allExceptions || []
    if (classFilter) rows = rows.filter((r) => r.exception_class === classFilter)
    return [...rows].sort(SORTERS[sortLabel])
  }, [allExceptions, classFilter, sortLabel])

  if (!allExceptions) {
    return <div style={{ color: 'var(--color-text-3)' }}>Loading…</div>
  }

  if (allExceptions.length === 0) {
    return (
      <div>
        <div className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
          Exception Center
        </div>
        <div style={{ color: 'var(--color-text-3)', marginTop: 16 }}>
          No exceptions — either no batch has been run, or every record auto-resolved.
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
        Exception Center
      </div>
      <div style={{ fontSize: 13, color: 'var(--color-text-3)', marginTop: 4 }}>
        {allExceptions.length} exceptions · {formatRupeesPrecise(totalRisk)} total ITC at risk
      </div>

      <div className="flex items-center justify-between" style={{ marginTop: 20, flexWrap: 'wrap', gap: 12 }}>
        <div className="flex gap-2">
          {['Individual', 'Grouped'].map((m) => (
            <button
              key={m}
              onClick={() => setViewMode(m)}
              className="font-sans"
              style={{
                fontSize: 13,
                padding: '6px 14px',
                borderRadius: 99,
                border: `1px solid ${viewMode === m ? 'var(--color-border-2)' : 'var(--color-border)'}`,
                background: viewMode === m ? 'var(--color-surface-2)' : 'transparent',
                color: viewMode === m ? 'var(--color-text-1)' : 'var(--color-text-2)',
                cursor: 'pointer',
              }}
            >
              {m}
            </button>
          ))}
        </div>

        <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
          <button
            onClick={() => setClassFilter('')}
            className="font-sans"
            style={PILL_STYLE(classFilter === '')}
          >
            All ({allExceptions.length})
          </button>
          {EXC_CLASSES.map((cls) => (
            <button
              key={cls}
              onClick={() => setClassFilter(cls)}
              className="font-sans"
              style={PILL_STYLE(classFilter === cls)}
            >
              {cls} ({counts[cls] || 0})
            </button>
          ))}
        </div>
      </div>

      {viewMode === 'Individual' && (
        <>
          <div style={{ marginTop: 16 }}>
            <select
              value={sortLabel}
              onChange={(e) => setSortLabel(e.target.value)}
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
              {Object.keys(SORTERS).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginTop: 16 }}>
            {individualRows.map((r) => (
              <ExceptionCard key={r.record_id} record={r} onAction={handleAction} />
            ))}
          </div>
        </>
      )}

      {viewMode === 'Grouped' && (
        <div style={{ marginTop: 16 }}>
          {!grouped ? (
            <div style={{ color: 'var(--color-text-3)' }}>Loading…</div>
          ) : (
            grouped.map((g, i) => <GroupCard key={i} group={g} onAction={handleAction} />)
          )}
        </div>
      )}
    </div>
  )
}

function PILL_STYLE(active) {
  return {
    fontSize: 12,
    padding: '5px 10px',
    borderRadius: 99,
    border: `1px solid ${active ? 'var(--color-border-2)' : 'var(--color-border)'}`,
    background: active ? 'var(--color-surface-2)' : 'transparent',
    color: active ? 'var(--color-text-1)' : 'var(--color-text-2)',
    cursor: 'pointer',
  }
}
