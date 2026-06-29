const normaliseValue = (value) => {
  if (value === undefined || value === null) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const downloadText = (filename, text, mime) => {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export const downloadJson = (filename, data) => {
  downloadText(filename, JSON.stringify(data, null, 2), 'application/json;charset=utf-8')
}

export const downloadCsv = (filename, rows) => {
  const list = Array.isArray(rows) ? rows : []
  const headers = []
  for (const row of list) {
    Object.keys(row || {}).forEach(key => { if (!headers.includes(key)) headers.push(key) })
  }
  const escapeCell = (value) => {
    const text = normaliseValue(value)
    if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`
    return text
  }
  const lines = [headers.join(',')]
  for (const row of list) lines.push(headers.map(key => escapeCell(row?.[key])).join(','))
  downloadText(filename, '\ufeff' + lines.join('\n'), 'text/csv;charset=utf-8')
}
