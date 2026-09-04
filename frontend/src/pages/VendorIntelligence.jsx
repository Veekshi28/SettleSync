import { useEffect, useState } from 'react'

import VendorTable, { VendorRiskChart } from '../components/VendorTable'
import { getVendors } from '../api'
import { formatRupeesPrecise } from '../format'

export default function VendorIntelligence() {
  const [vendors, setVendors] = useState(null)

  useEffect(() => {
    getVendors().then(setVendors)
  }, [])

  if (!vendors) {
    return <div style={{ color: 'var(--color-text-3)' }}>Loading…</div>
  }

  const highRisk = vendors.filter((v) => v.status === 'Critical')

  return (
    <div>
      <div className="font-sans" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-text-1)' }}>
        Vendor Intelligence
      </div>
      <div style={{ fontSize: 13, color: 'var(--color-text-3)', marginTop: 4 }}>
        Compliance scorecard for this batch
      </div>

      {vendors.length === 0 ? (
        <div style={{ color: 'var(--color-text-3)', marginTop: 24 }}>
          No batch loaded. Run reconciliation from the Control Tower first.
        </div>
      ) : (
        <>
          <div style={{ marginTop: 24 }}>
            <VendorTable vendors={vendors} />
          </div>

          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 24, marginTop: 24 }}>
            <div>
              <div className="font-sans" style={{ fontSize: 16, fontWeight: 500, marginBottom: 12 }}>
                High-risk vendors
              </div>
              {highRisk.length === 0 ? (
                <div style={{ fontSize: 13, color: 'var(--color-text-3)' }}>No critical vendors this period.</div>
              ) : (
                highRisk.map((v) => (
                  <div
                    key={v.gstin}
                    style={{
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderLeft: '3px solid var(--color-rose)',
                      borderRadius: 6,
                      padding: '10px 14px',
                      marginBottom: 8,
                    }}
                  >
                    <div className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-1)' }}>
                      {v.name}
                    </div>
                    <div className="mono" style={{ fontSize: 11, color: 'var(--color-text-3)', marginTop: 2 }}>
                      {v.gstin}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-2)', marginTop: 4 }}>
                      {v.rule_37a > 0 && `${v.rule_37a} Rule 37A`}
                      {v.rule_37a > 0 && v.itc_timebarred > 0 && ' · '}
                      {v.itc_timebarred > 0 && `${v.itc_timebarred} ITC time-barred`}
                      {v.rule_37a === 0 && v.itc_timebarred === 0 && `Match rate ${v.match_rate}%`}
                      {' · '}
                      <span className="mono" style={{ color: 'var(--color-rose)' }}>
                        {formatRupeesPrecise(v.itc_risk_paise)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div>
              <div className="font-sans" style={{ fontSize: 16, fontWeight: 500, marginBottom: 12 }}>
                ITC risk by vendor
              </div>
              <VendorRiskChart vendors={vendors} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
