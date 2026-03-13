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

// --- DevTools Panel Support ---

// Tab Data Cache for Network and Headers
const tabData = {};

function initTabData(tabId) {
  if (!tabData[tabId]) {
    tabData[tabId] = {
      requests: [],
      headers: {}
    };
  }
}

// Ensure cleanup when tabs are closed
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabData[tabId]) {
    delete tabData[tabId];
  }
});

// Clear data on navigation
chrome.webNavigation?.onBeforeNavigate?.addListener((details) => {
    if (details.frameId === 0 && tabData[details.tabId]) {
        tabData[details.tabId] = { requests: [], headers: {} };
    }
});

// Capture network requests
chrome.webRequest.onCompleted.addListener(
  (details) => {
    if (details.tabId >= 0) {
      initTabData(details.tabId);
      // store relevant request info
      tabData[details.tabId].requests.push({
        url: details.url,
        method: details.method,
        type: details.type,
        ip: details.ip
      });
    }
  },
  { urls: ["<all_urls>"] }
);

// Capture security headers
chrome.webRequest.onHeadersReceived.addListener(
  (details) => {
    if (details.tabId >= 0 && details.type === "main_frame") {
      initTabData(details.tabId);
      const headers = {};
      
      const relevantHeaders = [
        "content-security-policy",
        "strict-transport-security",
        "x-frame-options",
        "referrer-policy"
      ];

      for (const header of details.responseHeaders) {
        const name = header.name.toLowerCase();
        if (relevantHeaders.includes(name)) {
          headers[name] = header.value;
        }
      }
      tabData[details.tabId].headers = headers;
    }
  },
  { urls: ["<all_urls>"] },
  ["responseHeaders"]
);

// Message relay between DevTools and Content Script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getNetworkData") {
    sendResponse(tabData[request.tabId] || { requests: [], headers: {} });
    return true;
  }
  
  if (request.action === "triggerScan") {
    chrome.tabs.sendMessage(request.tabId, { action: "extractPageData" }, (response) => {
        if (chrome.runtime.lastError) {
             sendResponse({ error: chrome.runtime.lastError.message });
        } else {
             sendResponse(response);
        }
    });
    return true; // Keep message channel open for async response
  }
});
