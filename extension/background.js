// --- Constants ---
const API_URL = "http://localhost:8000/api/predict";

// --- State Cache ---
const CACHE = new Set();
const tabData = {};

function initTabData(tabId) {
  if (!tabData[tabId]) {
    tabData[tabId] = {
      requests: [],
      headers: {},
      lastUrl: ""
    };
  }
}

// --- Tab Update Tracking ---
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && tab.url.startsWith('http')) {
    initTabData(tabId);
    tabData[tabId].lastUrl = tab.url;
    if (!CACHE.has(tab.url)) {
      analyzeTab(tabId, tab.url);
    }
  }
});

async function analyzeTab(tabId, url) {
  try {
    console.log(`Analyzing: ${url}`);
    
    // Capture HTML
    const injectionResults = await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => document.documentElement.outerHTML
    });
    const htmlContent = injectionResults[0]?.result;

    // Capture Screenshot
    const screenshotDataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png' }).catch(() => null);

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

    if (data.prediction === "phishing") {
      chrome.tabs.sendMessage(tabId, { action: "showWarning", data: data });
      chrome.action.setBadgeText({ text: "!", tabId: tabId });
      chrome.action.setBadgeBackgroundColor({ color: "#EF4444", tabId: tabId });
    } else {
      chrome.action.setBadgeText({ text: "OK", tabId: tabId });
      chrome.action.setBadgeBackgroundColor({ color: "#10B981", tabId: tabId });
      CACHE.add(url);
    }
  } catch (error) {
    console.warn("Background analysis failed:", error);
  }
}

// --- DevTools Support ---

chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabData[tabId]) delete tabData[tabId];
});

// Capture network requests info (observer pattern)
chrome.webRequest.onCompleted.addListener(
  (details) => {
    if (details.tabId >= 0) {
      initTabData(details.tabId);
      tabData[details.tabId].requests.push({
        url: details.url,
        method: details.method,
        type: details.type,
        ip: details.ip,
        statusCode: details.statusCode,
        timestamp: Date.now()
      });
      // Keep only last 100
      if (tabData[details.tabId].requests.length > 100) tabData[details.tabId].requests.shift();
    }
  },
  { urls: ["<all_urls>"] }
);

// Capture security headers for main frame
chrome.webRequest.onHeadersReceived.addListener(
  (details) => {
    if (details.tabId >= 0 && details.type === "main_frame") {
      initTabData(details.tabId);
      const headers = {};
      const relevantHeaders = [
        "content-security-policy",
        "strict-transport-security",
        "x-frame-options",
        "referrer-policy",
        "x-content-type-options",
        "content-type"
      ];

      details.responseHeaders.forEach(h => {
        const name = h.name.toLowerCase();
        if (relevantHeaders.includes(name)) {
          headers[name] = h.value;
        }
      });
      tabData[details.tabId].headers = headers;
    }
  },
  { urls: ["<all_urls>"] },
  ["responseHeaders", "extraHeaders"]
);

// Message handling
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  initTabData(request.tabId || sender.tab?.id);

  if (request.action === "getNetworkData") {
    sendResponse(tabData[request.tabId] || { requests: [], headers: {} });
    return true;
  }
  
  if (request.action === "triggerScan") {
    chrome.tabs.sendMessage(request.tabId, { action: "extractPageData" }, (response) => {
        if (chrome.runtime.lastError) {
             sendResponse({ error: "Could not connect to content script. Please refresh the page." });
        } else {
             sendResponse(response);
        }
    });
    return true;
  }
});
