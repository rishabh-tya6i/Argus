import React, { useState } from "react"
import DOMPurify from "dompurify"
import ResultCard from "./ResultCard.jsx"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

export default function HomePage() {
  const [url, setUrl] = useState("")
  const [html, setHtml] = useState("")
  const [advanced, setAdvanced] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState(null)

  const submit = async () => {
    setError("")
    setLoading(true)
    try {
      const body = { url }
      if (advanced && html.trim()) body.html = DOMPurify.sanitize(html)
      const r = await fetch(`${API_BASE}/api/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data = await r.json()
      setResult(data)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card bg-base-100 shadow">
      <div className="card-body">
        <h2 className="card-title">Analyze URL</h2>
        <input className="input input-bordered w-full" placeholder="https://..." value={url} onChange={e => setUrl(e.target.value)} />
        <label className="label cursor-pointer">
          <span className="label-text">Advanced: paste HTML</span>
          <input type="checkbox" className="toggle" checked={advanced} onChange={e => setAdvanced(e.target.checked)} />
        </label>
        {advanced && (
          <textarea className="textarea textarea-bordered w-full h-40" placeholder="Optional HTML" value={html} onChange={e => setHtml(e.target.value)} />
        )}
        <div className="card-actions justify-end">
          <button className="btn btn-primary" onClick={submit} disabled={loading || !url}>Submit</button>
        </div>
        {loading && <progress className="progress w-full"></progress>}
        {error && <div className="alert alert-error"><span>{error}</span></div>}
        {result && <ResultCard result={result} />}
      </div>
    </div>
  )
}