chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'GET_PAGE_CONTENT') {
    sendResponse({
      html: document.documentElement.outerHTML.substring(0, 500000) // Truncate very long pages
    });
  }
});
