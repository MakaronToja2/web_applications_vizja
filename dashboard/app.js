// Dashboard — fetches servers from REST API and listens for WebSocket alerts

const API_URL = "https://localhost:8443/api";
const WS_URL = "ws://localhost:8765";

// Fetch server list from REST API
async function fetchServers() {
    try {
        const res = await fetch(`${API_URL}/servers`, {
            // Accept self-signed cert in development
        });
        const servers = await res.json();
        renderServers(servers);
    } catch (err) {
        document.getElementById("server-list").textContent =
            "Nie można połączyć z API";
    }
}

function renderServers(servers) {
    const container = document.getElementById("server-list");
    if (servers.length === 0) {
        container.textContent = "Brak zarejestrowanych serwerów";
        return;
    }
    container.innerHTML = servers
        .map(
            (s) => `
        <div class="server-card">
            <span>${s.server_id || s.id}</span>
            <span class="status ${(s.status || "unknown").toLowerCase()}">${s.status || "UNKNOWN"}</span>
        </div>
    `
        )
        .join("");
}

// WebSocket connection for real-time alerts
function connectWebSocket() {
    const ws = new WebSocket(WS_URL);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        addAlert(data);
        // Refresh server list on status changes
        if (data.type === "alert" || data.type === "recovery") {
            fetchServers();
        }
    };

    ws.onclose = () => {
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

function addAlert(data) {
    const container = document.getElementById("alert-list");
    const cssClass = data.status === "DOWN" ? "down" : "up";
    const label = data.status === "DOWN" ? "AWARIA" : "PRZYWRÓCONO";

    const el = document.createElement("div");
    el.className = `alert-item ${cssClass}`;
    el.textContent = `[${data.timestamp || new Date().toISOString()}] ${label}: ${data.server_id}`;

    container.prepend(el);

    // Keep max 50 alerts visible
    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

// Init
fetchServers();
setInterval(fetchServers, 15000);
connectWebSocket();
