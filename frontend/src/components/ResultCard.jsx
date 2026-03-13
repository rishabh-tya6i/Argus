import React from "react"

export default function ResultCard({ result }) {
  const isPhishing = result.prediction === "phishing"
  const { model_scores, important_features } = result.explanation

  return (
    <div className={`card shadow-lg mt-6 border-l-4 ${isPhishing ? "border-error bg-error/10" : "border-success bg-success/10"}`}>
      <div className="card-body">
        <div className="flex items-center justify-between">
          <h2 className="card-title text-2xl">
            {isPhishing ? "⚠️ Phishing Detected" : "✅ Safe Website"}
          </h2>
          <div className="badge badge-lg">{Math.round(result.confidence * 100)}% Confidence</div>
        </div>

        <div className="divider">Multi-Modal Analysis</div>

        <div className="grid grid-cols-2 gap-4">
          <ScoreBar label="URL Analysis" score={model_scores.url_model} />
          <ScoreBar label="HTML Content" score={model_scores.html_model} />
          <ScoreBar label="Visual AI" score={model_scores.visual_model} />
          <ScoreBar label="Classical ML" score={model_scores.classical_model} />
        </div>

        {important_features.length > 0 && (
          <>
            <div className="divider">Key Indicators</div>
            <ul className="list-disc ml-5">
              {important_features.map((f, i) => (
                <li key={i} className="font-medium">{f}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  )
}

function ScoreBar({ label, score }) {
  const pct = Math.round(score * 100)
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <progress className={`progress w-full ${score > 0.5 ? "progress-error" : "progress-success"}`} value={pct} max="100"></progress>
    </div>
  )
}