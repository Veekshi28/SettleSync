import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import RecordTable from '../components/RecordTable'
import { getRecords, pdfExportUrl } from '../api'

export default function Reconciliation() {
  const navigate = useNavigate()
  const [records, setRecords] = useState(null)

  useEffect(() => {
    getRecords().then(setRecords)
  }, [])

  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
            Reconciliation
          </span>
          {records && (
            <span
              className="font-sans mono"
              style={{
                fontSize: 12,
                color: 'var(--color-text-2)',
                background: 'var(--color-surface-2)',
                borderRadius: 99,
                padding: '2px 10px',
              }}
            >
              {records.length}
            </span>
          )}
        </div>
        <a
          href={pdfExportUrl()}
          className="font-sans"
          style={{
            fontSize: 13,
            border: '1px solid var(--color-border-2)',
            borderRadius: 6,
            padding: '8px 14px',
            color: 'var(--color-text-2)',
            textDecoration: 'none',
          }}
        >
          Export
        </a>
      </div>

      <div style={{ marginTop: 24 }}>
        {!records ? (
          <div style={{ color: 'var(--color-text-3)' }}>Loading…</div>
        ) : records.length === 0 ? (
          <div style={{ color: 'var(--color-text-3)' }}>
            No batch loaded. Run reconciliation from the Control Tower first.
          </div>
        ) : (
          <RecordTable records={records} onReview={() => navigate('/exceptions')} />
        )}
      </div>
    </div>
  )
}
