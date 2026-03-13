const API_URL = "http://localhost:8000/api/predict";

// Cache to prevent re-checking same URL immediately
const CACHE = new Set();

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && tab.url.startsWith('http')) {
    if (!CACHE.has(tab.url)) {
      analyzeTab(tabId, tab.url);
    }
  }
});

async function analyzeTab(tabId, url) {
  try {
    console.log(`Analyzing: ${url}`);

    // 1. Capture HTML Content
    const injectionResults = await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => document.documentElement.outerHTML
    });
    const htmlContent = injectionResults[0].result;

    // 2. Capture Screenshot (Visible Tab)
    const screenshotDataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png' });

    // 3. Send to API
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: url,
        html: htmlContent,
        screenshot: screenshotDataUrl
      })
    });

    if (!response.ok) return;

    const data = await response.json();
    console.log("Prediction:", data);

    // 4. Act on Prediction
    if (data.prediction === "phishing") {
      chrome.tabs.sendMessage(tabId, {
        action: "showWarning",
        data: data
      });

      chrome.action.setBadgeText({ text: "!", tabId: tabId });
      chrome.action.setBadgeBackgroundColor({ color: "#FF0000", tabId: tabId });
    } else {
      chrome.action.setBadgeText({ text: "OK", tabId: tabId });
      chrome.action.setBadgeBackgroundColor({ color: "#00FF00", tabId: tabId });
      CACHE.add(url);
    }

  } catch (error) {
    console.error("Analysis failed:", error);
  }
}
