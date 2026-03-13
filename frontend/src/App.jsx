import React, { useState } from "react"
import HomePage from "./components/HomePage.jsx"
import HistoryList from "./components/HistoryList.jsx"
import SettingsModal from "./components/SettingsModal.jsx"
import AnalyticsDashboard from "./components/AnalyticsDashboard.jsx"

export default function App() {
  const [openSettings, setOpenSettings] = useState(false)
  const [activeTab, setActiveTab] = useState("home")

  return (
    <div className="min-h-screen bg-base-200">
      <div className="navbar bg-base-100 shadow mb-4">
        <div className="flex-1">
          <a className="btn btn-ghost text-xl">Phishing Link Detector</a>
        </div>
        <div className="flex-none gap-2">
          <div className="tabs tabs-boxed">
            <a className={`tab ${activeTab === "home" ? "tab-active" : ""}`} onClick={() => setActiveTab("home")}>Scanner</a>
            <a className={`tab ${activeTab === "analytics" ? "tab-active" : ""}`} onClick={() => setActiveTab("analytics")}>Analytics</a>
          </div>
          <button className="btn btn-ghost" onClick={() => setOpenSettings(true)}>Settings</button>
        </div>
      </div>

      <div className="container mx-auto p-4">
        {activeTab === "home" ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2"><HomePage /></div>
            <div><HistoryList /></div>
          </div>
        ) : (
          <AnalyticsDashboard />
        )}
      </div>

      <SettingsModal open={openSettings} onClose={() => setOpenSettings(false)} />
    </div>
  )
}