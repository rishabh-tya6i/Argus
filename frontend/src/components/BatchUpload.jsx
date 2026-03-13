import React, { useState } from "react"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

export default function BatchUpload() {
  const [rows, setRows] = useState([])
  const parseCsv = txt => {
    const lines = txt.trim().split(/\r?\n/)
    const urls = lines.map(l => l.split(",")[0]).filter(Boolean)
    return urls
  }
  const onFile = async e => {
    const file = e.target.files?.[0]
    if (!file) return
    const txt = await file.text()
    const urls = parseCsv(txt)
    const r = await fetch(`${API_BASE}/api/batch_predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls })
    })
    const data = await r.json()
    setRows(data.results || [])
  }
  return (
    <div className="card bg-base-100 shadow mt-4">
      <div className="card-body">
        <h2 className="card-title">Batch CSV</h2>
        <input type="file" className="file-input file-input-bordered" accept=".csv" onChange={onFile} />
        <div className="overflow-x-auto">
          <table className="table">
            <thead><tr><th>URL</th><th>Label</th><th>Confidence</th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}><td className="truncate max-w-xs">{r.url}</td><td>{r.label}</td><td>{(r.confidence * 100).toFixed(1)}%</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}