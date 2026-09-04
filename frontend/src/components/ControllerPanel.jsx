import { useState } from 'react'
import { MessageSquare, Send, Lock, X } from 'lucide-react'
import { askController } from '../api'

const SUGGESTED_QUESTIONS = [
  "What's blocking close?",
  'Which vendor has the most ITC at risk?',
  'How many RULE_37A exceptions need review?',
  'Summarize this batch for my CA',
]

function LoadingDots() {
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="pulse-dot"
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: 'var(--color-text-3)',
              animationDelay: `${i * 200}ms`,
            }}
          />
        ))}
      </div>
      <span className="font-sans" style={{ fontSize: 12, color: 'var(--color-text-3)' }}>
        Controller is checking the data…
      </span>
    </div>
  )
}

function Exchange({ item, faded }) {
  return (
    <div style={{ opacity: faded ? 0.6 : 1, marginBottom: 16 }}>
      <div className="font-sans" style={{ fontSize: 13, color: 'var(--color-text-2)', marginBottom: 6 }}>
        {item.question}
      </div>
      <div
        style={{
          background: 'var(--color-surface-2)',
          borderRadius: 6,
          padding: 12,
        }}
      >
        <div className="font-sans" style={{ fontSize: 14, color: 'var(--color-text-1)', lineHeight: 1.6 }}>
          {item.answer}
        </div>
        <div className="font-sans" style={{ fontSize: 11, color: 'var(--color-text-3)', marginTop: 8 }}>
          {item.used_llm ? 'via Claude' : 'deterministic'}
        </div>
      </div>
    </div>
  )
}

export default function ControllerPanel({ open, onToggle, hasBatch }) {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([]) // newest last, keep last 3

  async function submit(q) {
    const text = (q ?? question).trim()
    if (!text || loading || !hasBatch) return
    setLoading(true)
    setQuestion('')
    try {
      const result = await askController(text)
      setHistory((h) => [...h.slice(-2), { question: text, ...result }])
    } catch (e) {
      setHistory((h) => [
        ...h.slice(-2),
        { question: text, answer: `Could not reach the controller: ${e.message}`, used_llm: false },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        onClick={onToggle}
        aria-label="Ask the controller"
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 48,
          height: 48,
          borderRadius: '50%',
          background: 'var(--color-surface-2)',
          border: '1px solid var(--color-border-2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          zIndex: 30,
        }}
      >
        {open ? <X size={20} color="var(--color-text-2)" /> : <MessageSquare size={20} color="var(--color-text-2)" />}
      </button>

      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: 320,
          background: 'var(--color-surface)',
          borderLeft: '1px solid var(--color-border)',
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 200ms ease',
          zIndex: 25,
          display: 'flex',
          flexDirection: 'column',
          padding: 20,
        }}
      >
        <div className="font-sans" style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-1)', marginBottom: 16 }}>
          Ask the controller
        </div>

        {!hasBatch ? (
          <div className="flex flex-col items-center justify-center" style={{ flex: 1, textAlign: 'center' }}>
            <Lock size={24} color="var(--color-text-3)" />
            <div style={{ fontSize: 13, color: 'var(--color-text-3)', marginTop: 12 }}>
              Run a reconciliation batch first
            </div>
          </div>
        ) : (
          <>
            <div style={{ flex: 1, overflowY: 'auto', marginBottom: 12 }}>
              {history.length === 0 && !loading && (
                <div>
                  <div style={{ fontSize: 12, color: 'var(--color-text-3)', marginBottom: 10 }}>
                    Try asking:
                  </div>
                  <div className="flex flex-col gap-2">
                    {SUGGESTED_QUESTIONS.map((q) => (
                      <button
                        key={q}
                        onClick={() => submit(q)}
                        className="font-sans"
                        style={{
                          fontSize: 12,
                          textAlign: 'left',
                          padding: '8px 12px',
                          borderRadius: 99,
                          border: '1px solid var(--color-border-2)',
                          background: 'transparent',
                          color: 'var(--color-text-2)',
                          cursor: 'pointer',
                        }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {history.map((item, i) => (
                <Exchange key={i} item={item} faded={i < history.length - 1} />
              ))}

              {loading && <LoadingDots />}
            </div>

            <div className="flex items-center gap-2">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submit()}
                placeholder="Ask anything about this batch…"
                disabled={loading}
                className="mono"
                style={{
                  flex: 1,
                  fontSize: 13,
                  background: 'var(--color-surface-2)',
                  border: '1px solid var(--color-border-2)',
                  borderRadius: 4,
                  padding: '8px 10px',
                  color: 'var(--color-text-1)',
                }}
              />
              <button
                onClick={() => submit()}
                disabled={loading || !question.trim()}
                className="send-btn"
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: 4,
                  border: '1px solid var(--color-border-2)',
                  background: 'transparent',
                  color: 'var(--color-text-2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                <Send size={15} />
              </button>
            </div>
          </>
        )}
      </div>
    </>
  )
}
