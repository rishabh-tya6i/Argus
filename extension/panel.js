// --- Constants ---
const API_BASE = "http://localhost:8000";
// In a real app, this should be securely stored/retrieved
const API_KEY = "argus_default_key"; 

// --- State Management ---
let currentTabId = chrome.devtools.inspectedWindow.tabId;
let tabCache = {}; // Stores results per tabId

// --- Navigation ---
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const target = e.currentTarget.getAttribute('data-target');
        switchView(target);
    });
});

function switchView(target) {
    document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-target') === target);
    });
    document.querySelectorAll('.view').forEach(v => {
        v.classList.toggle('active', v.id === `view-${target}`);
    });
}

// --- Initialization ---
async function init() {
    // Get current tab URL on startup
    chrome.devtools.inspectedWindow.eval("window.location.href", (url) => {
        if (url) {
            document.getElementById('current-url').textContent = url;
            // Optionally auto-scan or load from cache
            if (tabCache[currentTabId]) renderAll(tabCache[currentTabId]);
        }
    });

    // Setup network monitoring
    chrome.devtools.network.onRequestFinished.addListener(handleNetworkRequest);
}

// --- Scan Logic ---
const scanBtn = document.getElementById('scan-btn');
scanBtn.addEventListener('click', async () => {
    await performFullScan();
});

async function performFullScan() {
    scanBtn.disabled = true;
    scanBtn.innerHTML = '<span class="icon">⏳</span> Scanning...';
    updateStatus("Initializing scan...", "warning");

    try {
        // 1. Get URL and DOM Data
        updateStatus("Extracting DOM metrics...", "warning");
        const pageData = await new Promise((resolve, reject) => {
            chrome.runtime.sendMessage({ action: "triggerScan", tabId: currentTabId }, response => {
                if (chrome.runtime.lastError) reject(chrome.runtime.lastError);
                else if (response && response.error) reject(new Error(response.error));
                else resolve(response);
            });
        });

        const url = pageData.url;
        document.getElementById('current-url').textContent = url;

        // 2. Fetch Predictive Analysis
        updateStatus("Querying Argus AI Engine...", "warning");
        const predictRes = await fetchWithAuth(`${API_BASE}/api/predict`, {
            method: "POST",
            body: JSON.stringify({ url: url })
        });

        // 3. Fetch Domain Intel
        updateStatus("Fetching Domain Intelligence...", "warning");
        const domain = new URL(url).hostname;
        const intelRes = await fetchWithAuth(`${API_BASE}/intel/domain/${domain}`);

        // 4. Fetch Historical / Async Data & Background Stats
        updateStatus("Syncing security records...", "warning");
        const [scans, sandbox, securityScans, bgData] = await Promise.all([
            fetchWithAuth(`${API_BASE}/scans?url=${encodeURIComponent(url)}`),
            fetchWithAuth(`${API_BASE}/sandbox/runs?url=${encodeURIComponent(url)}`),
            fetchWithAuth(`${API_BASE}/security-scans?url=${encodeURIComponent(url)}`),
            new Promise(r => chrome.runtime.sendMessage({ action: "getNetworkData", tabId: currentTabId }, r))
        ]);

        // 5. Update Cache
        tabCache[currentTabId] = {
            url,
            pageData,
            predictRes,
            intelRes,
            scans: scans || [],
            sandbox: sandbox || [],
            securityScans: securityScans || [],
            network: bgData?.requests || tabCache[currentTabId]?.network || [],
            headers: bgData?.headers || {}
        };

        renderAll(tabCache[currentTabId]);
        updateStatus("Scan Complete", "success");

    } catch (err) {
        console.error("Scan failed:", err);
        updateStatus(`Scan Failed: ${err.message}`, "danger");
    } finally {
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<span class="icon">🔍</span> Scan Page';
    }
}

// --- Network Tracking ---
function handleNetworkRequest(request) {
    if (!tabCache[currentTabId]) tabCache[currentTabId] = { network: [] };
    if (!tabCache[currentTabId].network) tabCache[currentTabId].network = [];

    const reqData = {
        url: request.request.url,
        method: request.request.method,
        type: request._resourceType || 'other',
        status: request.response.status,
        time: request.time,
        ip: request.serverIPAddress,
        isSensitive: request.request.method === 'POST' && 
                     (request.request.postData?.text?.includes('password') || 
                      request.request.postData?.text?.includes('secret')),
        isCrossDomain: false
    };

    try {
        const reqUrl = new URL(reqData.url);
        const pageUrl = new URL(document.getElementById('current-url').textContent);
        reqData.isCrossDomain = reqUrl.origin !== pageUrl.origin;
    } catch(e) {}

    tabCache[currentTabId].network.unshift(reqData);
    if (tabCache[currentTabId].network.length > 100) tabCache[currentTabId].network.pop();

    updateNetworkBadge();
    if (document.getElementById('view-network').classList.contains('active')) {
        renderNetwork(tabCache[currentTabId].network);
    }
}

// --- Rendering Logic ---

function renderAll(data) {
    renderOverview(data);
    renderForms(data.pageData.forms || []);
    renderScripts(data.pageData.scripts || []);
    renderNetwork(data.network || []);
    renderSecurity(data);
    renderSandbox(data.sandbox || []);
}

function renderOverview(data) {
    const { predictRes, intelRes } = data;
    
    // Risk Score & Classification
    const riskScore = predictRes?.confidence || 0;
    const classification = predictRes?.prediction || '--';
    
    const scoreEl = document.getElementById('overview-risk-score');
    scoreEl.textContent = `${(riskScore * 100).toFixed(1)}%`;
    scoreEl.className = `metric-value ${riskScore > 0.7 ? 'text-danger' : (riskScore > 0.3 ? 'text-warning' : 'text-success')}`;

    const classEl = document.getElementById('overview-classification');
    classEl.textContent = classification.toUpperCase();
    classEl.className = `metric-value ${classification === 'phishing' ? 'text-danger' : (classification === 'suspicious' ? 'text-warning' : 'text-success')}`;

    // Reputation
    const repEl = document.getElementById('overview-reputation');
    const riskLevel = intelRes?.risk_level || 'unknown';
    repEl.textContent = riskLevel.toUpperCase();
    repEl.className = `metric-value ${riskLevel === 'high' ? 'text-danger' : (riskLevel === 'medium' ? 'text-warning' : 'text-success')}`;

    // Insights
    const insightContainer = document.getElementById('overview-explanation');
    insightContainer.innerHTML = '';
    if (predictRes?.explanation?.important_features) {
        predictRes.explanation.important_features.forEach(feat => {
            const item = document.createElement('div');
            item.className = 'explanation-item';
            item.innerHTML = `<span class="icon">🔍</span> ${feat}`;
            insightContainer.appendChild(item);
        });
    } else {
        insightContainer.innerHTML = '<div class="empty-state">No specific insights found.</div>';
    }

    // Domain Intel
    document.getElementById('intel-age').textContent = intelRes?.domain_age || '--';
    document.getElementById('intel-feeds').textContent = intelRes?.threat_counts ? Object.values(intelRes.threat_counts).reduce((a, b) => a + b, 0) : '0';
    document.getElementById('intel-homograph').textContent = intelRes?.is_homograph ? 'DETECTED' : 'Clean';
}

function renderForms(forms) {
    document.getElementById('badge-forms').textContent = forms.length;
    const list = document.getElementById('forms-list');
    list.innerHTML = '';

    if (!forms.length) {
        list.innerHTML = '<div class="empty-state">No forms detected.</div>';
        return;
    }

    forms.forEach(f => {
        const item = document.createElement('div');
        item.className = `list-item ${f.hasPassword || f.crossDomain ? 'warning' : ''}`;
        if (f.crossDomain && f.hasPassword) item.className = 'list-item danger';

        item.innerHTML = `
            <div class="item-title">${f.action || 'No Action URL'} [${f.method}]</div>
            <div class="item-tags">
                ${f.hasPassword ? createTag('Password Field', 'danger') : createTag('Normal')}
                ${f.crossDomain ? createTag('Cross-Domain Submission', 'warning') : createTag('Same-Origin')}
                ${f.hasHiddenFields ? createTag('Hidden Inputs', 'default') : ''}
            </div>
        `;
        list.appendChild(item);
    });
}

function renderScripts(scripts) {
    document.getElementById('badge-scripts').textContent = scripts.length;
    const list = document.getElementById('scripts-list');
    list.innerHTML = '';

    if (!scripts.length) {
        list.innerHTML = '<div class="empty-state">No scripts detected.</div>';
        return;
    }

    scripts.forEach(s => {
        const item = document.createElement('div');
        const isRisky = s.content?.includes('eval(') || s.crossDomain;
        item.className = `list-item ${isRisky ? 'warning' : ''}`;

        item.innerHTML = `
            <div class="item-title">${s.isInline ? 'Inline Script' : s.src}</div>
            <div class="item-tags">
                ${s.isInline ? createTag('Inline') : createTag('External')}
                ${s.content?.includes('eval(') ? createTag('eval() detected', 'danger') : ''}
                ${s.crossDomain ? createTag('Third-Party Domain', 'warning') : ''}
            </div>
        `;
        list.appendChild(item);
    });
}

function renderNetwork(requests) {
    document.getElementById('badge-network').textContent = requests.length;
    const list = document.getElementById('network-list');
    list.innerHTML = '';

    if (!requests.length) {
        list.innerHTML = '<div class="empty-state">No network data yet. Try refreshing the page.</div>';
        return;
    }

    requests.forEach(r => {
        const item = document.createElement('div');
        item.className = `list-item ${r.isSensitive ? 'danger' : (r.isCrossDomain ? 'warning' : '')}`;
        item.innerHTML = `
            <div class="item-title">${r.method} ${r.url}</div>
            <div class="item-tags">
                ${createTag(r.type)}
                ${r.isSensitive ? createTag('SENSITIVE POST', 'danger') : ''}
                ${r.isCrossDomain ? createTag('Cross-Domain', 'warning') : ''}
                ${r.status ? createTag(r.status, r.status >= 400 ? 'danger' : 'success') : ''}
            </div>
        `;
        list.appendChild(item);
    });
}

function renderSecurity(data) {
    // Render Headers from Background Data
    const grid = document.getElementById('headers-grid');
    grid.innerHTML = '';
    
    const requiredHeaders = {
        'content-security-policy': 'Content-Security-Policy',
        'strict-transport-security': 'Strict-Transport-Security',
        'x-frame-options': 'X-Frame-Options',
        'referrer-policy': 'Referrer-Policy',
        'x-content-type-options': 'X-Content-Type-Options'
    };

    const actualHeaders = data.headers || {};

    Object.entries(requiredHeaders).forEach(([key, displayName]) => {
        const value = actualHeaders[key];
        const hasHeader = !!value;
        const card = document.createElement('div');
        card.className = `header-card ${hasHeader ? '' : 'missing'}`;
        card.innerHTML = `
            <div class="header-name">${displayName} ${hasHeader ? createTag('Present', 'success') : createTag('Missing', 'danger')}</div>
            <div class="${hasHeader ? 'header-value' : 'text-danger'}">${hasHeader ? value : 'Header not found on main frame.'}</div>
        `;
        grid.appendChild(card);
    });

    // Render Backend Scans
    const scanList = document.getElementById('security-scans-list');
    scanList.innerHTML = '';
    if (data.securityScans && data.securityScans.length) {
        data.securityScans.forEach(s => {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <div class="item-title">Security Scan #${s.id}</div>
                <div class="item-tags">
                    ${createTag(s.status, s.status === 'completed' ? 'success' : 'warning')}
                    ${createTag(new Date(s.created_at).toLocaleString())}
                </div>
            `;
            scanList.appendChild(item);
        });
    } else {
        scanList.innerHTML = '<div class="empty-state">No backend security scans found.</div>';
    }
}

function renderSandbox(runs) {
    const container = document.getElementById('sandbox-content');
    container.innerHTML = '';

    if (!runs.length) {
        container.innerHTML = '<div class="empty-state">No sandbox data available for this tab.</div>';
        return;
    }

    const run = runs[0]; // Show latest
    container.innerHTML = `
        <div class="sandbox-run-card">
            <div class="sandbox-header">
                <div>
                    <h3 style="margin-bottom: 4px;">Run #${run.id}</h3>
                    <div class="text-muted">${new Date(run.created_at).toLocaleString()}</div>
                </div>
                <div class="tag ${run.status === 'completed' ? 'success' : 'warning'}">${run.status.toUpperCase()}</div>
            </div>
            
            <div class="dashboard-grid">
                 <div class="metric-card">
                    <div class="metric-title">Risk Score</div>
                    <div class="metric-value ${run.risk_score > 0.7 ? 'text-danger' : ''}">${run.risk_score ? (run.risk_score * 100).toFixed(1) + '%' : '--'}</div>
                 </div>
            </div>
            
            <button class="primary-btn" onclick="window.open('${API_BASE}/dashboard/sandbox/${run.id}')">View Full Report</button>
        </div>
    `;
}

// --- Utilities ---

async function fetchWithAuth(url, options = {}) {
    const headers = {
        ...options.headers,
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    };
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) return null;
    return response.json();
}

function updateStatus(text, type) {
    const dot = document.getElementById('global-status-dot');
    const label = document.getElementById('global-status-text');
    label.textContent = text;
    
    const colors = {
        success: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
        default: "#94a3b8"
    };
    dot.style.backgroundColor = colors[type] || colors.default;
}

function createTag(text, type = 'default') {
    return `<span class="tag ${type}">${text}</span>`;
}

function updateNetworkBadge() {
    const count = tabCache[currentTabId]?.network?.length || 0;
    document.getElementById('badge-network').textContent = count;
}

// Start
init();
