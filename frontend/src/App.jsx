import { useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'

import Sidebar from './components/Sidebar'
import ControllerPanel from './components/ControllerPanel'
import ControlTower from './pages/ControlTower'
import Reconciliation from './pages/Reconciliation'
import ExceptionCenter from './pages/ExceptionCenter'
import VendorIntelligence from './pages/VendorIntelligence'
import CloseReview from './pages/CloseReview'
import AuditEvaluation from './pages/AuditEvaluation'
import { getBatchStatus } from './api'

export default function App() {
  const [hasBatch, setHasBatch] = useState(false)
  const [panelOpen, setPanelOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    getBatchStatus()
      .then((s) => !cancelled && setHasBatch(s.has_batch))
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div style={{ display: 'flex' }}>
      <Sidebar hasBatch={hasBatch} />
      <main
        className="page-fade"
        style={{
          marginLeft: 56,
          flex: 1,
          minHeight: '100vh',
          padding: '28px 32px',
        }}
      >
        <div style={{ maxWidth: 1360, margin: '0 auto' }}>
          <Routes>
            <Route path="/" element={<ControlTower onBatchChange={setHasBatch} />} />
            <Route path="/reconciliation" element={<Reconciliation />} />
            <Route path="/exceptions" element={<ExceptionCenter />} />
            <Route path="/vendors" element={<VendorIntelligence />} />
            <Route path="/close-review" element={<CloseReview />} />
            <Route path="/audit" element={<AuditEvaluation />} />
          </Routes>
        </div>
      </main>
      <ControllerPanel open={panelOpen} onToggle={() => setPanelOpen((o) => !o)} hasBatch={hasBatch} />
    </div>
  )
}
