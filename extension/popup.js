document.addEventListener('DOMContentLoaded', async () => {
    const statusDiv = document.getElementById('status');
    const detailsDiv = document.getElementById('details');

    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab || !tab.url.startsWith('http')) {
        statusDiv.textContent = "Not a web page";
        statusDiv.className = "status";
        return;
    }

    try {
        const response = await fetch("http://localhost:8000/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: tab.url })
        });

        const data = await response.json();

        if (data.prediction === "phishing") {
            statusDiv.textContent = "⚠️ PHISHING DETECTED";
            statusDiv.className = "status phishing";
        } else {
            statusDiv.textContent = "✅ Safe Website";
            statusDiv.className = "status safe";
        }

        detailsDiv.innerHTML = `
      <p>Confidence: <strong>${(data.confidence * 100).toFixed(1)}%</strong></p>
    `;

    } catch (error) {
        statusDiv.textContent = "Error connecting to server";
        statusDiv.className = "status";
        console.error(error);
    }
});

document.getElementById('report-btn').addEventListener('click', () => {
    alert("Report feature coming soon!");
});
