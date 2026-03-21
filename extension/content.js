chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "showWarning") {
    showPhishingWarning(request.data);
  } else if (request.action === "extractPageData") {
    try {
        const data = extractSecurityData();
        sendResponse(data);
    } catch (err) {
        sendResponse({ error: err.message });
    }
  }
});

function extractSecurityData() {
  const forms = [];
  document.querySelectorAll('form').forEach(form => {
    const hasPassword = !!form.querySelector('input[type="password"]');
    const hasHiddenFields = !!form.querySelector('input[type="hidden"]');
    
    // Check if the form action points to a different domain
    let isCrossDomain = false;
    if (form.action) {
        try {
            const actionUrl = new URL(form.action, window.location.href);
            isCrossDomain = actionUrl.origin !== window.location.origin;
        } catch(e) { /* Ignore invalid URLs */ }
    }

    forms.push({
      action: form.action,
      method: form.method || 'GET',
      hasPassword: hasPassword,
      hasHiddenFields: hasHiddenFields,
      crossDomain: isCrossDomain
    });
  });

  const scripts = [];
  document.querySelectorAll('script').forEach(script => {
    let isCrossDomain = false;
    if (script.src) {
        try {
            const srcUrl = new URL(script.src, window.location.href);
            isCrossDomain = srcUrl.origin !== window.location.origin;
        } catch(e) { /* Ignore invalid URLs */ }
    }

    scripts.push({
      src: script.src,
      isInline: !script.src,
      content: !script.src ? script.textContent : null,
      crossDomain: isCrossDomain
    });
  });

  return {
    url: window.location.href,
    title: document.title,
    forms: forms,
    scripts: scripts
  };
}

function showPhishingWarning(data) {
  // Check if warning already exists
  if (document.getElementById("phishing-warning-overlay")) return;

  const overlay = document.createElement("div");
  overlay.id = "phishing-warning-overlay";

  // Create Shadow DOM
  const shadow = overlay.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = `
    :host {
      all: initial;
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background-color: #c0392b;
      z-index: 2147483647; /* Max Z-Index */
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: white;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .container {
      background: white;
      color: #333;
      padding: 40px;
      border-radius: 12px;
      text-align: center;
      max-width: 600px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    }
    h1 {
      color: #c0392b;
      margin-top: 0;
      font-size: 32px;
    }
    p {
      font-size: 18px;
      line-height: 1.6;
      margin-bottom: 20px;
    }
    .details {
      background: #f8f9fa;
      padding: 15px;
      border-radius: 8px;
      text-align: left;
      margin-bottom: 20px;
      font-size: 14px;
      border-left: 4px solid #c0392b;
    }
    button {
      background-color: #c0392b;
      color: white;
      border: none;
      padding: 12px 24px;
      font-size: 16px;
      border-radius: 6px;
      cursor: pointer;
      margin: 0 10px;
      transition: background 0.2s;
    }
    button:hover {
      background-color: #a93226;
    }
    button.secondary {
      background-color: transparent;
      color: #666;
      border: 1px solid #ccc;
    }
    button.secondary:hover {
      background-color: #f1f1f1;
      color: #333;
    }
  `;

  const container = document.createElement("div");
  container.className = "container";

  container.innerHTML = `
    <h1>⚠️ Phishing Detected!</h1>
    <p>This website has been identified as a potential phishing attack. It may be trying to steal your passwords or personal information.</p>
    
    <div class="details">
      <strong>Confidence:</strong> ${(data.confidence * 100).toFixed(1)}%<br>
      <strong>Reason:</strong> ${data.explanation.important_features.join(", ") || "Multiple suspicious signals detected."}
    </div>

    <div>
      <button id="go-back">Go Back (Recommended)</button>
      <button id="proceed" class="secondary">Proceed Anyway (Unsafe)</button>
    </div>
    <div style="margin-top: 20px; font-size: 12px; color: #666;">
      <a href="#" id="report-safe">Report as Safe</a>
    </div>
  `;

  shadow.appendChild(style);
  shadow.appendChild(container);
  document.body.appendChild(overlay);

  // Event Listeners
  shadow.getElementById("go-back").addEventListener("click", () => {
    window.history.back();
  });

  shadow.getElementById("proceed").addEventListener("click", () => {
    overlay.remove();
  });

  shadow.getElementById("report-safe").addEventListener("click", async (e) => {
    e.preventDefault();
    await fetch("http://localhost:8000/api/feedback?url=" + encodeURIComponent(data.url) + "&label=safe", { method: "POST" });
    alert("Thanks for your feedback! We will review this site.");
    overlay.remove();
  });
}
