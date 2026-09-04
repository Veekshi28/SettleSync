import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatRupeesPrecise } from '../format'

const STATUS_STYLE = {
  Critical: { bg: 'var(--color-rose-dim)', color: 'var(--color-rose)' },
  Watch: { bg: 'var(--color-amber-dim)', color: 'var(--color-amber)' },
  Clean: { bg: 'var(--color-emerald-dim)', color: 'var(--color-emerald)' },
}

const BAR_COLOR = {
  Critical: '#F43F5E',
  Watch: '#F59E0B',
  Clean: '#10B981',
}

function truncate(name, n = 12) {
  return name.length > n ? `${name.slice(0, n)}…` : name
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const v = payload[0].payload
  return (
    <div
      className="font-sans"
      style={{
        background: 'var(--color-surface-2)',
        border: '1px solid var(--color-border-2)',
        borderRadius: 6,
        padding: '8px 12px',
        fontSize: 12,
      }}
    >
      <div style={{ color: 'var(--color-text-1)', marginBottom: 2 }}>{v.name}</div>
      <div className="mono" style={{ color: 'var(--color-text-2)' }}>
        {formatRupeesPrecise(v.itc_risk_paise)}
      </div>
    </div>
  )
}

export function VendorRiskChart({ vendors }) {
  const data = vendors
    .filter((v) => v.itc_risk_paise > 0)
    .map((v) => ({ name: truncate(v.name), itc_risk_paise: v.itc_risk_paise, thousands: v.itc_risk_paise / 100000, status: v.status }))

  if (data.length === 0) {
    return <div style={{ color: 'var(--color-text-3)', fontSize: 13 }}>No ITC risk to chart — every vendor is clean.</div>
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data}>
        <CartesianGrid stroke="var(--color-border)" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={{ stroke: 'var(--color-border)' }} />
        <YAxis
          tick={{ fill: '#94A3B8', fontSize: 11 }}
          axisLine={{ stroke: 'var(--color-border)' }}
          label={{ value: '₹ thousands', angle: -90, position: 'insideLeft', fill: '#475569', fontSize: 11 }}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--color-surface-2)' }} />
        <Bar dataKey="thousands" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={BAR_COLOR[d.status]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function VendorTable({ vendors }) {
  return (
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
              {['Vendor name', 'GSTIN', 'Invoices', 'Match rate', 'Rule 37A', 'ITC lapsed', 'ITC at risk', 'Status'].map(
                (h) => (
                  <th
                    key={h}
                    className="font-sans"
                    style={{
                      textAlign: h === 'ITC at risk' ? 'right' : 'left',
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
            {vendors.map((v) => {
              const s = STATUS_STYLE[v.status]
              return (
                <tr
                  key={v.gstin}
                  style={{ height: 48, borderBottom: '1px solid var(--color-border)' }}
                  onMouseOver={(e) => (e.currentTarget.style.background = 'var(--color-surface-2)')}
                  onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '0 16px', fontSize: 13, color: 'var(--color-text-1)' }}>{v.name}</td>
                  <td className="mono" style={{ padding: '0 16px', fontSize: 12, color: 'var(--color-text-2)' }}>
                    {v.gstin}
                  </td>
                  <td style={{ padding: '0 16px', fontSize: 13, color: 'var(--color-text-2)' }}>{v.total}</td>
                  <td style={{ padding: '0 16px', fontSize: 13, color: 'var(--color-text-2)' }}>{v.match_rate}%</td>
                  <td style={{ padding: '0 16px', fontSize: 13, color: v.rule_37a > 0 ? 'var(--color-rose)' : 'var(--color-text-3)' }}>
                    {v.rule_37a}
                  </td>
                  <td style={{ padding: '0 16px', fontSize: 13, color: v.itc_timebarred > 0 ? 'var(--color-rose)' : 'var(--color-text-3)' }}>
                    {v.itc_timebarred}
                  </td>
                  <td className="mono" style={{ padding: '0 16px', textAlign: 'right', fontSize: 13, color: 'var(--color-text-1)' }}>
                    {formatRupeesPrecise(v.itc_risk_paise)}
                  </td>
                  <td style={{ padding: '0 16px' }}>
                    <span
                      className="font-sans"
                      style={{
                        fontSize: 11,
                        borderRadius: 99,
                        padding: '2px 8px',
                        background: s.bg,
                        color: s.color,
                      }}
                    >
                      {v.status}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
