const R = 80
const C = 2 * Math.PI * R
const ARC_FRACTION = 0.75
const ARC_LENGTH = C * ARC_FRACTION

function colorFor(score) {
  if (score >= 90) return 'var(--color-emerald)'
  if (score >= 60) return 'var(--color-amber)'
  return 'var(--color-rose)'
}

export default function ScoreGauge({ score = 0, canClose = false, size = 200 }) {
  const offset = ARC_LENGTH - (score / 100) * ARC_LENGTH
  const color = colorFor(score)

  return (
    <div style={{ width: size, height: size, position: 'relative' }}>
      <svg
        viewBox="0 0 200 200"
        width={size}
        height={size}
        style={{ transform: 'rotate(-225deg)' }}
      >
        <circle
          cx="100"
          cy="100"
          r={R}
          fill="none"
          stroke="var(--color-border-2)"
          strokeWidth="10"
          strokeDasharray={`${ARC_LENGTH} ${C}`}
          strokeLinecap="round"
        />
        <circle
          cx="100"
          cy="100"
          r={R}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={`${ARC_LENGTH} ${C}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease-out, stroke 0.5s ease' }}
        />
      </svg>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          className="font-sans"
          style={{ fontSize: 56, fontWeight: 300, color, lineHeight: 1 }}
        >
          {score}
        </div>
        <div style={{ fontSize: 13, color: 'var(--color-text-3)', marginTop: 2 }}>/ 100</div>
        <div
          className="font-sans"
          style={{
            fontSize: 12,
            fontWeight: 500,
            marginTop: 8,
            color: canClose ? 'var(--color-emerald)' : 'var(--color-rose)',
          }}
        >
          {canClose ? 'READY TO CLOSE' : 'BLOCKED'}
        </div>
      </div>
    </div>
  )
}
