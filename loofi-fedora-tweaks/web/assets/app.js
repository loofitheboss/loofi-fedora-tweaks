// Loofi Web Dashboard - JavaScript

const API_BASE = window.location.origin;
const TOKEN_KEY = 'loofi_jwt_token';
const REFRESH_INTERVAL = 10000; // 10 seconds

// State Management
let authToken = null;
let refreshTimer = null;

// DOM Elements
const loginScreen = document.getElementById('login-screen');
const dashboardScreen = document.getElementById('dashboard-screen');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const apiKeyInput = document.getElementById('api-key-input');
const logoutBtn = document.getElementById('logout-btn');
const systemInfoContainer = document.getElementById('system-info');
const systemInfoTime = document.getElementById('system-info-time');
const agentStatusContainer = document.getElementById('agent-status');
const executeForm = document.getElementById('execute-form');
const executeResult = document.getElementById('execute-result');
const executeOutput = document.getElementById('execute-output');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    loginForm.addEventListener('submit', handleLogin);
    logoutBtn.addEventListener('click', handleLogout);
    executeForm.addEventListener('submit', handleExecute);
}

// Authentication
function checkAuth() {
    authToken = sessionStorage.getItem(TOKEN_KEY);
    if (authToken) {
        showDashboard();
    } else {
        showLogin();
    }
}

function showLogin() {
    loginScreen.classList.remove('hidden');
    dashboardScreen.classList.add('hidden');
    clearInterval(refreshTimer);
}

function showDashboard() {
    loginScreen.classList.add('hidden');
    dashboardScreen.classList.remove('hidden');
    loadDashboardData();
    startAutoRefresh();
}

async function handleLogin(e) {
    e.preventDefault();
    const apiKey = apiKeyInput.value.trim();
    loginError.textContent = '';

    try {
        const response = await fetch(`${API_BASE}/api/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `api_key=${encodeURIComponent(apiKey)}`
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Invalid API key');
        }

        const data = await response.json();
        authToken = data.access_token;
        sessionStorage.setItem(TOKEN_KEY, authToken);
        apiKeyInput.value = '';
        showDashboard();
    } catch (error) {
        loginError.textContent = error.message;
    }
}

function handleLogout() {
    authToken = null;
    sessionStorage.removeItem(TOKEN_KEY);
    showLogin();
}

// API Calls
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            handleLogout();
            throw new Error('Unauthorized - Please login again');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Request failed: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        throw error;
    }
}

// Dashboard Data Loading
async function loadDashboardData() {
    await Promise.all([
        loadSystemInfo(),
        loadAgentStatus(),
    ]);
}

async function loadSystemInfo() {
    try {
        const data = await apiRequest('/api/info');
        renderSystemInfo(data);
        systemInfoTime.textContent = new Date().toLocaleTimeString();
    } catch (error) {
        systemInfoContainer.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
    }
}

async function loadAgentStatus() {
    try {
        const data = await apiRequest('/api/agents');
        renderAgentStatus(data);
    } catch (error) {
        agentStatusContainer.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
    }
}

// Rendering Functions
function renderSystemInfo(data) {
    const health = data.health || {};
    const cpu = health.cpu || {};
    const memory = health.memory || {};

    const items = [
        { label: 'Version', value: data.version },
        { label: 'Codename', value: data.codename },
        { label: 'System Type', value: data.system_type },
        { label: 'Package Manager', value: data.package_manager },
        { label: 'Hostname', value: health.hostname || 'N/A' },
        { label: 'Uptime', value: health.uptime || 'N/A' },
        { label: 'CPU Status', value: cpu.status || 'N/A' },
        { label: 'CPU Load', value: cpu.load_1min ? `${cpu.load_1min} (1m)` : 'N/A' },
        { label: 'Memory Status', value: memory.status || 'N/A' },
        { label: 'Memory Usage', value: memory.used ? `${memory.used} / ${memory.total}` : 'N/A' },
    ];

    systemInfoContainer.innerHTML = items.map(item => `
        <div class="info-item">
            <div class="info-label">${item.label}</div>
            <div class="info-value">${escapeHtml(String(item.value))}</div>
        </div>
    `).join('');
}

function renderAgentStatus(data) {
    const agents = data.agents || [];
    const states = data.states || [];

    if (agents.length === 0) {
        agentStatusContainer.innerHTML = '<div class="loading">No agents found</div>';
        return;
    }

    agentStatusContainer.innerHTML = agents.map((agent, idx) => {
        const state = states[idx] || {};
        const status = state.status || 'unknown';
        const statusClass = `status-${status.toLowerCase()}`;
        const lastRun = state.last_run ? new Date(state.last_run).toLocaleString() : 'Never';

        return `
            <div class="agent-card ${statusClass}">
                <div class="agent-name">${escapeHtml(agent.name || agent.agent_id)}</div>
                <span class="agent-status ${statusClass}">${escapeHtml(status)}</span>
                <div class="agent-meta">
                    <div>Enabled: ${agent.enabled ? 'Yes' : 'No'}</div>
                    <div>Last run: ${lastRun}</div>
                </div>
            </div>
        `;
    }).join('');
}

// Action Executor
async function handleExecute(e) {
    e.preventDefault();

    const command = document.getElementById('command-input').value.trim();
    const argsInput = document.getElementById('args-input').value.trim();
    const pkexec = document.getElementById('pkexec-checkbox').checked;
    const preview = document.getElementById('preview-checkbox').checked;

    // Parse args
    const args = argsInput ? argsInput.split(',').map(arg => arg.trim()).filter(Boolean) : [];

    executeResult.classList.add('hidden');
    executeOutput.textContent = '';

    try {
        const payload = {
            command,
            args,
            pkexec,
            preview
        };

        const result = await apiRequest('/api/execute', {
            method: 'POST',
            body: JSON.stringify(payload),
        });

        displayExecuteResult(result);
    } catch (error) {
        displayExecuteResult({
            success: false,
            message: error.message,
            preview: false,
        });
    }
}

function displayExecuteResult(result) {
    executeResult.classList.remove('hidden');
    executeOutput.textContent = JSON.stringify(result, null, 2);
}

// Auto-refresh
function startAutoRefresh() {
    clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
        loadSystemInfo();
        loadAgentStatus();
    }, REFRESH_INTERVAL);
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
