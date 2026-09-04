// All backend calls live here — one function per endpoint, always via
// relative /api/... paths (the Vite dev server proxies these to :8000,
// and the built app is served by the same FastAPI process in production).

async function req(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // response wasn't JSON — keep statusText
    }
    throw new Error(detail)
  }
  return res
}

async function getJSON(path) {
  const res = await req(path)
  return res.json()
}

async function postJSON(path, body) {
  const res = await req(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })
  return res.json()
}

export function runBatch() {
  return postJSON('/api/batch/run')
}

export function getBatchStatus() {
  return getJSON('/api/batch/status')
}

export function getRecords({ status = 'all', excClass } = {}) {
  const params = new URLSearchParams({ status })
  if (excClass) params.set('exc_class', excClass)
  return getJSON(`/api/records?${params}`)
}

export function getExceptions({ grouped = false, excClass } = {}) {
  const params = new URLSearchParams({ grouped: String(grouped) })
  if (excClass) params.set('exc_class', excClass)
  return getJSON(`/api/exceptions?${params}`)
}

export function recordAction(recordId, action, note = '') {
  return postJSON(`/api/records/${encodeURIComponent(recordId)}/action`, { action, note })
}

export function getGates({ minMatchRate, maxVariance, maxHighRisk } = {}) {
  const params = new URLSearchParams()
  if (minMatchRate !== undefined) params.set('min_match_rate', minMatchRate)
  if (maxVariance !== undefined) params.set('max_variance', maxVariance)
  if (maxHighRisk !== undefined) params.set('max_high_risk', maxHighRisk)
  const qs = params.toString()
  return getJSON(`/api/gates${qs ? `?${qs}` : ''}`)
}

export function authorizeClose() {
  return postJSON('/api/close/authorize')
}

export function overrideClose(justification) {
  return postJSON('/api/close/override', { justification })
}

export function getVendors() {
  return getJSON('/api/vendors')
}

export function getAuditEvents(n = 25) {
  return getJSON(`/api/audit/events?n=${n}`)
}

export function verifyAudit() {
  return getJSON('/api/audit/verify')
}

export function getEvaluation() {
  return getJSON('/api/evaluation')
}

export function getHistory(n = 12) {
  return getJSON(`/api/history?n=${n}`)
}

export function pdfExportUrl() {
  return '/api/pdf/export'
}

export function askController(question) {
  return postJSON('/api/query', { question })
}

export function preflightScan() {
  return postJSON('/api/batch/preflight')
}

export function getPlaybook(recordId) {
  return getJSON(`/api/records/${encodeURIComponent(recordId)}/playbook`)
}

export function completePlaybookStep(recordId, step, note = '') {
  return postJSON(`/api/records/${encodeURIComponent(recordId)}/playbook/${step}/complete`, { note })
}

export function getGstCalendar() {
  return getJSON('/api/gst/calendar')
}
