export default function MetricCard({ label, value, mono = false, accent }) {
  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 8,
        padding: '14px 16px',
      }}
    >
      <div
        className={mono ? 'mono' : 'font-sans'}
        style={{ fontSize: 20, fontWeight: 500, color: accent || 'var(--color-text-1)' }}
      >
        {value}
      </div>
      <div className="font-sans" style={{ fontSize: 12, color: 'var(--color-text-3)', marginTop: 4 }}>
        {label}
      </div>
    </div>
  )
}
