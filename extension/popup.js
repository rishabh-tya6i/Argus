async function updateUI() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) return;

  chrome.storage.local.get(tab.url, (data) => {
    const result = data[tab.url];
    const content = document.getElementById('content');

    if (result) {
      renderResult(content, result);
    } else {
      setTimeout(updateUI, 1000); // Retry if result isn't ready
    }
  });
}

function renderResult(container, result) {
  let statusClass = 'safe';
  let icon = '✅';
  let statusText = 'Safe';

  if (result.prediction === 'phishing') {
    statusClass = 'phish';
    icon = '🚨';
    statusText = 'Phishing';
  } else if (result.prediction === 'suspicious') {
    statusClass = 'suspicious';
    icon = '⚠️';
    statusText = 'Suspicious';
  }

  const confidencePerc = (result.confidence * 100).toFixed(1);

  // Group reasons
  const reasonsHtml = (result.explanation.reasons || []).map(r => `
    <div class="reason-item">
      <span>•</span>
      <span>${r.message}</span>
    </div>
  `).join('') || '<div class="reason-item">No significant risks found.</div>';

  container.innerHTML = `
    <div class="status-card">
      <div class="status-icon">${icon}</div>
      <div class="status-text ${statusClass}">${statusText}</div>
      <div class="confidence-badge">Confidence: ${confidencePerc}%</div>
      <div class="reasons-list">
        ${reasonsHtml}
      </div>
    </div>
  `;
}

document.addEventListener('DOMContentLoaded', updateUI);
