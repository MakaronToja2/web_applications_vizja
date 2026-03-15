// Dashboard — GraphQL queries + subscriptions (WebSocket)

const GQL_URL = "https://localhost:8080/graphql";
const GQL_WS_URL = "wss://localhost:8080/graphql";

// --- GraphQL helper ---

async function gqlQuery(query, variables = {}) {
    const res = await fetch(GQL_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, variables }),
    });
    const json = await res.json();
    if (json.errors) console.error("GraphQL errors:", json.errors);
    return json.data;
}

// --- Server state (updated via WebSocket) ---

let serverCache = [];

function updateServerFromWS(update) {
    const idx = serverCache.findIndex(s => s.serverId === update.serverId);
    if (idx >= 0) {
        serverCache[idx] = { ...serverCache[idx], ...update };
    } else {
        serverCache.push(update);
    }
    renderServers(serverCache);
}

// --- Fetch & render servers ---

async function fetchServers() {
    try {
        const data = await gqlQuery(`{
            servers {
                serverId name status cpu mem lastHeartbeat
            }
        }`);
        serverCache = data.servers;
        renderServers(serverCache);
    } catch (err) {
        document.getElementById("server-list").textContent =
            "Nie można połączyć z API";
    }
}

function renderServers(servers) {
    const container = document.getElementById("server-list");
    if (!servers || servers.length === 0) {
        container.textContent = "Brak zarejestrowanych serwerów";
        return;
    }
    container.innerHTML = servers
        .map(s => `
            <div class="server-card">
                <div class="server-info">
                    <span class="server-id">${s.serverId}</span>
                    <span class="server-metrics">
                        ${s.cpu != null ? `CPU: ${s.cpu}%` : ""}
                        ${s.mem != null ? ` | RAM: ${s.mem}%` : ""}
                        ${s.lastHeartbeat ? ` | ${new Date(s.lastHeartbeat).toLocaleTimeString()}` : ""}
                    </span>
                </div>
                <div class="server-actions">
                    <span class="status ${s.status.toLowerCase()}">${s.status}</span>
                    <button class="delete-btn" onclick="deleteServer('${s.serverId}')">&#x2715;</button>
                </div>
            </div>
        `)
        .join("");
}

// --- Fetch & render stats ---

async function fetchStats() {
    try {
        const data = await gqlQuery(`{
            stats { totalServers serversUp serversDown totalAlerts }
        }`);
        renderStats(data.stats);
    } catch (err) {
        // silent
    }
}

function renderStats(stats) {
    document.getElementById("stats").innerHTML = `
        <div class="stat-box">Serwery <span class="value">${stats.totalServers}</span></div>
        <div class="stat-box" style="color:#22c55e">UP <span class="value">${stats.serversUp}</span></div>
        <div class="stat-box" style="color:#ef4444">DOWN <span class="value">${stats.serversDown}</span></div>
        <div class="stat-box">Alerty <span class="value">${stats.totalAlerts}</span></div>
    `;
}

// --- Fetch & render alert rules ---

async function fetchRules() {
    try {
        const data = await gqlQuery(`{
            alertRules { id name metric operator threshold serverId enabled }
        }`);
        renderRules(data.alertRules);
    } catch (err) {
        // silent
    }
}

function renderRules(rules) {
    const container = document.getElementById("rule-list");
    if (!rules || rules.length === 0) {
        container.textContent = "Brak reguł alertów";
        return;
    }
    container.innerHTML = rules
        .map(r => `
            <div class="rule-card ${r.enabled ? "" : "rule-disabled"}">
                <div class="rule-info">
                    <strong>${r.name}</strong>
                    <span class="rule-condition">${r.metric} ${r.operator} ${r.threshold}</span>
                    ${r.serverId ? `<span> (${r.serverId})</span>` : "<span> (wszystkie)</span>"}
                </div>
                <div class="rule-actions">
                    <button onclick="toggleRule(${r.id}, ${!r.enabled})">
                        ${r.enabled ? "Wyłącz" : "Włącz"}
                    </button>
                    <button class="delete" onclick="deleteRule(${r.id})">Usuń</button>
                </div>
            </div>
        `)
        .join("");
}

// --- Mutations ---

async function createRule(e) {
    e.preventDefault();
    const name = document.getElementById("rule-name").value;
    const metric = document.getElementById("rule-metric").value;
    const operator = document.getElementById("rule-operator").value;
    const threshold = parseFloat(document.getElementById("rule-threshold").value);
    const serverId = document.getElementById("rule-server").value || null;

    const serverArg = serverId ? `, serverId: "${serverId}"` : "";

    await gqlQuery(`mutation {
        createAlertRule(
            name: "${name}", metric: "${metric}",
            operator: "${operator}", threshold: ${threshold}${serverArg}
        ) { id }
    }`);

    document.getElementById("rule-form").reset();
    fetchRules();
}

async function deleteServer(serverId) {
    if (!confirm(`Usunąć serwer ${serverId}?`)) return;
    await gqlQuery(`mutation { deleteServer(serverId: "${serverId}") }`);
    fetchServers();
    fetchStats();
}

async function clearAlerts() {
    if (!confirm("Usunąć wszystkie alerty?")) return;
    await gqlQuery(`mutation { clearAlerts }`);
    fetchAlerts();
    fetchStats();
}

async function deleteRule(id) {
    await gqlQuery(`mutation { deleteAlertRule(id: ${id}) }`);
    fetchRules();
}

async function toggleRule(id, enabled) {
    await gqlQuery(`mutation { toggleAlertRule(id: ${id}, enabled: ${enabled}) { id } }`);
    fetchRules();
}

// --- Fetch recent alerts ---

async function fetchAlerts() {
    try {
        const data = await gqlQuery(`{
            alerts(limit: 20) { id ruleName serverId message timestamp }
        }`);
        renderAlertHistory(data.alerts);
    } catch (err) {
        // silent
    }
}

function renderAlertHistory(alerts) {
    const container = document.getElementById("alert-list");
    if (!alerts || alerts.length === 0) {
        container.innerHTML = "<div style='color:#64748b'>Brak alertów</div>";
        return;
    }
    container.innerHTML = alerts
        .map(a => `
            <div class="alert-item triggered">
                <strong>${a.serverId}</strong> — ${a.message}
                <br><small>${a.ruleName} | ${new Date(a.timestamp).toLocaleString()}</small>
            </div>
        `)
        .join("");
}

// --- WebSocket subscription (GraphQL over WS) ---

function connectSubscription() {
    const wsStatus = document.getElementById("ws-status");
    const ws = new WebSocket(GQL_WS_URL, "graphql-transport-ws");

    ws.onopen = () => {
        ws.send(JSON.stringify({ type: "connection_init" }));
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "connection_ack") {
            wsStatus.textContent = "połączony";
            wsStatus.classList.add("connected");

            // Subscribe to alerts
            ws.send(JSON.stringify({
                id: "alert-sub",
                type: "subscribe",
                payload: {
                    query: `subscription { alertTriggered { id ruleName serverId message timestamp } }`
                }
            }));

            // Subscribe to status changes
            ws.send(JSON.stringify({
                id: "status-sub",
                type: "subscribe",
                payload: {
                    query: `subscription { serverStatusChanged { serverId status cpu mem } }`
                }
            }));
        }

        if (msg.type === "next") {
            const data = msg.payload.data;

            if (data.alertTriggered) {
                const a = data.alertTriggered;
                addLiveAlert(`${a.serverId} — ${a.message} (${a.ruleName})`);
                fetchAlerts();
                fetchStats();
            }

            if (data.serverStatusChanged) {
                updateServerFromWS(data.serverStatusChanged);
                fetchStats();
            }
        }
    };

    ws.onclose = () => {
        wsStatus.textContent = "rozłączony";
        wsStatus.classList.remove("connected");
        setTimeout(connectSubscription, 3000);
    };

    ws.onerror = () => ws.close();
}

function addLiveAlert(text) {
    const container = document.getElementById("alert-list");
    const el = document.createElement("div");
    el.className = "alert-item info";
    el.innerHTML = `<strong>NOWY</strong> ${text} <small>${new Date().toLocaleTimeString()}</small>`;
    container.prepend(el);

    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

// --- Init ---

document.getElementById("rule-form").addEventListener("submit", createRule);

fetchServers();
fetchStats();
fetchRules();
fetchAlerts();
connectSubscription();

// No polling — all updates come via WebSocket subscriptions
