const API_BASE_URL = 'http://localhost:8000';

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && tab.url.startsWith('http')) {
    chrome.tabs.sendMessage(tabId, { action: 'GET_PAGE_CONTENT' }, (response) => {
      if (chrome.runtime.lastError) {
        console.warn('Content script not ready or not permitted on this page.');
        return;
      }
      if (response) {
        scanUrl(tab.url, response.html);
      }
    });
  }
});

async function scanUrl(url, html) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/predict`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Type': 'extension'
      },
      body: JSON.stringify({
        url: url,
        html: html,
        source: 'extension'
      })
    });

    if (!response.ok) throw new Error('API request failed');

    const result = await response.json();
    chrome.storage.local.set({ [url]: result });

    if (result.prediction === 'phishing' && result.confidence > 0.8) {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon128.png',
        title: 'Phishing Alert!',
        message: `Argus detected this site as high-risk (${(result.confidence * 100).toFixed(1)}%). Proceed with extreme CAUTION.`,
        priority: 2
      });
    }
  } catch (error) {
    console.error('Scan error:', error);
  }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'GET_RESULT') {
    chrome.storage.local.get(request.url, (data) => {
      sendResponse(data[request.url]);
    });
    return true; // async response
  }
});
