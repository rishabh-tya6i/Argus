import React, { useEffect, useState } from "react"

export default function SettingsModal({ open, onClose }) {
  const [threshold, setThreshold] = useState(0.5)
  const [modelVersion, setModelVersion] = useState("default")
  useEffect(() => {
    const t = parseFloat(localStorage.getItem("threshold") || "0.5")
    setThreshold(isNaN(t) ? 0.5 : t)
    setModelVersion(localStorage.getItem("modelVersion") || "default")
  }, [open])
  const save = () => {
    localStorage.setItem("threshold", String(threshold))
    localStorage.setItem("modelVersion", modelVersion)
    onClose()
  }
  return (
    <dialog className="modal" open={open}>
      <div className="modal-box">
        <h3 className="font-bold text-lg">Settings</h3>
        <div className="form-control">
          <label className="label"><span className="label-text">Threshold</span></label>
          <input type="range" min="0" max="1" step="0.01" value={threshold} onChange={e => setThreshold(parseFloat(e.target.value))} className="range" />
        </div>
        <div className="form-control">
          <label className="label"><span className="label-text">Model version</span></label>
          <input className="input input-bordered" value={modelVersion} onChange={e => setModelVersion(e.target.value)} />
        </div>
        <div className="modal-action">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save}>Save</button>
        </div>
      </div>
      <form method="dialog" className="modal-backdrop" onClick={onClose}><button>close</button></form>
    </dialog>
  )
}