import React, { useEffect, useState } from "react"

export default function HistoryList() {
  const [items, setItems] = useState([])

  const fetchHistory = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/history")
      const data = await res.json()
      setItems(data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 2000) // Poll every 2s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="card bg-base-100 shadow h-full">
      <div className="card-body">
        <h2 className="card-title">Live Detection Feed</h2>
        <div className="overflow-y-auto max-h-[500px]">
          <table className="table w-full">
            <thead>
              <tr>
                <th>Status</th>
                <th>URL</th>
                <th>Confidence</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={i} className="hover">
                  <td>
                    {it.prediction === "phishing" ? (
                      <span className="badge badge-error">Phishing</span>
                    ) : (
                      <span className="badge badge-success">Safe</span>
                    )}
                  </td>
                  <td className="max-w-xs truncate" title={it.url}>{it.url}</td>
                  <td>{(it.confidence * 100).toFixed(1)}%</td>
                  <td className="text-xs opacity-70">{it.timestamp}</td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan="4" className="text-center">No detections yet</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}