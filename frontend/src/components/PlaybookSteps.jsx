import { useEffect, useState } from 'react'
import { ChevronDown, Check } from 'lucide-react'
import { getPlaybook, completePlaybookStep } from '../api'

function formatTs(ts) {
  if (!ts) return ''
  return ts.includes('T') ? ts.split('T')[1].slice(0, 5) : ts
}

export default function PlaybookSteps({ recordId, onAllMandatoryComplete }) {
  const [open, setOpen] = useState(false)
  const [playbook, setPlaybook] = useState(null) // { steps, completed_steps }
  const [busyStep, setBusyStep] = useState(null)

  useEffect(() => {
    if (open && !playbook) {
      getPlaybook(recordId).then(setPlaybook).catch(() => {})
    }
  }, [open, playbook, recordId])

  const steps = playbook?.steps || []
  const completed = new Set(playbook?.completed_steps || [])
  const mandatorySteps = steps.filter((s) => s.mandatory)
  const allMandatoryDone = mandatorySteps.length > 0 && mandatorySteps.every((s) => completed.has(s.step))

  useEffect(() => {
    if (allMandatoryDone) onAllMandatoryComplete?.()
  }, [allMandatoryDone, onAllMandatoryComplete])

  async function toggleStep(step) {
    if (completed.has(step) || busyStep) return
    setBusyStep(step)
    const nowLabel = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    // optimistic update
    setPlaybook((p) => ({
      ...p,
      completed_steps: [...p.completed_steps, step],
      completed_details: { ...p.completed_details, [step]: { ts: nowLabel } },
    }))
    try {
      await completePlaybookStep(recordId, step)
    } catch {
      // revert on failure
      setPlaybook((p) => ({
        ...p,
        completed_steps: p.completed_steps.filter((s) => s !== step),
        completed_details: Object.fromEntries(
          Object.entries(p.completed_details).filter(([k]) => Number(k) !== step)
        ),
      }))
    } finally {
      setBusyStep(null)
    }
  }

  return (
    <div style={{ marginTop: 12, borderTop: '1px solid var(--color-border)', paddingTop: 12 }}>
      <div
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 font-sans"
        style={{ fontSize: 13, color: 'var(--color-text-2)', cursor: 'pointer' }}
      >
        Resolution steps {steps.length > 0 ? `(${steps.length} steps)` : ''}
        <ChevronDown
          size={14}
          color="var(--color-text-3)"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }}
        />
      </div>

      {open && (
        <div style={{ marginTop: 10 }}>
          {!playbook ? (
            <div style={{ fontSize: 12, color: 'var(--color-text-3)' }}>Loading…</div>
          ) : steps.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--color-text-3)' }}>No playbook defined for this exception class.</div>
          ) : (
            <>
              <div style={{ marginBottom: 12 }}>
                <div className="font-sans" style={{ fontSize: 11, color: 'var(--color-text-3)', marginBottom: 4 }}>
                  {completed.size}/{steps.length} steps complete
                </div>
                <div style={{ height: 4, background: 'var(--color-border-2)', borderRadius: 2 }}>
                  <div
                    style={{
                      height: 4,
                      width: `${(completed.size / steps.length) * 100}%`,
                      background: 'var(--color-emerald)',
                      borderRadius: 2,
                      transition: 'width 200ms',
                    }}
                  />
                </div>
              </div>

              {steps.map((s) => {
                const isDone = completed.has(s.step)
                const ts = playbook?.completed_details?.[s.step]?.ts
                return (
                  <div key={s.step} className="flex items-start gap-3" style={{ padding: '8px 0' }}>
                    <button
                      onClick={() => toggleStep(s.step)}
                      disabled={isDone}
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        border: `1px solid ${isDone ? 'var(--color-emerald)' : 'var(--color-border-2)'}`,
                        background: isDone ? 'var(--color-emerald)' : 'transparent',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: isDone ? 'default' : 'pointer',
                        flexShrink: 0,
                        marginTop: 2,
                        padding: 0,
                      }}
                    >
                      {isDone && <Check size={11} color="#08101F" strokeWidth={3} />}
                    </button>
                    <div style={{ flex: 1 }}>
                      <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--color-text-3)' }}>
                          Step {s.step}
                        </span>
                        <span
                          className="font-sans"
                          style={{
                            fontSize: 13,
                            fontWeight: 500,
                            color: 'var(--color-text-1)',
                            textDecoration: isDone ? 'line-through' : 'none',
                            opacity: isDone ? 0.6 : 1,
                          }}
                        >
                          {s.action}
                        </span>
                        {s.mandatory && (
                          <span
                            className="font-sans"
                            style={{
                              fontSize: 11,
                              background: 'var(--color-rose-dim)',
                              color: 'var(--color-rose)',
                              borderRadius: 99,
                              padding: '1px 8px',
                            }}
                          >
                            Required
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--color-text-2)', marginTop: 2, opacity: isDone ? 0.6 : 1 }}>
                        {s.detail}
                      </div>
                      {isDone && ts && (
                        <div style={{ fontSize: 11, color: 'var(--color-text-3)', marginTop: 2 }}>
                          Completed {formatTs(ts)}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}

              {allMandatoryDone && (
                <div
                  className="font-sans"
                  style={{
                    marginTop: 10,
                    fontSize: 12,
                    color: 'var(--color-emerald)',
                    background: 'var(--color-emerald-dim)',
                    borderRadius: 6,
                    padding: '8px 10px',
                  }}
                >
                  Mandatory steps complete — ready to approve
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
