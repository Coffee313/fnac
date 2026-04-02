// API Base URL
const API_URL = '/api';

// Message display
function showMessage(text, type = 'success') {
    const msg = document.getElementById('message');
    msg.textContent = text;
    msg.className = `message show ${type}`;
    setTimeout(() => msg.classList.remove('show'), 3000);
}

// Tab switching
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
        loadTabData(btn.dataset.tab);
    });
});

// Load tab data
async function loadTabData(tab) {
    if (tab === 'devices') {
        await loadDeviceGroups();
        await loadDevices();
    } else if (tab === 'clients') {
        await loadClientGroups();
        await loadClients();
    } else if (tab === 'policies') {
        await loadClientGroupsForPolicy();
        await loadPolicies();
    } else if (tab === 'logs') {
        await loadLogs();
    }
}

// ===== DEVICES =====
async function loadDeviceGroups() {
    try {
        const res = await fetch(`${API_URL}/device-groups`);
        const groups = await res.json();
        const container = document.getElementById('deviceGroupsContainer');
        container.innerHTML = groups.map(g => `
            <div class="item">
                <div class="item-info">
                    <p><strong>Name:</strong> ${g.name}</p>
                </div>
                <div class="item-actions">
                    <button class="btn-delete" onclick="deleteDeviceGroup('${g.name}')">Delete</button>
                </div>
            </div>
        `).join('');
        
        const select = document.getElementById('deviceGroup');
        select.innerHTML = '<option value="">Select Device Group</option>' + 
            groups.map(g => `<option value="${g.name}">${g.name}</option>`).join('');
    } catch (e) {
        showMessage('Error loading device groups', 'error');
    }
}

async function loadDevices() {
    try {
        const res = await fetch(`${API_URL}/devices`);
        const devices = await res.json();
        const container = document.getElementById('devicesContainer');
        container.innerHTML = devices.map(d => `
            <div class="item">
                <div class="item-info">
                    <p><strong>Name:</strong> ${d.name}</p>
                    <p><strong>IP:</strong> ${d.ip_address}</p>
                    <p><strong>Group:</strong> ${d.device_group_name}</p>
                </div>
                <div class="item-actions">
                    <button class="btn-delete" onclick="deleteDevice('${d.name}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        showMessage('Error loading devices', 'error');
    }
}

document.getElementById('deviceGroupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('groupName').value;
    try {
        const res = await fetch(`${API_URL}/device-groups`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (res.ok) {
            showMessage('Device group created');
            e.target.reset();
            await loadDeviceGroups();
        } else {
            const err = await res.json();
            showMessage(err.error || 'Error creating group', 'error');
        }
    } catch (e) {
        showMessage('Error creating group', 'error');
    }
});

document.getElementById('deviceForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('deviceId').value;
    const ip_address = document.getElementById('deviceIp').value;
    const shared_secret = document.getElementById('deviceSecret').value;
    const device_group_name = document.getElementById('deviceGroup').value;
    try {
        const res = await fetch(`${API_URL}/devices`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, ip_address, shared_secret, device_group_name })
        });
        if (res.ok) {
            showMessage('Device created');
            e.target.reset();
            await loadDevices();
        } else {
            const err = await res.json();
            showMessage(err.error || 'Error creating device', 'error');
        }
    } catch (e) {
        showMessage('Error creating device', 'error');
    }
});

async function deleteDevice(name) {
    if (!confirm('Delete this device?')) return;
    try {
        const res = await fetch(`${API_URL}/devices/${name}`, { method: 'DELETE' });
        if (res.ok) {
            showMessage('Device deleted');
            await loadDevices();
        } else {
            showMessage('Error deleting device', 'error');
        }
    } catch (e) {
        showMessage('Error deleting device', 'error');
    }
}

async function deleteDeviceGroup(name) {
    if (!confirm('Delete this group?')) return;
    try {
        const res = await fetch(`${API_URL}/device-groups/${name}`, { method: 'DELETE' });
        if (res.ok) {
            showMessage('Group deleted');
            await loadDeviceGroups();
        } else {
            const err = await res.json();
            showMessage(err.error || 'Error deleting group', 'error');
        }
    } catch (e) {
        showMessage('Error deleting group', 'error');
    }
}

// ===== CLIENTS =====
async function loadClientGroups() {
    try {
        const res = await fetch(`${API_URL}/client-groups`);
        const groups = await res.json();
        const container = document.getElementById('clientGroupsContainer');
        container.innerHTML = groups.map(g => `
            <div class="item">
                <div class="item-info">
                    <p><strong>Name:</strong> ${g.name}</p>
                </div>
                <div class="item-actions">
                    <button class="btn-delete" onclick="deleteClientGroup('${g.name}')">Delete</button>
                </div>
            </div>
        `).join('');
        
        const select = document.getElementById('clientGroup');
        select.innerHTML = '<option value="">Select Client Group</option>' + 
            groups.map(g => `<option value="${g.name}">${g.name}</option>`).join('');
    } catch (e) {
        showMessage('Error loading client groups', 'error');
    }
}

async function loadClients() {
    try {
        const res = await fetch(`${API_URL}/clients`);
        const clients = await res.json();
        const container = document.getElementById('clientsContainer');
        container.innerHTML = clients.map(c => `
            <div class="item">
                <div class="item-info">
                    <p><strong>MAC:</strong> ${c.mac_address}</p>
                    ${c.name ? `<p><strong>Name:</strong> ${c.name}</p>` : ''}
                    <p><strong>Group:</strong> ${c.client_group_name}</p>
                </div>
                <div class="item-actions">
                    <button class="btn-delete" onclick="deleteClient('${c.mac_address}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        showMessage('Error loading clients', 'error');
    }
}

document.getElementById('clientGroupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('cGroupName').value;
    try {
        const res = await fetch(`${API_URL}/client-groups`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (res.ok) {
            showMessage('Client group created');
            e.target.reset();
            await loadClientGroups();
        } else {
            const err = await res.json();
            showMessage(err.error || 'Error creating group', 'error');
        }
    } catch (e) {
        showMessage('Error creating group', 'error');
    }
});

document.getElementById('clientForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const mac_address = document.getElementById('clientMac').value;
    const name = document.getElementById('clientName').value;
    const client_group_name = document.getElementById('clientGroup').value;
    try {
        const res = await fetch(`${API_URL}/clients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mac_address, name, client_group_name })
        });
        if (res.ok) {
            showMessage('Client created');
            e.target.reset();
            await loadClients();
        } else {
            const err = await res.json();
            showMessage(err.error || 'Error creating client', 'error');
        }
    } catch (e) {
        showMessage('Error creating client', 'error');
    }
});

async function deleteClient(mac) {
    if (!confirm('Delete this client?')) return;
    try {
        const res = await fetch(`${API_URL}/clients/${encodeURIComponent(mac)}`, { method: 'DELETE' });
        if (res.ok) {
            showMessage('Client deleted');
            await loadClients();
        } else {
            showMessage('Error deleting client', 'error');
        }
    } catch (e) {
        showMessage('Error deleting client', 'error');
    }
}

async function deleteClientGroup(name) {
    if (!confirm('Delete this group?')) return;
    try {
        const res = await fetch(`${API_URL}/client-groups/${name}`, { method: 'DELETE' });
        if (res.ok) {
            showMessage('Group deleted');
            await loadClientGroups();
        } else {
            const err = await res.json();
            showMessage(err.error || 'Error deleting group', 'error');
        }
    } catch (e) {
        showMessage('Error deleting group', 'error');
    }
}

// ===== POLICIES =====
async function loadClientGroupsForPolicy() {
    try {
        const res = await fetch(`${API_URL}/client-groups`);
        const groups = await res.json();
        const select = document.getElementById('policyClientGroup');
        select.innerHTML = '<option value="">Select Client Group</option>' + 
            groups.map(g => `<option value="${g.name}">${g.name}</option>`).join('');
    } catch (e) {
        showMessage('Error loading client groups', 'error');
    }
}

async function loadPolicies() {
    try {
        const res = await fetch(`${API_URL}/policies`);
        const policies = await res.json();
        const container = document.getElementById('policiesContainer');
        container.innerHTML = policies.map(p => `
            <div class="item">
                <div class="item-info">
                    <p><strong>Name:</strong> ${p.name}</p>
                    <p><strong>Client Group:</strong> ${p.client_group_name}</p>
                    <p><strong>Decision:</strong> <span class="status-badge status-${p.decision.toLowerCase()}">${p.decision}</span></p>
                    ${p.vlan_id ? `<p><strong>VLAN:</strong> ${p.vlan_id}</p>` : ''}
                </div>
                <div class="item-actions">
                    <button class="btn-delete" onclick="deletePolicy('${p.name}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        showMessage('Error loading policies', 'error');
    }
}

document.getElementById('policyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('policyId').value;
    const client_group_name = document.getElementById('policyClientGroup').value;
    const decision = document.getElementById('policyDecision').value;
    const vlan_id = document.getElementById('policyVlan').value ? parseInt(document.getElementById('policyVlan').value) : null;
    try {
        const res = await fetch(`${API_URL}/policies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, client_group_name, decision, vlan_id })
        });
        if (res.ok) {
            showMessage('Policy created');
            e.target.reset();
            await loadPolicies();
        } else {
            const err = await res.json();
            showMessage(err.error || 'Error creating policy', 'error');
        }
    } catch (e) {
        showMessage('Error creating policy', 'error');
    }
});

async function deletePolicy(name) {
    if (!confirm('Delete this policy?')) return;
    try {
        const res = await fetch(`${API_URL}/policies/${name}`, { method: 'DELETE' });
        if (res.ok) {
            showMessage('Policy deleted');
            await loadPolicies();
        } else {
            showMessage('Error deleting policy', 'error');
        }
    } catch (e) {
        showMessage('Error deleting policy', 'error');
    }
}

// ===== LOGS =====
async function loadLogs() {
    try {
        const mac = document.getElementById('filterMac').value;
        const outcome = document.getElementById('filterOutcome').value;
        let url = `${API_URL}/logs`;
        const params = [];
        if (mac) params.push(`mac_address=${encodeURIComponent(mac)}`);
        if (outcome) params.push(`outcome=${outcome}`);
        if (params.length) url += '?' + params.join('&');
        
        const res = await fetch(url);
        const logs = await res.json();
        const container = document.getElementById('logsContainer');
        
        // Update log counter
        const logCounter = document.getElementById('logCounter');
        if (logCounter) {
            logCounter.textContent = logs.length;
        }
        
        if (logs.length === 0) {
            container.innerHTML = '<div class="no-logs">No authentication logs yet</div>';
            return;
        }
        
        container.innerHTML = logs.map(l => {
            // Parse timestamp - it's already in GMT+3 from the database
            const timestamp = new Date(l.timestamp);
            // Format time as HH:MM:SS
            const hours = String(timestamp.getUTCHours()).padStart(2, '0');
            const minutes = String(timestamp.getUTCMinutes()).padStart(2, '0');
            const seconds = String(timestamp.getUTCSeconds()).padStart(2, '0');
            const timeStr = `${hours}:${minutes}:${seconds}`;
            
            // Format date as DD.MM.YYYY
            const day = String(timestamp.getUTCDate()).padStart(2, '0');
            const month = String(timestamp.getUTCMonth() + 1).padStart(2, '0');
            const year = timestamp.getUTCFullYear();
            const dateStr = `${day}.${month}.${year}`;
            
            const isSuccess = l.outcome === 'success';
            const icon = isSuccess ? '✓' : '✗';
            const vlanInfo = l.vlan_id ? ` • VLAN ${l.vlan_id}` : '';
            const policyInfo = l.policy_name ? ` • Policy: ${l.policy_name}` : '';
            
            return `
                <div class="log-item ${isSuccess ? 'log-success' : 'log-failure'}">
                    <div class="log-icon">${icon}</div>
                    <div class="log-content">
                        <div class="log-main">
                            <span class="log-time">${dateStr} ${timeStr}</span>
                            <span class="log-mac">${l.client_mac}</span>
                            <span class="log-status">${isSuccess ? 'ACCEPT' : 'REJECT'}${vlanInfo}${policyInfo}</span>
                        </div>
                        <div class="log-meta">
                            <span class="log-device">Device: ${l.device_id}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        showMessage('Error loading logs', 'error');
    }
}

document.getElementById('filterForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    await loadLogs();
});

// Auto-refresh logs every 5 seconds when logs tab is active
let logsRefreshInterval = null;

document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Clear existing interval
        if (logsRefreshInterval) clearInterval(logsRefreshInterval);
        
        // Start auto-refresh if logs tab is selected
        if (btn.dataset.tab === 'logs') {
            logsRefreshInterval = setInterval(loadLogs, 5000);
        }
    });
});

// Initial load
loadTabData('devices');

// ===== IMPORT/EXPORT =====

// Export configuration
document.getElementById('exportBtn').addEventListener('click', async () => {
    try {
        const res = await fetch(`${API_URL}/export`);
        if (!res.ok) {
            const err = await res.json();
            showMessage(`Export failed: ${err.error}`, 'error');
            return;
        }
        
        const config = await res.json();
        const dataStr = JSON.stringify(config, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `fnac-config-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        showMessage('Configuration exported successfully');
    } catch (e) {
        showMessage('Error exporting configuration', 'error');
    }
});

// Import configuration
document.getElementById('importForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fileInput = document.getElementById('importFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showMessage('Please select a file', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const res = await fetch(`${API_URL}/import`, {
            method: 'POST',
            body: formData
        });
        
        if (!res.ok) {
            const err = await res.json();
            showMessage(`Import failed: ${err.error}`, 'error');
            return;
        }
        
        const result = await res.json();
        
        // Display import results
        const resultsDiv = document.getElementById('importResults');
        let resultsHtml = '<h4>Import Results:</h4>';
        
        for (const [category, stats] of Object.entries(result.results)) {
            resultsHtml += `
                <div class="import-result-item">
                    <strong>${category}:</strong> 
                    ${stats.success} imported
                    ${stats.failed > 0 ? `, ${stats.failed} failed` : ''}
                    ${stats.errors.length > 0 ? `<br><small>${stats.errors.join('<br>')}</small>` : ''}
                </div>
            `;
        }
        
        resultsDiv.innerHTML = resultsHtml;
        resultsDiv.style.display = 'block';
        
        fileInput.value = '';
        showMessage('Configuration imported successfully');
        
        // Reload all data
        setTimeout(() => {
            loadTabData('devices');
        }, 500);
    } catch (e) {
        showMessage('Error importing configuration', 'error');
    }
});
