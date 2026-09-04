export function formatRupees(paise) {
  if (paise === null || paise === undefined) return '—'
  const rupees = paise / 100
  return `₹${rupees.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

export function formatRupeesPrecise(paise) {
  if (paise === null || paise === undefined) return '—'
  const rupees = paise / 100
  return `₹${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
