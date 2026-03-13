// --- Navigation ---
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const target = e.currentTarget.getAttribute('data-target');
        
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${target}`).classList.add('active');
    });
});

// --- State ---
let analysisState = {
    riskScore: 0,
    vulns: 0,
    reputation: 'Unknown'
};

// --- API Endpoints ---
const API_BASE = "http://localhost:8000";

// --- Scan Logic ---
const scanBtn = document.getElementById('scan-btn');
scanBtn.addEventListener('click', async () => {
    scanBtn.disabled = true;
    scanBtn.innerHTML = '<span class="icon">⏳</span> Scanning...';
    
    // Reset state
    analysisState.vulns = 0;
    
    try {
        const tabId = chrome.devtools.inspectedWindow.tabId;
        
        document.getElementById('global-status-text').textContent = "Extracting page data...";
        
        // 1. Get Page DOM info
        const pageData = await new Promise((resolve, reject) => {
            chrome.runtime.sendMessage({ action: "triggerScan", tabId: tabId }, response => {
                if (chrome.runtime.lastError) reject(chrome.runtime.lastError);
                else if (response && response.error) reject(new Error(response.error));
                else resolve(response);
            });
        });

        document.getElementById('global-status-text').textContent = "Fetching network logs...";
        
        // 2. Get Network / Header info
        const networkData = await new Promise((resolve, reject) => {
            chrome.runtime.sendMessage({ action: "getNetworkData", tabId: tabId }, response => {
                if (chrome.runtime.lastError) reject(chrome.runtime.lastError);
                else resolve(response);
            });
        });

        document.getElementById('current-url').textContent = pageData.url || '-';
        
        // 3. Analysis & Display
        analyzeForms(pageData.forms || []);
        analyzeScripts(pageData.scripts || []);
        analyzeNetwork(networkData.requests || []);
        analyzeHeaders(networkData.headers || {});
        
        document.getElementById('global-status-text').textContent = "Fetching threat intelligence...";
        
        // 4. API Backend Analysis
        await fetchSignals(pageData.url, pageData);
        
        // Update Overview
        document.getElementById('overview-vulns').textContent = analysisState.vulns;
        
        document.getElementById('global-status-text').textContent = "Scan Complete";
        document.getElementById('global-status-dot').style.backgroundColor = "var(--success-color)";
    } catch (err) {
        console.error("Scan error:", err);
        document.getElementById('global-status-text').textContent = `Scan Failed: ${err.message || 'Unknown Error'}`;
        document.getElementById('global-status-dot').style.backgroundColor = "var(--danger-color)";
    } finally {
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<span class="icon">🔍</span> Scan Page';
    }
});

function createBadge(text, type='default') {
    const classMap = { 'danger': 'danger', 'warning': 'warning', 'success': 'success', 'default': '' };
    return `<span class="tag ${classMap[type]}">${text}</span>`;
}

// --- Analysis Functions ---

function analyzeForms(forms) {
    document.getElementById('badge-forms').textContent = forms.length;
    const list = document.getElementById('forms-list');
    list.innerHTML = '';
    
    if (forms.length === 0) {
        list.innerHTML = '<div class="empty-state">No forms found on page.</div>';
        return;
    }

    forms.forEach(f => {
        let isRisky = false;
        let reasons = [];
        
        if (f.hasPassword && f.method.toUpperCase() === 'GET') {
            isRisky = true;
            reasons.push(createBadge('GET Password', 'danger'));
            analysisState.vulns++;
        }
        if (f.hasPassword && f.crossDomain) {
            isRisky = true;
            reasons.push(createBadge('Cross-Domain Exfiltration', 'danger'));
            analysisState.vulns++;
        }
        if (!f.action) {
            reasons.push(createBadge('No Action', 'warning'));
        }

        const item = document.createElement('div');
        item.className = `list-item ${isRisky ? 'danger' : ''}`;
        item.innerHTML = `
            <div class="item-title">${f.action || 'No Action'} (${f.method})</div>
            <div class="item-tags">
                ${f.hasPassword ? createBadge('Contains Password', 'warning') : createBadge('No Password')}
                ${f.crossDomain ? createBadge('Cross-Domain', 'warning') : ''}
                ${reasons.join('')}
            </div>
        `;
        list.appendChild(item);
    });
}

function analyzeScripts(scripts) {
    document.getElementById('badge-scripts').textContent = scripts.length;
    const list = document.getElementById('scripts-list');
    list.innerHTML = '';
    
    if (scripts.length === 0) {
        list.innerHTML = '<div class="empty-state">No scripts found.</div>';
        return;
    }

    scripts.forEach(s => {
        let isRisky = false;
        let reasons = [];
        
        if (s.isInline && s.content) {
            if (s.content.includes('eval(')) {
                isRisky = true;
                reasons.push(createBadge('eval() used', 'danger'));
                analysisState.vulns++;
            }
            if (s.content.includes('atob(')) {
                reasons.push(createBadge('atob() used', 'warning'));
            }
            // Basic obfuscation check (long lines, lots of hex/special chars)
            if (s.content.length > 500 && s.content.split('\n').length < 3) {
                reasons.push(createBadge('Possible Obfuscation', 'warning'));
            }
        }
        
        if (s.crossDomain) {
            reasons.push(createBadge('Cross-Domain', 'warning'));
        }

        const item = document.createElement('div');
        item.className = `list-item ${isRisky ? 'danger' : ''}`;
        
        const title = s.isInline ? 'Inline Script' : s.src;
        
        item.innerHTML = `
            <div class="item-title">${title}</div>
            <div class="item-tags">
                ${s.isInline ? createBadge('Inline') : createBadge('External')}
                ${reasons.join('')}
            </div>
        `;
        list.appendChild(item);
    });
}

function analyzeNetwork(requests) {
    document.getElementById('badge-network').textContent = requests.length;
    const list = document.getElementById('network-list');
    list.innerHTML = '';
    
    if (requests.length === 0) {
        list.innerHTML = '<div class="empty-state">No network data captured. Refresh page while tab is open.</div>';
        return;
    }

    requests.slice(0, 50).forEach(r => {
        const item = document.createElement('div');
        item.className = 'list-item';
        item.innerHTML = `
            <div class="item-title">${r.method} ${r.url}</div>
            <div class="item-tags">
                ${createBadge(r.type)}
                ${r.ip ? createBadge(r.ip, 'default') : ''}
            </div>
        `;
        list.appendChild(item);
    });
}

function analyzeHeaders(headers) {
    const grid = document.getElementById('headers-grid');
    grid.innerHTML = '';
    
    const requiredHeaders = {
        'content-security-policy': 'Content-Security-Policy',
        'strict-transport-security': 'Strict-Transport-Security',
        'x-frame-options': 'X-Frame-Options',
        'referrer-policy': 'Referrer-Policy'
    };

    for (const [key, displayName] of Object.entries(requiredHeaders)) {
        const val = headers[key] || headers[displayName] || headers[displayName.toLowerCase()];
        const hasHeader = !!val;
        
        if (!hasHeader) {
            analysisState.vulns++;
        }

        const card = document.createElement('div');
        card.className = `header-card ${hasHeader ? '' : 'missing'}`;
        card.style = hasHeader ? '' : 'border-color: rgba(239, 68, 68, 0.5); background: rgba(239, 68, 68, 0.05);';
        card.innerHTML = `
            <div class="header-name">${displayName} <span class="tag ${hasHeader ? 'success' : 'danger'}">${hasHeader ? 'Present' : 'Missing'}</span></div>
            ${hasHeader ? `<div class="header-value">${val}</div>` : `<div class="text-danger" style="font-size: 12px; margin-top: 8px;">Header not found.</div>`}
        `;
        grid.appendChild(card);
    }
}

async function fetchSignals(url, pageData) {
    const container = document.getElementById('signals-container');
    container.innerHTML = '<div class="empty-state">Fetching intelligence...</div>';
    
    try {
        if (!url || !url.startsWith('http')) throw new Error("Invalid URL for backend scan");
        const domainUrl = new URL(url);
        const domain = domainUrl.hostname;

        // Fetch Domain Intel
        let reputationRes = null;
        try {
            const r = await fetch(`${API_BASE}/intel/domain/${domain}`);
            if (r.ok) reputationRes = await r.json();
        } catch (e) { console.warn("Intel fetch failed", e); }

        // Fetch Predict API
        let predictRes = null;
        try {
            const r = await fetch(`${API_BASE}/api/predict`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url })
            });
            if (r.ok) predictRes = await r.json();
        } catch(e) { console.warn("Predict fetch failed", e); }

        container.innerHTML = '';
        
        // Render Reputation
        if (reputationRes) {
            const riskLevel = reputationRes.risk_level || 'unknown';
            document.getElementById('overview-reputation').textContent = riskLevel.toUpperCase();
            document.getElementById('overview-reputation').className = `metric-value indicator-value text-${riskLevel === 'high' ? 'danger' : (riskLevel === 'medium' ? 'warning' : 'success')}`;

            container.innerHTML += `
                <div class="list-item">
                    <div class="item-title">Domain Intelligence: ${domain}</div>
                    <div class="item-tags" style="margin-bottom: 8px;">
                        ${createBadge(`Risk: ${riskLevel}`, riskLevel === 'high' ? 'danger' : 'default')}
                    </div>
                </div>
            `;
        }

        // Render Prediction
        if (predictRes) {
            const isPhishing = predictRes.prediction === "phishing";
            document.getElementById('overview-risk-score').textContent = `${(predictRes.confidence * 100).toFixed(1)}%`;
            if (isPhishing) document.getElementById('overview-risk-score').classList.add('text-danger');

            let reasonsHtml = '';
            if (predictRes.explanation && predictRes.explanation.important_features) {
                reasonsHtml = predictRes.explanation.important_features.map(f => `<li>${f}</li>`).join('');
            }

            container.innerHTML += `
                <div class="list-item ${isPhishing ? 'danger' : ''}">
                    <div class="item-title">Prediction Engine</div>
                    <div class="item-tags" style="margin-bottom: 12px;">
                        ${createBadge(`Result: ${predictRes.prediction}`, isPhishing ? 'danger' : 'success')}
                        ${createBadge(`Confidence: ${(predictRes.confidence * 100).toFixed(1)}%`)}
                    </div>
                    ${reasonsHtml ? `<div style="font-size: 13px;"><strong>Risk Signals:</strong><ul style="margin-left: 20px; margin-top: 4px; color: var(--text-muted);">${reasonsHtml}</ul></div>` : ''}
                </div>
            `;

            const summaryBlock = document.getElementById('overview-summary-text');
            summaryBlock.textContent = isPhishing 
                ? "Critical security alerting! Site exhibits strong phishing characteristics."
                : "Site appears normal, but check vulnerabilities and forms for specific issues.";
            summaryBlock.className = isPhishing ? 'text-danger' : 'text-muted';
        }
        
    } catch (e) {
        container.innerHTML = `<div class="empty-state text-danger">Failed to fetch backend signals: ${e.message}</div>`;
    }
}
